"""Model files: where they come from, and a lock file that pins exactly which bytes are used.

Models are not in git and not in container images. `CATALOG` says which Hugging Face repository and which files
make up each model. `models.lock.json` (committed) records, per model, the repository revision (a git commit id)
and the SHA-256 and size of every file. The first fetch of a model resolves the newest revision and writes the lock
entry; every later fetch, on any machine, downloads that same revision and refuses files that differ.
"""

import contextlib
import fnmatch
import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

LOCK_FILE = "models.lock.json"
WHISPER_FILES = ("config.json", "preprocessor_config.json", "model.bin", "tokenizer.json", "vocabulary.*")


@dataclass(frozen=True)
class ModelSpec:
    repo: str
    patterns: tuple[str, ...]  # fnmatch patterns on the path inside the repository
    licence: str


CATALOG: dict[str, ModelSpec] = {
    "stt-small": ModelSpec(
        repo="Systran/faster-whisper-small",
        patterns=WHISPER_FILES,
        licence="MIT (OpenAI Whisper small, CTranslate2 conversion by Systran)",
    ),
    "stt-tiny": ModelSpec(
        repo="Systran/faster-whisper-tiny",
        patterns=WHISPER_FILES,
        licence="MIT (OpenAI Whisper tiny, CTranslate2 conversion by Systran); for CI's pipeline test (M4)",
    ),
    "tts-en-libritts": ModelSpec(
        repo="rhasspy/piper-voices",
        patterns=(
            "en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx",
            "en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx.json",
            "en/en_US/libritts_r/medium/MODEL_CARD",
        ),
        licence="CC BY 4.0 (LibriTTS-R dataset, per the model card); for the synthetic test meetings only (D7)",
    ),
}


class Hub(Protocol):
    """The three things needed from a model repository host. `HuggingFaceHub` is the real one; tests use a fake."""

    def resolve_revision(self, repo: str) -> str: ...

    def list_files(self, repo: str, revision: str) -> list[str]: ...

    def download(self, repo: str, filename: str, revision: str, staging: Path) -> Path: ...


class HuggingFaceHub:
    def __init__(self) -> None:
        from huggingface_hub import HfApi  # imported here: only fetching needs the hub client

        self._api = HfApi()

    def resolve_revision(self, repo: str) -> str:
        return self._api.model_info(repo).sha

    def list_files(self, repo: str, revision: str) -> list[str]:
        return [sibling.rfilename for sibling in self._api.model_info(repo, revision=revision).siblings]

    def download(self, repo: str, filename: str, revision: str, staging: Path) -> Path:
        import httpx
        from huggingface_hub import hf_hub_url

        from meeting.download import resumable_get

        # Not hf_hub_download: it cannot resume across attempts, and Xet's signed URLs expire on a slow line (D33).
        # The partial file is kept under staging/<revision>, so a later run (another pod) resumes it.
        url = hf_hub_url(repo, filename, revision=revision)  # honours HF_ENDPOINT
        target = staging / revision[:12] / filename
        timeout = httpx.Timeout(30.0, read=120.0)
        with httpx.Client(
            follow_redirects=True, timeout=timeout, headers={"User-Agent": "meeting-fetch-models"}
        ) as client:
            return resumable_get(client, url, target)


class IntegrityError(RuntimeError):
    """Model files differ from the lock file."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def read_lock(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def write_lock(path: Path, lock: dict) -> None:
    path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def describe(directory: Path) -> dict[str, dict]:
    """SHA-256 and size of every file in a model directory."""
    return {
        item.name: {"sha256": sha256_file(item), "size": item.stat().st_size}
        for item in sorted(directory.iterdir())
        if item.is_file()
    }


def verify(name: str, models_dir: Path, lock: dict) -> list[str]:
    """Problems with a model on disk compared with the lock (an empty list means it is exactly the locked model)."""
    entry = lock.get(name)
    if entry is None:
        return [f"{name}: not in {LOCK_FILE}"]
    directory = models_dir / name
    if not directory.is_dir():
        return [f"{name}: {directory} does not exist"]
    problems = []
    on_disk = describe(directory)
    for filename, expected in entry["files"].items():
        actual = on_disk.pop(filename, None)
        if actual is None:
            problems.append(f"{name}: {filename} is missing")
        elif actual != expected:
            problems.append(f"{name}: {filename} differs from the lock (sha256 {actual['sha256'][:12]}...)")
    problems.extend(f"{name}: {filename} is not in the lock" for filename in on_disk)
    return problems


def fetch(name: str, models_dir: Path, lock: dict, hub: Hub, *, update: bool = False) -> dict:
    """Download a model into models_dir/<name>/ and return its lock entry (also stored in `lock`).

    Locked and not `update`: download the locked revision; raise IntegrityError if any file differs from the lock.
    Not locked, or `update`: resolve the newest revision, download it and write a new lock entry.
    """
    spec = CATALOG[name]
    locked = None if update else lock.get(name)
    if locked is not None and locked["repo"] != spec.repo:
        raise IntegrityError(f"{name}: locked to {locked['repo']}, catalog says {spec.repo}; fetch with --update")
    revision = locked["revision"] if locked else hub.resolve_revision(spec.repo)

    wanted = [f for f in hub.list_files(spec.repo, revision) if any(fnmatch.fnmatch(f, p) for p in spec.patterns)]
    if not wanted:
        raise IntegrityError(f"{name}: no file in {spec.repo}@{revision} matches {spec.patterns}")

    directory = models_dir / name
    directory.mkdir(parents=True, exist_ok=True)
    staging = models_dir / ".staging" / name
    for filename in sorted(wanted):
        target = directory / Path(filename).name
        expected = locked["files"].get(target.name) if locked else None
        if expected and target.is_file() and target.stat().st_size == expected["size"]:
            if sha256_file(target) == expected["sha256"]:
                continue  # already the locked file
        downloaded = hub.download(spec.repo, filename, revision, staging)
        os.replace(downloaded, target)
    shutil.rmtree(staging, ignore_errors=True)
    with contextlib.suppress(OSError):
        staging.parent.rmdir()  # only succeeds when no other download is staged

    entry = {"repo": spec.repo, "revision": revision, "files": describe(directory)}
    if locked is not None and entry["files"] != locked["files"]:
        raise IntegrityError(
            f"{name}: files of {spec.repo}@{revision[:12]} differ from {LOCK_FILE}: "
            + "; ".join(verify(name, models_dir, lock))
        )
    lock[name] = entry
    return entry
