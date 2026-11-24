"""The Speech batch transcriber (D44-D46) against the documented API, served by scripts/fake_speech.py over real
HTTP: what it submits, how it waits, how it reads the result, and where its token goes."""

import json

import httpx
import pytest
from fake_speech import FIXTURES, FakeSpeech

from meeting.speech import (
    NO_PHRASE_LIST,
    SpeechError,
    SpeechJobFailed,
    SpeechJobGone,
    SpeechTranscriber,
    SpeechUnavailable,
    TranscriptionPending,
    segments_from_result,
    speakers_hint,
)
from meeting.transcript import stamp

AUDIO = "https://strecmeeting.blob.core.windows.net/incoming/m01-1/recording.wav"


@pytest.fixture
def fake():
    server = FakeSpeech().start()
    yield server
    server.stop()


class Clock:
    """time.monotonic and time.sleep for the poll loop, without waiting."""

    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def transcriber(url: str, clock: Clock | None = None, **kw) -> SpeechTranscriber:
    clock = clock or Clock()
    tokens = iter(range(1000))
    return SpeechTranscriber(
        url + "/",
        token=lambda: f"token-{next(tokens)}",
        region="uaenorth",
        sleep=clock.sleep,
        clock=lambda: clock.now,
        **kw,
    )


def test_submit_sends_the_plain_blob_url_and_the_documented_properties(fake):
    job_url = transcriber(fake.url).submit(AUDIO, display_name="m01-1", speakers=3)
    assert job_url.startswith(f"{fake.url}/speechtotext/transcriptions/") and "api-version=2025-10-15" in job_url
    (body,) = fake.submitted
    assert body["contentUrls"] == [AUDIO]  # no SAS: the Speech identity reads the blob (D3)
    assert (body["displayName"], body["locale"]) == ("m01-1", "en-US")
    props = body["properties"]
    assert props["diarization"] == {"enabled": True, "maxSpeakers": 3}  # 2025-10-15 names, not diarizationEnabled
    assert props["channels"] == [0] and 6 <= props["timeToLiveHours"] <= 744
    assert "destinationContainerUrl" not in props  # it would need a SAS and an open account (D3)
    assert fake.requests[0] == ("POST", "/speechtotext/transcriptions:submit", True)


def test_a_finished_job_becomes_the_transcript_in_time_order(fake):
    speech = transcriber(fake.url)
    transcript = speech.wait(speech.submit(AUDIO, display_name="m01-1", speakers=2), names=("Sara", "Omar"))
    texts = [s.text for s in transcript.segments]
    assert texts[0] == "Good morning, everyone. Let's go through the status."  # sorted, though served out of order
    assert len(texts) == 4  # the NoMatch phrase and the empty one are dropped
    assert [stamp(s.start) for s in transcript.segments] == ["00:00", "00:04", "00:10", "00:13"]
    second = transcript.segments[1]
    assert (second.start, second.end, second.speaker) == (4.1, 9.7, "Guest-1")
    assert {s.speaker for s in transcript.segments} == {"Guest-1", "Guest-2"}  # labels, never names (D6)
    assert (transcript.language, transcript.audio_seconds, transcript.seconds) == ("en-US", 21.4, 72.0)
    assert transcript.engine == "azure-speech batch 2025-10-15 uaenorth"
    assert transcript.warnings == [NO_PHRASE_LIST]  # the attendees couldn't be passed as hints (D44)


def test_no_names_no_warning(fake):
    speech = transcriber(fake.url)
    assert speech.wait(speech.submit(AUDIO, display_name="m", speakers=0)).warnings == []


def test_the_token_goes_to_the_speech_endpoint_only(fake):
    speech = transcriber(fake.url)
    speech.wait(speech.submit(AUDIO, display_name="m01-1", speakers=2))
    api = [r for r in fake.requests if r[1].startswith("/speechtotext/")]
    content = [r for r in fake.requests if r[1].startswith("/_content/")]
    assert api and all(token for _, _, token in api)
    assert content and not any(token for _, _, token in content)  # the SAS-URL result file: no Authorization


def test_a_link_to_another_host_is_refused_before_the_token_is_sent(fake):
    speech = transcriber(fake.url)
    with pytest.raises(SpeechError, match="refusing to send the token"):
        speech.wait("https://evil.example/speechtotext/transcriptions/x?api-version=2025-10-15")
    assert fake.requests == []


