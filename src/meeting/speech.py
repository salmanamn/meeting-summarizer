"""Speech to text on Azure: Azure AI Speech batch transcription, REST API 2025-10-15 (D3, D44, D45).

A batch transcription is a job on the service, not a call: submit it with the recording's plain blob URL (the
Speech resource reads the blob with its own managed identity, no SAS), poll it until it has succeeded or failed,
read its result file, delete it. The job (`meeting.job`) records the job's URL on the meeting record as soon as it
is submitted, so a delivery that runs out of waiting time, or a host that dies, never submits the recording twice:
the next delivery polls the same job (D45).

Authentication (D46): a Microsoft Entra token for Cognitive Services on every call to the Speech endpoint, which
must be the resource's custom subdomain. The token is only ever sent to that endpoint's origin: a link in a
response that points anywhere else is refused, and the result file (a SAS URL on Microsoft-managed storage) is
fetched without it.

What the result gives the transcript: one segment per recognized phrase (the best of `nBest`, display form, with
punctuation), its offset and duration in ticks (100 ns), and with diarization a speaker number, written
`Guest-<n>` (a label, never a name, D6). Batch transcription has no phrase list, so the attendees' names can't be
passed as hints the way Whisper takes them: the transcript says so in its warnings (D44).
"""

import logging
import time
from collections.abc import Callable
from datetime import datetime
from urllib.parse import urlsplit

import httpx

from meeting.settings import Settings
from meeting.transcript import Segment, Transcript

log = logging.getLogger("meeting.speech")

API_VERSION = "2025-10-15"
TICKS_PER_SECOND = 10_000_000
TIME_TO_LIVE_HOURS = 24  # the service deletes a job this long after it finished; we delete it as soon as it's read
MAX_SPEAKERS = 35  # the API's limit for diarization.maxSpeakers (2..35)
# Failures that delivering the same recording again can't fix (DetailedErrorCode values of the 2025-10-15 API).
PERMANENT_CODES = frozenset(
    {
        "InvalidAudioFormat",
        "EmptyAudioFile",
        "AudioLengthLimitExceeded",
        "BadChannelConfiguration",
        "InvalidChannelSpecification",
    }
)
NO_PHRASE_LIST = "attendee names not passed: batch transcription takes no phrase list (D44)"


class SpeechError(RuntimeError):
    """Transient: the call didn't work this time (configuration, a role still propagating, a bad answer). The job
    lets it propagate and the host retries the delivery."""


class SpeechUnavailable(SpeechError):
    """The service is unreachable, overloaded (429) or failing (5xx): waited for like a model error (D21)."""


class SpeechJobGone(SpeechError):
    """The submitted job no longer exists (deleted, or past its time to live): it must be submitted again."""


class SpeechJobFailed(Exception):
    """The job reached `Failed`. `permanent` when the recording itself is the problem (PERMANENT_CODES)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.permanent = code in PERMANENT_CODES


class TranscriptionPending(RuntimeError):
    """Not finished within this delivery's waiting time. Transient on purpose: the host's next delivery polls the
    same job again (its URL is on the record), it never submits a second one."""


def _seconds(ticks: float | int | None) -> float:
    return round((ticks or 0) / TICKS_PER_SECOND, 2)


def _timestamp(text: str | None) -> datetime | None:
    if not text:
        return None
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def speakers_hint(attendees: int) -> int:
    """diarization.maxSpeakers: the number of attendees, within the API's 2..35."""
    return max(2, min(MAX_SPEAKERS, attendees or 2))


