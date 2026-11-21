"""Resumable downloads (D33): continue the part file, ask the URL again after a failure, give up only when stuck."""

import httpx
import pytest

from meeting.download import DownloadError, resumable_get

DATA = bytes(range(256)) * 40  # 10 240 bytes


class Host:
    """A model host behind a resolve URL. `script` is what each request gets: an action per request, in order;
    after the script ends every request is served normally."""

    def __init__(self, script=()):
        self.script = list(script)
        self.requests: list[dict] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append({"url": str(request.url), "range": request.headers.get("Range")})
        if request.url.path.startswith("/resolve/"):  # every attempt is redirected to a newly signed URL
            return httpx.Response(302, headers={"Location": f"https://cdn.test/blob?sig={len(self.requests)}"})
        action = self.script.pop(0) if self.script else "ok"
        start = int(request.headers["Range"].split("=")[1].rstrip("-")) if "Range" in request.headers else 0
        if action == "403":
            return httpx.Response(403)
        if action == "404":
            return httpx.Response(404)
        if action == "refused":  # a host the egress policy does not allow: DNS answers REFUSED, nothing connects
            raise httpx.ConnectError("[Errno -3] Temporary failure in name resolution", request=request)
        if action == "ignore-range":
            return httpx.Response(200, content=DATA)
        body = DATA[start:]
        if action.startswith("cut:"):  # send N bytes, then the connection breaks
            body = body[: int(action[4:])]
            stream = BrokenStream(body)
        else:
            stream = httpx.ByteStream(body)
        status, headers = (206, {"Content-Range": f"bytes {start}-{len(DATA) - 1}/{len(DATA)}"}) if start else (200, {})
        headers["Content-Length"] = str(len(DATA) - start)
        return httpx.Response(status, headers=headers, stream=stream)


class BrokenStream(httpx.SyncByteStream):
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __iter__(self):
        yield self.body
        raise httpx.ReadError("connection reset by peer")


def get(host: Host, tmp_path, **kwargs):
    client = httpx.Client(transport=httpx.MockTransport(host.handler), follow_redirects=True)
    lines: list[str] = []
    path = resumable_get(
        client,
        "https://hub.test/resolve/rev/model.bin",
        tmp_path / "model.bin",
        log=lines.append,
        sleep=lambda s: None,
        **kwargs,
    )
    return path, lines


def test_a_clean_download_lands_under_its_name_and_leaves_no_part_file(tmp_path):
    path, _ = get(Host(), tmp_path)
    assert path.read_bytes() == DATA
    assert not (tmp_path / "model.bin.part").exists()


def test_a_broken_connection_resumes_from_where_it_stopped(tmp_path):
    host = Host(["cut:4000", "cut:3000"])
    path, lines = get(host, tmp_path)
    assert path.read_bytes() == DATA
    ranges = [r["range"] for r in host.requests if "cdn.test" in r["url"]]
    assert ranges == [None, "bytes=4000-", "bytes=7000-"]
    assert sum("resuming" in line for line in lines) == 2


def test_an_expired_signed_url_is_followed_by_a_fresh_one(tmp_path):
    host = Host(["cut:5000", "403"])
    path, _ = get(host, tmp_path)
    assert path.read_bytes() == DATA
    signed = [r["url"] for r in host.requests if "cdn.test" in r["url"]]
    assert len(set(signed)) == len(signed) == 3  # every attempt went back to the resolve URL for a new signature
    assert all(r["url"].startswith("https://hub.test/resolve/") for r in host.requests[::2])


def test_a_part_file_from_an_earlier_run_is_continued(tmp_path):
    (tmp_path / "model.bin.part").write_bytes(DATA[:6000])  # left by a pod that was stopped
    host = Host()
    path, _ = get(host, tmp_path)
    assert path.read_bytes() == DATA
    assert [r["range"] for r in host.requests if "cdn.test" in r["url"]] == ["bytes=6000-"]


def test_a_server_that_ignores_the_range_starts_the_file_again(tmp_path):
    (tmp_path / "model.bin.part").write_bytes(b"x" * 6000)
    path, _ = get(Host(["ignore-range"]), tmp_path)
    assert path.read_bytes() == DATA


def test_attempts_that_add_nothing_end_with_an_error_and_keep_the_bytes(tmp_path):
    host = Host(["cut:4000", "403", "403", "403", "403"])
    with pytest.raises(DownloadError, match=r"4 attempts in a row added nothing.*4000 bytes kept"):
        get(host, tmp_path)
    assert (tmp_path / "model.bin.part").stat().st_size == 4000
    assert not (tmp_path / "model.bin").exists()


def test_a_missing_file_is_not_retried(tmp_path):
    host = Host(["404"])
    with pytest.raises(DownloadError, match="HTTP 404"):
        get(host, tmp_path)
    assert len([r for r in host.requests if "cdn.test" in r["url"]]) == 1


def test_progress_is_reported_while_a_long_download_runs(tmp_path):
    ticks = iter(range(0, 10_000, 40))  # every clock() call is 40 s later
    _, lines = get(Host(), tmp_path, clock=lambda: next(ticks), report_every=30)
    assert any(line.startswith("  model.bin: ") and "MB/s" in line for line in lines)


def test_a_failed_attempt_names_the_host_it_could_not_reach(tmp_path):
    host = Host(["cut:4000", "refused"])
    path, lines = get(host, tmp_path)
    assert path.read_bytes() == DATA
    stopped = [line for line in lines if "stopped at" in line]
    assert "(cdn.test: connection reset by peer)" in stopped[0]
    assert "(cdn.test: [Errno -3] Temporary failure in name resolution)" in stopped[1]
