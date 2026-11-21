"""Downloads that survive a slow or broken line: resume where the last attempt stopped, with a fresh URL each time.

Why not the hub client's own download (M5 on a ~600 KiB/s line): huggingface_hub 1.33 writes each attempt to a new
temporary file, so nothing carries over from one attempt (or one pod) to the next, and Xet-backed files are fetched
through short-lived signed URLs; a 486 MB file that took longer than about an hour ended in `403 Forbidden` and
started again from zero, three times. Here every attempt asks the `resolve` URL again (the host redirects it to a
newly signed URL), continues the `.part` file with an HTTP Range request, and only gives up after several attempts
in a row that added nothing. The `.part` file lives next to the target on the models volume, so a later pod resumes
it too. The caller checks the finished file against the lock; this module only moves bytes (D33).
"""

import contextlib
import os
import time
from collections.abc import Callable
from pathlib import Path

import httpx

RETRY_STATUS = {403, 408, 429, 500, 502, 503, 504}  # 403: a signed URL that expired between redirect and request


class DownloadError(RuntimeError):
    """The download could not be completed."""


def _total_from(response: httpx.Response, start: int) -> int | None:
    if response.status_code == 206:
        content_range = response.headers.get("Content-Range", "")  # bytes START-END/TOTAL
        total = content_range.rpartition("/")[2]
        return int(total) if total.isdigit() else None
    length = response.headers.get("Content-Length")
    return int(length) if length and length.isdigit() else None


def resumable_get(
    client: httpx.Client,
    url: str,
    target: Path,
    *,
    log: Callable[[str], None] = print,
    sleep: Callable[[float], None] = time.sleep,
    max_stalls: int = 4,
    report_every: float = 30.0,
    clock: Callable[[], float] = time.monotonic,
) -> Path:
    """Download url to target via target.part. Returns target. Raises DownloadError when it cannot finish."""
    part = target.with_name(target.name + ".part")
    target.parent.mkdir(parents=True, exist_ok=True)
    stalls, total, attempt = 0, None, 0
    while True:
        attempt += 1
        have = part.stat().st_size if part.exists() else 0
        if total is not None and have == total:
            break
        if total is not None and have > total:
            part.unlink()
            have = 0
        headers = {"Accept-Encoding": "identity"}  # ranges are byte offsets of the file itself, never of a gzip stream
        if have:
            headers["Range"] = f"bytes={have}-"
        started, last_report, wrote = clock(), clock(), 0
        host = httpx.URL(url).host  # the host this attempt last talked to: a blocked one is named in the log (D44)
        try:
            with client.stream("GET", url, headers=headers) as response:
                host = response.url.host  # after redirects: the CDN that serves the bytes
                if response.status_code == 416 and have:  # asked past the end: the part file is already complete or bad
                    part.unlink()
                    continue
                if response.status_code in RETRY_STATUS:
                    raise DownloadError(f"HTTP {response.status_code}")
                if response.status_code not in (200, 206):
                    raise DownloadError(f"{target.name}: HTTP {response.status_code} from the model host")  # fatal
                if have and response.status_code == 200:  # the server ignored the Range header: start again
                    have = 0
                total = _total_from(response, have) or total
                with part.open("ab" if have else "wb") as fh:
                    for chunk in response.iter_bytes():  # as received: a sized chunker would hold back the last bytes
                        fh.write(chunk)
                        wrote += len(chunk)
                        if clock() - last_report >= report_every:
                            last_report = clock()
                            rate = wrote / max(clock() - started, 1e-6) / 1e6
                            done = (have + wrote) / 1e6
                            of = f"/{total / 1e6:.0f}" if total else ""
                            log(f"  {target.name}: {done:.0f}{of} MB, {rate:.1f} MB/s")
            if total is None or part.stat().st_size == total:
                break
            raise DownloadError("the connection closed before the end of the file")
        except (httpx.TransportError, DownloadError) as exc:
            if isinstance(exc, DownloadError) and "from the model host" in str(exc):
                raise
            if isinstance(exc, httpx.TransportError):
                with contextlib.suppress(RuntimeError):  # no request attached (should not happen with stream)
                    host = exc.request.url.host
            stalls = 0 if wrote else stalls + 1
            if stalls >= max_stalls:
                raise DownloadError(
                    f"{target.name}: {stalls} attempts in a row added nothing ({host}: {type(exc).__name__}: {exc}); "
                    f"{part.stat().st_size if part.exists() else 0} bytes kept in {part.name} for the next run"
                ) from exc
            wait = min(60.0, 5.0 * 2**stalls)
            size = part.stat().st_size if part.exists() else 0
            log(
                f"  {target.name}: attempt {attempt} stopped at {size / 1e6:.0f} MB ({host}: {exc}); "
                f"resuming in {wait:.0f} s"
            )
            sleep(wait)
    os.replace(part, target)
    return target
