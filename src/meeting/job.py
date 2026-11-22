"""One meeting job (D15-D18): the manifest's arrival starts it, a record in Cosmos DB carries it through its stages.

    received     the manifest is valid and every file it lists is there, the right size, type and SHA-256; the
                 attachments are read into text blocks, stored next to the transcript (D22)
    transcribed  the transcript is stored as a blob (a retry or a re-upload of the same recording reuses it)
    summarised   the grounded summary is on the record
    failed       error.code says why; error.retryable says whether delivering the same manifest again helps

The Event Grid-based Blob trigger runs the function for every delivery of a BlobCreated event, duplicates
included, on whatever blob is there now (it does not compare ETags, and keeps no receipts). So this module decides
what a delivery means:
- same manifest ETag, job summarised (or failed for good): a duplicate, counted in `deliveries`, nothing redone;
- same ETag, job unfinished: a retry (the function failed or the host died), resumed where the record says;
- another ETag: a new upload of the folder. It restarts a failed job; any other job ignores it (`ignored_uploads`).
Every write after the first is conditioned on the record's ETag, so of two concurrent deliveries one does the
work and the other stops (D18).

Errors: `Rejected` = the upload or its content can't be summarised (permanent, no model call is retried for it).
Anything else is transient (model or store unreachable): it propagates, the host retries the delivery at once, up
to JOB_MAX_ATTEMPTS = poisonBlobThreshold, and the last attempt records `retries_exhausted` instead of raising.
A model error (timeout, no connection, 429, 5xx) first waits 30, 60, 120, 120 s (D21): the host's retry is
immediate, and a local model keeps generating a request its client gave up on, so an immediate retry only queues
behind it and times out too (M2 run A).
"""

import logging
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import openai

from meeting.documents import AttachmentRejected, Document, LocalReader
from meeting.manifest import MANIFEST_NAME, ManifestInvalid, meeting_id_from_path, parse
from meeting.media import HEAD_BYTES, Unreadable, attachment_kind, audio_kind, duration_seconds
from meeting.settings import Settings
from meeting.stores import Conflict, TooLarge
from meeting.summarize import NoSpeech, SummaryInvalid, TranscriptTooLong, summarize
from meeting.transcript import Transcript

log = logging.getLogger("meeting.job")
RECORD_VERSION = 1
# Errors from the model's endpoint worth waiting for. APITimeoutError is an APIConnectionError.
MODEL_ERRORS = (openai.APIConnectionError, openai.RateLimitError, openai.InternalServerError)


def model_retry_delay(attempt: int, base: int, cap: int) -> int:
    """Seconds to wait after a model error on `attempt` (1-based) before the host retries: base, 2x, 4x ..., capped."""
    return min(cap, base * 2 ** (attempt - 1))


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class Rejected(Exception):
    """Permanent: the upload breaks the contract, or its content can't be summarised. `code` is stable (status
    endpoint, tests); the message names files and limits, never content."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Outcome:
    status: str  # summarised | failed | duplicate | ignored
    meeting_id: str | None
    detail: str


def transcript_blob_name(meeting_id: str, sha256: str, stt_model: str) -> str:
    """One transcript per recording content and model: a re-upload of the same bytes reuses it."""
    return f"{meeting_id}/{sha256[:16]}.{stt_model}.json"


def document_blob_name(meeting_id: str, sha256: str, name: str) -> str:
    """An attachment's text blocks, keyed by its content like the transcript (D22)."""
    return f"{meeting_id}/{sha256[:16]}.{name}.json"


def public_view(doc: dict) -> dict:
    """The record as the status endpoint shows it: Cosmos system fields dropped."""
    return {k: v for k, v in doc.items() if not k.startswith("_")}


