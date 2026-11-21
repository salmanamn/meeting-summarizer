"""The model lock: first fetch pins, later fetches reproduce, any difference is reported."""

from pathlib import Path

import pytest

from meeting import modelstore
from meeting.modelstore import IntegrityError, ModelSpec, fetch, read_lock, verify, write_lock


class FakeHub:
    """A model host in memory: repo -> revision -> {path: bytes}. `head` is what `main` points at."""

    def __init__(self) -> None:
        self.repos: dict[str, dict[str, dict[str, bytes]]] = {}
        self.head: dict[str, str] = {}
        self.downloads: list[tuple[str, str]] = []

    def publish(self, repo: str, revision: str, files: dict[str, bytes]) -> None:
        self.repos.setdefault(repo, {})[revision] = files
        self.head[repo] = revision

    def resolve_revision(self, repo: str) -> str:
        return self.head[repo]

    def list_files(self, repo: str, revision: str) -> list[str]:
        return list(self.repos[repo][revision])

    def download(self, repo: str, filename: str, revision: str, staging: Path) -> Path:
        self.downloads.append((revision, filename))
        target = staging / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.repos[repo][revision][filename])
        return target


@pytest.fixture
def hub(monkeypatch):
    monkeypatch.setattr(
        modelstore,
        "CATALOG",
        {
            "stt-test": ModelSpec(repo="org/whisper", patterns=modelstore.WHISPER_FILES, licence="test"),
            "tts-test": ModelSpec(
                repo="org/voices", patterns=("ar/x/voice.onnx", "ar/x/voice.onnx.json"), licence="test"
            ),
        },
    )
    fake = FakeHub()
    fake.publish(
        "org/whisper",
        "rev-1",
        {
            "config.json": b"{}",
            "model.bin": b"weights-1",
            "tokenizer.json": b"tok",
            "vocabulary.txt": b"v",
            "README.md": b"x",
        },
    )
    fake.publish(
        "org/voices", "rev-a", {"ar/x/voice.onnx": b"onnx", "ar/x/voice.onnx.json": b"{}", "en/y/other.onnx": b"no"}
    )
    return fake


def test_first_fetch_downloads_matching_files_flat_and_writes_the_lock_entry(hub, tmp_path):
    lock = {}
    entry = fetch("stt-test", tmp_path, lock, hub)

    assert sorted(p.name for p in (tmp_path / "stt-test").iterdir()) == [
        "config.json",
        "model.bin",
        "tokenizer.json",
        "vocabulary.txt",
    ]  # README.md does not match a pattern
    assert entry["repo"] == "org/whisper"
    assert entry["revision"] == "rev-1"
    assert entry["files"]["model.bin"] == {
        "sha256": "d6d6b238a083cd70d9cca3b4232e0289a0dc5cfaa9644d8af7601f92b5c76f4f",
        "size": 9,
    }
    assert lock == {"stt-test": entry}
    assert verify("stt-test", tmp_path, lock) == []
    assert not (tmp_path / ".staging").exists()


def test_files_in_subfolders_land_flat_by_name(hub, tmp_path):
    fetch("tts-test", tmp_path, {}, hub)
    assert sorted(p.name for p in (tmp_path / "tts-test").iterdir()) == ["voice.onnx", "voice.onnx.json"]


def test_lock_round_trips_through_the_file(hub, tmp_path):
    lock = {}
    fetch("stt-test", tmp_path / "models", lock, hub)
    write_lock(tmp_path / "models.lock.json", lock)
    assert read_lock(tmp_path / "models.lock.json") == lock
    assert (tmp_path / "models.lock.json").read_text().endswith("}\n")
    assert read_lock(tmp_path / "absent.json") == {}


def test_locked_fetch_ignores_a_newer_upstream_revision(hub, tmp_path):
    lock = {}
    fetch("stt-test", tmp_path, lock, hub)
    hub.publish("org/whisper", "rev-2", {"config.json": b"{}", "model.bin": b"weights-2", "tokenizer.json": b"tok"})

    fresh = tmp_path / "other-machine"
    entry = fetch("stt-test", fresh, lock, hub)

    assert entry["revision"] == "rev-1"
    assert (fresh / "stt-test" / "model.bin").read_bytes() == b"weights-1"


