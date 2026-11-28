"""Models for a pod (Project 7, D56): the chart's Job downloads them into the models volume, every worker checks
them before it starts. Only locked models, from the lock baked into the image, so no Hugging Face client is needed:
a locked model is a list of files at a revision, each with its SHA-256 (D9).

python -m meeting.fetch_job fetch stt-tiny     download into MODELS_DIR, refuse anything that differs from the lock
python -m meeting.fetch_job check stt-tiny     exit 1 unless MODELS_DIR holds exactly the locked files

MODELS_LOCK names the lock file (the image's /opt/meeting-models/models.lock.json); HF_ENDPOINT the host.
"""

import argparse
import os
import sys
from pathlib import Path

from meeting.modelstore import IntegrityError, fetch, read_lock, verify

DEFAULT_LOCK = "/opt/meeting-models/models.lock.json"


class LockedHub:
    """The Hub protocol for locked models only: the lock says which files, the revision says which bytes."""

    def __init__(self, lock: dict, endpoint: str = "https://huggingface.co") -> None:
        self.lock = lock
        self.endpoint = endpoint.rstrip("/")

    def resolve_revision(self, repo: str) -> str:
        raise IntegrityError(f"{repo}: not locked; a pod fetches locked models only (fetch_models.py on a laptop)")

    def list_files(self, repo: str, revision: str) -> list[str]:
        for entry in self.lock.values():
            if entry["repo"] == repo and entry["revision"] == revision:
                return sorted(entry["files"])
        raise IntegrityError(f"{repo}@{revision[:12]}: not in the lock")

    def url(self, repo: str, filename: str, revision: str) -> str:
        return f"{self.endpoint}/{repo}/resolve/{revision}/{filename}"

    def download(self, repo: str, filename: str, revision: str, staging: Path) -> Path:
        import httpx

        from meeting.download import resumable_get

        target = staging / revision[:12] / filename
        timeout = httpx.Timeout(30.0, read=120.0)
        headers = {"User-Agent": "meeting-fetch-job"}
        with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
            return resumable_get(client, self.url(repo, filename, revision), target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=["fetch", "check"])
    parser.add_argument("names", nargs="+")
    args = parser.parse_args(argv)
    lock = read_lock(Path(os.environ.get("MODELS_LOCK", DEFAULT_LOCK)))
    models_dir = Path(os.environ.get("MODELS_DIR", "/models"))
    problems = []
    for name in args.names:
        if name not in lock:
            problems.append(f"{name}: not in the lock")
            continue
        if args.action == "fetch":
            try:
                fetch(
                    name,
                    models_dir,
                    dict(lock),
                    LockedHub(lock, os.environ.get("HF_ENDPOINT", "https://huggingface.co")),
                )
            except (IntegrityError, OSError) as exc:
                problems.append(f"{name}: {type(exc).__name__}: {exc}")
                continue
        problems += verify(name, models_dir, lock)
    for problem in problems:
        print(f"FAIL {problem}", flush=True)
    if not problems:
        print(f"OK   {', '.join(args.names)}: {args.action} matches the lock", flush=True)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
