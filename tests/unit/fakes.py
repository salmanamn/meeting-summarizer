"""In-memory stand-ins for meeting.stores (same methods, same ETag rules) and for the two models."""

import hashlib
import itertools
import json
import wave
from pathlib import Path

from factories import make_transcript

from meeting.stores import BlobInfo, Conflict, TooLarge

_etags = itertools.count(1)


def new_etag() -> str:
    return f'"0x{next(_etags):015X}"'


class FakeBlobs:
    def __init__(self, incoming: str = "incoming", transcripts: str = "transcripts") -> None:
        self.incoming, self.transcripts = incoming, transcripts
        self.data: dict[tuple[str, str], tuple[bytes, str]] = {}
        self.downloads: list[str] = []  # names streamed in full (sha256), in order

    def put(self, container: str, name: str, data: bytes) -> str:
        etag = new_etag()
        self.data[(container, name)] = (data, etag)
        return etag

    def read(self, container, name, max_bytes):
        if (container, name) not in self.data:
            return None
        data, etag = self.data[(container, name)]
        if len(data) > max_bytes:
            raise TooLarge(name)
        return data, etag

    def info(self, container, name):
        if (container, name) not in self.data:
            return None
        data, etag = self.data[(container, name)]
        return BlobInfo(size=len(data), etag=etag)

    def head(self, container, name, length):
        return self.data[(container, name)][0][:length]

    def sha256(self, container, name, max_bytes, target=None):
        data = self.data[(container, name)][0]
        self.downloads.append(name)
        if len(data) > max_bytes:
            raise TooLarge(name)
        if target:
            Path(target).write_bytes(data)
        return hashlib.sha256(data).hexdigest()

    def write_text(self, container, name, text):
        self.put(container, name, text.encode())

    def read_text(self, container, name):
        got = self.data.get((container, name))
        return got[0].decode() if got else None


class FakeJobs:
    def __init__(self) -> None:
        self.docs: dict[str, dict] = {}
        self.writes = 0

    def _stored(self, doc: dict) -> dict:
        stored = json.loads(json.dumps({k: v for k, v in doc.items() if not k.startswith("_")}))
        stored["_etag"] = new_etag()
        self.docs[doc["id"]] = stored
        self.writes += 1
        return json.loads(json.dumps(stored))

    def get(self, job_id):
        doc = self.docs.get(job_id)
        return json.loads(json.dumps(doc)) if doc else None

    def create(self, doc):
        if doc["id"] in self.docs:
            raise Conflict(doc["id"])
        return self._stored(doc)

    def replace(self, doc):
        current = self.docs.get(doc["id"])
        if current is None or current["_etag"] != doc.get("_etag"):
            raise Conflict(doc["id"])
        return self._stored(doc)

    def increment(self, job_id, field):
        self.docs[job_id][field] += 1
        self.docs[job_id]["_etag"] = new_etag()


class FakeTranscriber:
    def __init__(self, transcript=None, error: Exception | None = None) -> None:
        self.transcript = transcript or make_transcript(
            (0.0, 6.5, "Good morning. Omar, please send the numbers by Wednesday."),
            (7.0, 12.0, "Sure, I will send them by Wednesday."),
        )
        self.error = error
        self.calls: list[tuple[Path, tuple[str, ...]]] = []

    def transcribe(self, audio, *, names=()):
        self.calls.append((Path(audio), names))
        if self.error:
            raise self.error
        return self.transcript


def wav_bytes(seconds: float = 1.0, rate: int = 16000) -> bytes:
    """A silent mono 16-bit WAV file of the given length (PyAV reads its duration)."""
    import io

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(seconds * rate))
    return buffer.getvalue()


class FakeModel:
    """Stands in for meeting.llm.JsonModel: returns `answer` (a dict, dumped to JSON) or raises `error`."""

    def __init__(self, answer: dict | None = None, error: Exception | None = None) -> None:
        self.answer = answer
        self.error = error
        self.calls = 0
        self.requests: list[dict] = []  # name, user message and schema of every call

    def complete_json(self, *, system, user, schema, name):
        from meeting.llm import Completion

        self.calls += 1
        self.requests.append({"name": name, "user": user, "schema": schema})
        if self.error:
            raise self.error
        return Completion(
            text=json.dumps(self.answer), seconds=1.5, prompt_tokens=300, completion_tokens=120, finish_reason="stop"
        )


class FakeReader:
    """Stands in for meeting.documents.LocalReader: one block per attachment, or raises `error`."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[str] = []

    def read(self, path, name, kind):
        from meeting.documents import Block, Document

        self.calls.append(name)
        if self.error:
            raise self.error
        text = Path(path).read_bytes()[:40].decode(errors="replace")
        return Document(
            name=name, kind=kind, pages=1 if kind == "pdf" else None, blocks=[Block(f"{name} #1", text)], engine="fake"
        )