def test_second_fetch_downloads_nothing_when_files_match_the_lock(hub, tmp_path):
    lock = {}
    fetch("stt-test", tmp_path, lock, hub)
    hub.downloads.clear()
    fetch("stt-test", tmp_path, lock, hub)
    assert hub.downloads == []


def test_a_changed_file_is_reported_and_replaced_by_the_locked_one(hub, tmp_path):
    lock = {}
    fetch("stt-test", tmp_path, lock, hub)
    (tmp_path / "stt-test" / "model.bin").write_bytes(b"tampered!")  # same size, different bytes

    assert verify("stt-test", tmp_path, lock) == ["stt-test: model.bin differs from the lock (sha256 583b16f223ac...)"]
    hub.downloads.clear()
    fetch("stt-test", tmp_path, lock, hub)
    assert hub.downloads == [("rev-1", "model.bin")]
    assert verify("stt-test", tmp_path, lock) == []


def test_verify_reports_missing_and_unexpected_files(hub, tmp_path):
    lock = {}
    fetch("stt-test", tmp_path, lock, hub)
    (tmp_path / "stt-test" / "tokenizer.json").unlink()
    (tmp_path / "stt-test" / "extra.bin").write_bytes(b"?")
    assert verify("stt-test", tmp_path, lock) == [
        "stt-test: tokenizer.json is missing",
        "stt-test: extra.bin is not in the lock",
    ]


def test_verify_without_lock_entry_or_directory(hub, tmp_path):
    assert verify("stt-test", tmp_path, {}) == ["stt-test: not in models.lock.json"]
    lock = {}
    fetch("stt-test", tmp_path, lock, hub)
    assert verify("stt-test", tmp_path / "elsewhere", lock) == [
        f"stt-test: {tmp_path / 'elsewhere' / 'stt-test'} does not exist"
    ]


def test_upstream_content_that_differs_from_the_lock_is_refused(hub, tmp_path):
    lock = {}
    fetch("stt-test", tmp_path, lock, hub)
    locked = dict(lock["stt-test"])
    hub.repos["org/whisper"]["rev-1"]["model.bin"] = b"swapped!!"  # the host serves other bytes for the same revision

    with pytest.raises(IntegrityError, match=r"model\.bin differs from the lock"):
        fetch("stt-test", tmp_path / "other-machine", lock, hub)
    assert lock["stt-test"] == locked  # the lock is never rewritten by a failed fetch


def test_update_moves_the_lock_to_the_newest_revision(hub, tmp_path):
    lock = {}
    fetch("stt-test", tmp_path, lock, hub)
    hub.publish(
        "org/whisper",
        "rev-2",
        {"config.json": b"{}", "model.bin": b"weights-2", "tokenizer.json": b"tok", "vocabulary.json": b"[]"},
    )

    entry = fetch("stt-test", tmp_path, lock, hub, update=True)

    assert entry["revision"] == "rev-2"
    assert (tmp_path / "stt-test" / "model.bin").read_bytes() == b"weights-2"
    assert "vocabulary.json" in entry["files"]


def test_lock_for_another_repository_is_refused(hub, tmp_path):
    lock = {"stt-test": {"repo": "someone/else", "revision": "rev-1", "files": {}}}
    with pytest.raises(IntegrityError, match="locked to someone/else"):
        fetch("stt-test", tmp_path, lock, hub)


def test_repository_without_matching_files_is_refused(hub, tmp_path):
    hub.publish("org/voices", "rev-b", {"en/y/other.onnx": b"no"})
    with pytest.raises(IntegrityError, match="no file in org/voices@rev-b"):
        fetch("tts-test", tmp_path, {}, hub)


def test_real_catalog_names_are_directory_safe_and_patterns_cover_a_whisper_model():
    for name, spec in modelstore.CATALOG.items():
        assert name == Path(name).name and name.startswith(("stt-", "tts-"))
        assert "/" in spec.repo
    assert {"model.bin", "tokenizer.json", "config.json"} <= set(modelstore.CATALOG["stt-small"].patterns)