class JobRunner:
    def __init__(
        self,
        settings: Settings,
        blobs,
        jobs,
        transcriber: Callable[[], object],
        model: Callable[[], object],
        now: Callable[[], str] = utc_now,
        sleep: Callable[[float], None] = time.sleep,
        reader: Callable[[], object] | None = None,
    ) -> None:
        self.s = settings
        self.blobs = blobs
        self.jobs = jobs
        self._transcriber = transcriber  # factories: the Whisper model and the client load on first use only
        self._model = model
        self.now = now
        self.sleep = sleep
        self._reader = reader or (lambda: LocalReader(max_pages=settings.max_attachment_pages))

    # ---- entry point -------------------------------------------------------------------------------------------

    def handle(self, blob_path: str) -> Outcome:
        meeting_id = meeting_id_from_path(blob_path, self.s.incoming_container)
        if meeting_id is None:
            return Outcome("ignored", None, "not a manifest in a meeting folder")
        try:
            got = self.blobs.read(self.s.incoming_container, f"{meeting_id}/{MANIFEST_NAME}", self.s.max_manifest_bytes)
        except TooLarge:
            info = self.blobs.info(self.s.incoming_container, f"{meeting_id}/{MANIFEST_NAME}")
            got = (None, info.etag) if info else None
        if got is None:
            return Outcome("ignored", meeting_id, "the manifest no longer exists")
        raw, etag = got

        with tempfile.TemporaryDirectory(prefix="meeting-") as tmp:
            job = self.jobs.get(meeting_id)
            if job is not None and job["manifest_etag"] == etag:
                return self._again(job, Path(tmp))
            if job is not None and job["stage"] != "failed":
                self.jobs.increment(meeting_id, "ignored_uploads")
                log.warning("%s: new manifest ignored, the job is %s (use a new meeting id)", meeting_id, job["stage"])
                return Outcome("ignored", meeting_id, f"job is {job['stage']}; a new manifest needs a new meeting id")
            return self._start(meeting_id, raw, etag, job, Path(tmp))

    # ---- the three ways in -------------------------------------------------------------------------------------

    def _again(self, job: dict, tmp: Path) -> Outcome:
        """Another delivery for the manifest this job was started from."""
        meeting_id = job["id"]
        error = job.get("error") or {}
        if job["stage"] == "summarised" or (job["stage"] == "failed" and not error.get("retryable")):
            self.jobs.increment(meeting_id, "deliveries")
            log.info("%s: duplicate delivery, job already %s", meeting_id, job["stage"])
            return Outcome("duplicate", meeting_id, f"job already {job['stage']}")
        job["deliveries"] += 1
        if job["stage"] == "failed":  # retries were exhausted earlier: this delivery starts a new round
            job["history"].append(error)
            job["stages"].pop("failed", None)
            job.update(error=None, attempts=0, stage="transcribed" if job["transcript"] else "received")
        return self._work(job, None, tmp)

    def _start(self, meeting_id: str, raw: bytes | None, etag: str, prior: dict | None, tmp: Path) -> Outcome:
        """A new job, or a failed job restarted by a new upload of its folder."""
        now = self.now()
        doc = {
            "id": meeting_id,
            "record_version": RECORD_VERSION,
            "manifest_etag": etag,
            "stage": "received",
            "attempts": 0,
            "deliveries": (prior["deliveries"] + 1) if prior else 1,
            "ignored_uploads": prior["ignored_uploads"] if prior else 0,
            "stt_runs": prior["stt_runs"] if prior else 0,  # completed Whisper runs: a reused transcript adds none
            "created_at": prior["created_at"] if prior else now,
            "updated_at": now,
            "stages": {},  # stage -> time reached; "received" only once every check passed
            "title": None,
            "language": None,
            "attendees": [],
            "files": [],
            "recording_seconds": None,
            "transcript": None,
            "summary": None,
            "summary_meta": None,
            "error": None,
            "history": [*prior["history"], prior["error"]] if prior else [],
        }
        if prior:
            doc["_etag"] = prior["_etag"]
        recording = None
        try:
            manifest, files, recording, seconds = self._verify(meeting_id, raw, tmp)
            self._read_attachments(meeting_id, files, tmp)
        except Rejected as rejected:
            self._mark_failed(
                doc, rejected.code, rejected.message, retryable=False, stage="received", new=prior is None
            )
            return Outcome("failed", meeting_id, rejected.code)
        doc.update(
            title=manifest.title,
            language=manifest.language,
            attendees=list(manifest.attendees),
            files=files,
            recording_seconds=round(seconds, 2),
        )
        doc["stages"]["received"] = self.now()
        try:
            doc = self._write(doc, new=prior is None)
        except Conflict:
            return Outcome("duplicate", meeting_id, "another delivery started this job")
        log.info("%s: received (%d file(s), %.1f s of audio)", meeting_id, len(files), seconds)
        return self._work(doc, recording, tmp)

    # ---- stages ------------------------------------------------------------------------------------------------

    def _work(self, doc: dict, recording: Path | None, tmp: Path) -> Outcome:
        meeting_id = doc["id"]
        doc["attempts"] += 1
        doc["updated_at"] = self.now()
        try:
            doc = self.jobs.replace(doc)  # the attempt counts before the work: a host that dies still used one
        except Conflict:
            return Outcome("duplicate", meeting_id, "another delivery is working on this job")
        attempt, limit = doc["attempts"], self.s.job_max_attempts
        if attempt > limit:
            self._mark_failed(doc, "retries_exhausted", f"attempt {attempt} of {limit}", retryable=True)
            return Outcome("failed", meeting_id, "retries_exhausted")
        try:
            transcript, doc = self._transcribed(doc, recording, tmp)
            doc = self._summarised(doc, transcript)
        except Rejected as rejected:
            self._mark_failed(doc, rejected.code, rejected.message, retryable=False)
            return Outcome("failed", meeting_id, rejected.code)
        except Conflict:
            return Outcome("duplicate", meeting_id, "another delivery finished a stage first")
        except Exception as exc:
            if attempt >= limit:
                message = f"{type(exc).__name__} on attempt {attempt} of {limit}"
                self._mark_failed(doc, "retries_exhausted", message, retryable=True)
                return Outcome("failed", meeting_id, "retries_exhausted")
            log.warning(
                "%s: attempt %d of %d failed in %s: %s", meeting_id, attempt, limit, doc["stage"], type(exc).__name__
            )
            if isinstance(exc, MODEL_ERRORS):
                delay = model_retry_delay(attempt, self.s.model_retry_base_seconds, self.s.model_retry_max_seconds)
                log.info("%s: model error, waiting %d s before the host retries", meeting_id, delay)
                self.sleep(delay)
            raise
        return Outcome("summarised", meeting_id, f"attempt {attempt}")

    def _transcribed(self, doc: dict, recording: Path | None, tmp: Path) -> tuple[Transcript, dict]:
        meeting_id = doc["id"]
        ref = doc["files"][0]  # the recording is always first (manifest.files)
        name = transcript_blob_name(meeting_id, ref["sha256"], self.s.stt_model)
        stored = self.blobs.read_text(self.s.transcripts_container, name)
        if stored is not None:
            transcript = Transcript.from_json(stored)
            if doc["stage"] == "transcribed":
                return transcript, doc
            log.info("%s: transcript reused from %s", meeting_id, name)
        else:
            if recording is None:  # a retry: the file from the first attempt is gone, and may have been replaced
                recording = tmp / ref["name"]
                sha = self.blobs.sha256(
                    self.s.incoming_container, f"{meeting_id}/{ref['name']}", self.s.max_recording_bytes, recording
                )
                if sha != ref["sha256"]:
                    raise Rejected("hash_mismatch", f"{ref['name']} changed since the job was received")
            transcript = self._transcriber().transcribe(recording, names=tuple(doc["attendees"]))
            if not transcript.segments:
                raise Rejected("no_speech", "the recording has no speech")
            self.blobs.write_text(self.s.transcripts_container, name, transcript.to_json())
            doc["stt_runs"] += 1
            log.info(
                "%s: transcribed, %d segments, %.1f s of audio in %.1f s",
                meeting_id,
                len(transcript.segments),
                transcript.audio_seconds,
                transcript.seconds,
            )
        now = self.now()
        doc["transcript"] = {
            "blob": f"{self.s.transcripts_container}/{name}",
            "segments": len(transcript.segments),
            "audio_seconds": transcript.audio_seconds,
            "seconds": transcript.seconds,
            "engine": transcript.engine,
        }
        doc["stage"] = "transcribed"
        doc["stages"]["transcribed"] = now
        doc["updated_at"] = now
        return transcript, self.jobs.replace(doc)

    def _summarised(self, doc: dict, transcript: Transcript) -> dict:
        try:
            result = summarize(
                transcript,
                self._model(),
                attendees=tuple(doc["attendees"]),
                documents=self._documents(doc),
                max_chars=self.s.transcript_max_chars,
                part_chars=self.s.part_max_chars,
                attachment_chars=self.s.attachment_context_chars,
            )
        except NoSpeech:
            raise Rejected("no_speech", "the transcript is empty") from None
        except TranscriptTooLong as exc:
            raise Rejected("transcript_too_long", str(exc)) from None
        except SummaryInvalid as exc:
            raise Rejected("summary_invalid", str(exc)) from None
        c = result.completion
        now = self.now()
        doc["summary"] = result.summary.model_dump(mode="json")
        doc["summary_meta"] = {
            "model": self.s.chat_model,
            "seconds": c.seconds,
            "prompt_tokens": c.prompt_tokens,
            "completion_tokens": c.completion_tokens,
            "parts": result.parts,
            "calls": result.calls,
            "attachments_cut": list(result.truncated),
            "grounding_warnings": result.warnings,
        }
        doc["stage"] = "summarised"
        doc["stages"]["summarised"] = now
        doc["updated_at"] = now
        doc = self.jobs.replace(doc)
        log.info("%s: summarised in %.1f s (%s completion tokens)", doc["id"], c.seconds, c.completion_tokens)
        return doc

    # ---- checks before any model runs (D16) --------------------------------------------------------------------

    def _verify(self, meeting_id: str, raw: bytes | None, tmp: Path):
        if raw is None:
            raise Rejected("too_large", f"{MANIFEST_NAME} is larger than {self.s.max_manifest_bytes // 1024} KB")
        try:
            manifest = parse(raw, meeting_id)
        except ManifestInvalid as exc:
            raise Rejected("invalid_manifest", str(exc)) from None

        incoming = self.s.incoming_container
        checks = [(manifest.recording, "recording", self.s.max_recording_bytes)]
        checks += [(a, "attachment", self.s.max_attachment_bytes) for a in manifest.attachments]
        files = []
        for ref, role, limit in checks:  # cheap checks for every file first: no download for a broken upload
            if ref.size > limit:
                raise Rejected("too_large", f"{ref.name}: {ref.size} bytes, the limit for a {role} is {limit}")
            info = self.blobs.info(incoming, f"{meeting_id}/{ref.name}")
            if info is None:
                raise Rejected("missing_file", f"{ref.name} is listed but not in the folder")
            if info.size != ref.size:
                raise Rejected("size_mismatch", f"{ref.name}: {info.size} bytes stored, {ref.size} in the manifest")
            head = self.blobs.head(incoming, f"{meeting_id}/{ref.name}", HEAD_BYTES)
            kind = audio_kind(head) if role == "recording" else attachment_kind(head, ref.name)
            if kind is None:
                allowed = "wav, mp3, m4a, ogg, flac, webm" if role == "recording" else "pdf, docx"
                raise Rejected("unsupported_type", f"{ref.name}: its content is not one of {allowed}")
            files.append({"name": ref.name, "role": role, "kind": kind, "size": ref.size, "sha256": ref.sha256})

        recording = tmp / manifest.recording.name
        for ref, role, limit in checks:
            target = recording if role == "recording" else tmp / ref.name  # attachments are read next (D22)
            try:
                sha = self.blobs.sha256(incoming, f"{meeting_id}/{ref.name}", limit, target)
            except TooLarge:
                raise Rejected("too_large", f"{ref.name} grew past the limit while it was read") from None
            if sha != ref.sha256:
                raise Rejected("hash_mismatch", f"{ref.name}: the SHA-256 differs from the manifest")

        try:
            seconds = duration_seconds(recording)
        except Unreadable as exc:
            raise Rejected("unreadable_audio", f"{manifest.recording.name}: {exc}") from None
        if seconds > self.s.max_recording_seconds:
            limit_min = self.s.max_recording_seconds / 60
            raise Rejected("too_long", f"{seconds / 60:.1f} minutes of audio, the limit is {limit_min:.0f}")
        return manifest, files, recording, seconds

    # ---- attachments (D22) -------------------------------------------------------------------------------------

    def _read_attachments(self, meeting_id: str, files: list[dict], tmp: Path) -> None:
        """Read every attachment _verify downloaded into text blocks, store them as a blob, and note the blob and
        the counts on the file's entry. A file that can't be read is a permanent failure, before any model runs."""
        attachments = [f for f in files if f["role"] == "attachment"]
        if not attachments:
            return
        reader = self._reader()
        for entry in attachments:
            try:
                document = reader.read(tmp / entry["name"], entry["name"], entry["kind"])
            except AttachmentRejected as exc:
                raise Rejected(exc.code, exc.message) from None
            name = document_blob_name(meeting_id, entry["sha256"], entry["name"])
            self.blobs.write_text(self.s.transcripts_container, name, document.to_json())
            entry["document"] = {
                "blob": f"{self.s.transcripts_container}/{name}",
                "pages": document.pages,
                "blocks": len(document.blocks),
                "chars": document.chars,
                "engine": document.engine,
                "warnings": document.warnings,
            }
            log.info(
                "%s: %s read, %d block(s), %d characters",
                meeting_id,
                entry["name"],
                len(document.blocks),
                document.chars,
            )

    def _documents(self, doc: dict) -> tuple[Document, ...]:
        out = []
        for entry in doc["files"]:
            if entry["role"] != "attachment":
                continue
            container, _, name = entry["document"]["blob"].partition("/")
            stored = self.blobs.read_text(container, name)
            if stored is None:  # written before the record said "received"; gone only if someone deleted it
                raise Rejected("missing_file", f"the text of {entry['name']} is no longer stored")
            out.append(Document.from_json(stored))
        return tuple(out)

    # ---- record writes -----------------------------------------------------------------------------------------

    def _write(self, doc: dict, *, new: bool) -> dict:
        return (
            self.jobs.create({k: v for k, v in doc.items() if not k.startswith("_")}) if new else self.jobs.replace(doc)
        )

    def _mark_failed(
        self, doc: dict, code: str, message: str, *, retryable: bool, stage: str | None = None, new: bool = False
    ) -> None:
        now = self.now()
        doc["error"] = {
            "code": code,
            "message": message,
            "stage": stage or doc["stage"],
            "retryable": retryable,
            "at": now,
        }
        doc["stage"] = "failed"
        doc["stages"]["failed"] = now
        doc["updated_at"] = now
        try:
            self._write(doc, new=new)
        except Conflict:
            log.info("%s: another delivery wrote the job first; %s not recorded by this one", doc["id"], code)
            return
        log.warning("%s: failed (%s): %s", doc["id"], code, message)