def test_a_submit_answer_that_points_elsewhere_is_refused():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json={"self": "https://evil.example/speechtotext/transcriptions/1", "status": "x"})

    speech = SpeechTranscriber(
        "https://spch.cognitiveservices.azure.com/",
        token=lambda: "t",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(SpeechError, match="refusing"):
        speech.submit(AUDIO, display_name="m", speakers=2)


def test_waiting_polls_until_the_job_ends(fake):
    fake.running_polls = 3
    clock = Clock()
    speech = transcriber(fake.url, clock, poll_seconds=15, wait_seconds=1200)
    assert speech.wait(speech.submit(AUDIO, display_name="m", speakers=2)).segments
    assert clock.slept == [15, 15, 15]


def test_a_job_still_running_at_the_end_of_the_wait_is_pending_not_failed(fake):
    fake.running_polls = 100
    clock = Clock()
    speech = transcriber(fake.url, clock, poll_seconds=15, wait_seconds=60)
    job = speech.submit(AUDIO, display_name="m", speakers=2)
    with pytest.raises(TranscriptionPending):
        speech.wait(job)
    assert sum(clock.slept) <= 60  # never waits past its budget
    assert len(fake.submitted) == 1


def test_a_failed_job_says_whether_the_recording_is_the_problem(fake):
    fake.outcome = "failed-audio"
    speech = transcriber(fake.url)
    with pytest.raises(SpeechJobFailed) as failed:
        speech.wait(speech.submit(AUDIO, display_name="m", speakers=2))
    assert (failed.value.code, failed.value.permanent) == ("InvalidAudioFormat", True)
    fake.outcome = "failed-transient"
    with pytest.raises(SpeechJobFailed) as failed:
        speech.wait(speech.submit(AUDIO, display_name="m", speakers=2))
    assert (failed.value.code, failed.value.permanent) == ("InternalServerError", False)


def test_a_succeeded_job_without_a_transcription_reads_the_report(fake):
    fake.outcome = "report-only"
    speech = transcriber(fake.url)
    with pytest.raises(SpeechJobFailed) as failed:
        speech.wait(speech.submit(AUDIO, display_name="m", speakers=2))
    assert (failed.value.code, failed.value.permanent) == ("InvalidAudioFormat", True)


def test_http_errors_are_classified(fake):
    speech = transcriber(fake.url)
    fake.next_status = [503]
    with pytest.raises(SpeechUnavailable):
        speech.submit(AUDIO, display_name="m", speakers=2)
    fake.next_status = [429]
    with pytest.raises(SpeechUnavailable):
        speech.submit(AUDIO, display_name="m", speakers=2)
    fake.next_status = [403]  # a role assignment still propagating: transient, but not waited for
    with pytest.raises(SpeechError) as error:
        speech.submit(AUDIO, display_name="m", speakers=2)
    assert type(error.value) is SpeechError
    with pytest.raises(SpeechJobGone):
        speech.wait(f"{fake.url}/speechtotext/transcriptions/nope?api-version=2025-10-15")


def test_no_connection_is_unavailable():
    speech = SpeechTranscriber("http://127.0.0.1:9/", token=lambda: "t")  # discard port: refused
    with pytest.raises(SpeechUnavailable):
        speech.submit(AUDIO, display_name="m", speakers=2)


def test_delete_removes_the_job_and_tolerates_one_already_gone(fake):
    speech = transcriber(fake.url)
    job = speech.submit(AUDIO, display_name="m", speakers=2)
    speech.delete(job)
    speech.delete(job)  # 404 the second time: fine
    assert [j["deleted"] for j in fake.jobs.values()] == [True]
    with pytest.raises(SpeechJobGone):
        speech.wait(job)


def test_every_call_gets_a_fresh_token_from_the_provider(fake):
    seen = []

    def token() -> str:
        seen.append(1)
        return "t"

    speech = SpeechTranscriber(fake.url, token=token, sleep=lambda s: None)
    speech.wait(speech.submit(AUDIO, display_name="m", speakers=2))
    assert len(seen) == len(fake.api_calls())  # the provider caches and refreshes; the client never keeps a token


def test_speakers_hint_stays_within_the_api_limits():
    assert [speakers_hint(n) for n in (0, 1, 2, 7, 35, 80)] == [2, 2, 2, 7, 35, 35]


def test_other_channels_are_ignored():
    result = json.loads((FIXTURES / "contenturl_0.json").read_text())
    for phrase in result["recognizedPhrases"]:
        phrase["channel"] = 1
    assert segments_from_result(result) == []


def test_the_endpoint_must_be_a_url():
    with pytest.raises(ValueError):
        SpeechTranscriber("spch-meeting", token=lambda: "t")