def segments_from_result(result: dict, channel: int = 0) -> list[Segment]:
    """The recognized phrases of one channel, in time order, as the summary's segments."""
    out = []
    for phrase in result.get("recognizedPhrases", []):
        if phrase.get("recognitionStatus") != "Success" or phrase.get("channel", 0) != channel:
            continue
        best = (phrase.get("nBest") or [{}])[0]
        text = (best.get("display") or "").strip()
        if not text:
            continue
        start = phrase.get("offsetInTicks", 0)
        speaker = phrase.get("speaker")
        out.append(
            Segment(
                start=_seconds(start),
                end=_seconds(start + phrase.get("durationInTicks", 0)),
                text=text,
                speaker=f"Guest-{speaker}" if speaker is not None else None,
            )
        )
    return sorted(out, key=lambda s: (s.start, s.end))


class SpeechTranscriber:
    """The Speech batch transcription client. `remote = True` tells the job to hand it a blob URL, not a file."""

    remote = True

    def __init__(
        self,
        endpoint: str,
        *,
        token: Callable[[], str],
        locale: str = "en-US",
        region: str = "",
        poll_seconds: int = 15,
        wait_seconds: int = 1200,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        parts = urlsplit(endpoint)
        if parts.scheme not in ("https", "http") or not parts.netloc:
            raise ValueError(f"SPEECH_ENDPOINT is not a URL: {endpoint!r}")
        self.origin = f"{parts.scheme}://{parts.netloc}"
        self.token = token
        self.locale = locale
        self.poll_seconds = poll_seconds
        self.wait_seconds = wait_seconds
        self.name = f"azure-speech batch {API_VERSION}" + (f" {region}" if region else "")
        self._client = client or httpx.Client(timeout=httpx.Timeout(30.0), follow_redirects=False)
        self._sleep = sleep
        self._clock = clock

    @classmethod
    def from_settings(cls, settings: Settings) -> "SpeechTranscriber":
        from meeting.llm import entra_token_provider

        return cls(
            settings.speech_endpoint,
            token=entra_token_provider(),
            locale=settings.speech_locale,
            region=settings.speech_region,
            poll_seconds=settings.speech_poll_seconds,
            wait_seconds=settings.speech_wait_seconds,
        )

    # ---- the three calls the job makes -------------------------------------------------------------------------

    def submit(self, audio_url: str, *, display_name: str, speakers: int) -> str:
        """Start a job for one recording; returns the job's URL (its `self`), which the record keeps."""
        body = {
            "displayName": display_name,
            "locale": self.locale,
            "contentUrls": [audio_url],
            "properties": {
                "channels": [0],  # mono meetings; diarization works on one channel only
                "diarization": {"enabled": True, "maxSpeakers": speakers_hint(speakers)},
                "wordLevelTimestampsEnabled": False,  # phrase times are what the evidence cites (D14)
                "displayFormWordLevelTimestampsEnabled": False,
                "punctuationMode": "DictatedAndAutomatic",
                "profanityFilterMode": "None",  # minutes keep what was said, as Whisper's transcript does
                "timeToLiveHours": TIME_TO_LIVE_HOURS,
            },
        }
        job = self._api(
            "POST", f"{self.origin}/speechtotext/transcriptions:submit?api-version={API_VERSION}", body
        ).json()
        url = job.get("self")
        if not url:
            raise SpeechError("the submit answer has no job URL")
        self._check_origin(url)
        log.info("speech job submitted for %s (status %s)", display_name, job.get("status"))
        return url

    def wait(self, job_url: str, *, names: tuple[str, ...] = ()) -> Transcript:
        """Poll the job until it ends, at most `wait_seconds`, then read its transcript."""
        self._check_origin(job_url)
        deadline = self._clock() + self.wait_seconds
        while True:
            job = self._api("GET", job_url).json()
            status = job.get("status")
            if status == "Succeeded":
                return self._transcript(job, names)
            if status == "Failed":
                error = (job.get("properties") or {}).get("error") or {}
                raise SpeechJobFailed(error.get("code") or "Unknown", (error.get("message") or "")[:200])
            if self._clock() + self.poll_seconds > deadline:
                raise TranscriptionPending(f"speech job still {status} after {self.wait_seconds} s")
            self._sleep(self.poll_seconds)

    def delete(self, job_url: str) -> None:
        """Delete the job and its results on the service (they are stored as our transcript by now)."""
        self._check_origin(job_url)
        try:
            self._api("DELETE", job_url)
        except SpeechJobGone:
            pass

    # ---- reading the result ------------------------------------------------------------------------------------

    def _transcript(self, job: dict, names: tuple[str, ...]) -> Transcript:
        files_url = (job.get("links") or {}).get("files")
        if not files_url:
            raise SpeechError("the finished job has no files link")
        files = self._files(files_url)
        results = [f for f in files if f.get("kind") == "Transcription"]
        if not results:  # the job succeeded but the one recording didn't: the report says why
            reports = [f for f in files if f.get("kind") == "TranscriptionReport"]
            detail = {}
            if reports:
                details = self._content(reports[0]).get("details") or [{}]
                detail = details[0]
            raise SpeechJobFailed(
                detail.get("errorKind") or "NoTranscription", (detail.get("errorMessage") or "")[:200]
            )
        if len(results) != 1:
            raise SpeechError(f"expected one transcription file, got {len(results)}")
        result = self._content(results[0])
        started, ended = _timestamp(job.get("createdDateTime")), _timestamp(job.get("lastActionDateTime"))
        audio_ms = result.get("durationMilliseconds") or (job.get("properties") or {}).get("durationMilliseconds", 0)
        return Transcript(
            segments=segments_from_result(result),
            language=job.get("locale") or self.locale,
            audio_seconds=round(audio_ms / 1000, 2),
            seconds=round((ended - started).total_seconds(), 2) if started and ended else 0.0,
            engine=self.name,
            warnings=[NO_PHRASE_LIST] if names else [],
        )

    def _files(self, url: str) -> list[dict]:
        out, next_url = [], url
        while next_url:
            self._check_origin(next_url)
            page = self._api("GET", next_url).json()
            out += page.get("values", [])
            next_url = page.get("@nextLink")
        return out

    def _content(self, entry: dict) -> dict:
        """A result file. Its contentUrl is a SAS URL on Microsoft-managed storage: fetched WITHOUT our token."""
        url = (entry.get("links") or {}).get("contentUrl")
        if not url:
            raise SpeechError(f"result file {entry.get('name')} has no contentUrl")
        try:
            response = self._client.get(url)
        except httpx.TransportError as exc:
            raise SpeechUnavailable(f"result file: {type(exc).__name__}") from None
        self._raise_for(response, "result file")
        return response.json()

    # ---- HTTP --------------------------------------------------------------------------------------------------

    def _check_origin(self, url: str) -> None:
        parts = urlsplit(url)
        if f"{parts.scheme}://{parts.netloc}" != self.origin:
            raise SpeechError(f"refusing to send the token to {parts.scheme}://{parts.netloc} (not SPEECH_ENDPOINT)")

    def _api(self, method: str, url: str, body: dict | None = None) -> httpx.Response:
        self._check_origin(url)
        headers = {"Authorization": f"Bearer {self.token()}"}
        try:
            response = self._client.request(method, url, json=body, headers=headers)
        except httpx.TransportError as exc:
            raise SpeechUnavailable(f"{method} speech: {type(exc).__name__}") from None
        self._raise_for(response, f"{method} speech")
        return response

    @staticmethod
    def _raise_for(response: httpx.Response, what: str) -> None:
        status = response.status_code
        if status < 400:
            return
        code = ""
        try:
            error = response.json().get("error") or {}
            inner = error.get("innerError") or {}
            code = inner.get("code") or error.get("code") or ""
        except ValueError:
            pass
        message = f"{what}: HTTP {status}" + (f" {code}" if code else "")
        if status == 404:
            raise SpeechJobGone(message)
        if status == 429 or status >= 500:
            raise SpeechUnavailable(message)
        raise SpeechError(message)  # 401/403 (a role still propagating), 400 (configuration): the host retries
