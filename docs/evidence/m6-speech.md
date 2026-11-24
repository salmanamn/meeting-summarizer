# M6 evidence: Speech batch transcription and Entra ID, against stand-ins (D44-D47)

Written by the M6 runbook (Step 10) on 2026-11-24, branch m6-speech on top of main ad2dfaf. The Speech service itself was not called: its answers come from tests/fixtures/speech (documented, not recorded). First run on Azure: M7.

## Unit tests (all; the three new files)

```
330 passed, 11 deselected
43 passed
```

## Integration tests (Azurite, Cosmos emulator, fake_speech.py, fake_llm.py)

```
tests/integration/test_speech_ci.py::test_an_upload_is_transcribed_by_speech_and_summarised PASSED
tests/integration/test_speech_ci.py::test_a_long_job_is_waited_for_by_later_deliveries PASSED
tests/integration/test_speech_ci.py::test_a_recording_speech_can_t_read_fails_for_good PASSED
11 passed, 330 deselected
```

## Known-bad changes (tests_must_fail.py): the ten M6 ones and the total

```
KILLED   speech-submitted-every-delivery    tests/unit/test_job_speech.py
KILLED   speech-job-not-checkpointed        tests/unit/test_job_speech.py
KILLED   speech-reads-an-unchecked-blob     tests/unit/test_job_speech.py
KILLED   bad-recording-retried              tests/unit/test_job_speech.py
KILLED   speech-reuses-whisper-transcript   tests/unit/test_job_speech.py
KILLED   speech-wait-unbounded              tests/unit/test_speech.py
KILLED   token-sent-to-any-host             tests/unit/test_speech.py
KILLED   token-sent-to-the-result-storage   tests/unit/test_speech.py
KILLED   entra-setting-ignored              tests/unit/test_engines.py
KILLED   azure-falls-back-to-whisper        tests/unit/test_infra_contract.py
37/37 mutations killed
```
