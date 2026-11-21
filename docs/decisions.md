# Decisions

## D1 — Shape: a recording in, a summary out
- A meeting recording (and, from M3, optional PDF or DOCX attachments) is uploaded to Blob storage. A Python Function triggered by the new blob transcribes it, asks an LLM for a summary in a fixed JSON shape (decisions, action items with owners, open questions), and stores the result in Cosmos DB. One recording is one job.
- M1 runs the same steps in one process on the laptop (`scripts/summarize_file.py`) to prove the models and measure them; the Function, the trigger and the stores come in M2.
- Same rule as the earlier projects: the code that runs on the laptop runs in the Functions host and on Azure; only configuration differs (D8).

## D2 — Transcription on the laptop: faster-whisper, Whisper small, English
- faster-whisper 1.2.1 on CTranslate2 4.9, CPU, int8, Whisper small (`stt-small`): the model and the PyAV pin (`av<19`) measured and chosen in Project 4. Meetings are English to start (`STT_LANGUAGE=en`; empty lets Whisper detect the language from the first 30 seconds).
- Long-form audio: how Whisper goes through a whole recording is D13. Either way the voice-activity filter removes silence first, and no piece is conditioned on the previous text, so one misheard piece cannot repeat through the rest.
- Timestamps are kept per segment: the summary cites them as evidence (D4).
- The attendees' names go to Whisper as hotwords on every window. Without them, Whisper small wrote "Lina" in the first minute and "Lena" later in the same recording; the owner of an action item is only as good as the spelling of the name (D6).

## D3 — Transcription on Azure: Speech batch transcription, REST API 2025-10-15
- **Status:** planned for M6: checked against the docs on 2026-11-21, not run yet
- Batch transcription is the Speech API made for recordings in storage: an asynchronous job (submit, then poll or receive a web hook), with diarization. The current GA version of the speech to text REST API is `2025-10-15` (`/speechtotext/transcriptions:submit?api-version=2025-10-15`); `v3.0` and the `3.2` previews were retired on 2026-03-31, so nothing older is used.
- Region (Speech regions table, speech to text tab): `uaenorth` has real-time and batch transcription, and neither fast transcription nor Whisper via batch transcription. Fast transcription (synchronous, under 2 hours) would be simpler but is not in the lab's region; batch it is.
- Audio access without keys or SAS: the Speech resource's **system-assigned** identity (a user-assigned one is not supported for this) gets Storage Blob Data Reader on the recordings account, the account allows that Speech resource as a resource instance (trusted Azure services), and the job gets a plain blob URL. `destinationContainerUrl` is not used: it needs a SAS and an account open to all networks; results are read from the job's result files instead.
- The Function talks to a `Transcriber` interface (`src/meeting/stt.py`), so the Azure transcriber replaces faster-whisper by configuration. Whisper inside the Function on Azure stays possible and is measured against batch transcription in M7.

## D4 — The summary contract: strict schema, limits afterwards, grounded in the transcript
- `src/meeting/summary.py`: `MeetingSummary` = `title`, `overview`, `decisions[]` (`text`, `evidence`), `action_items[]` (`task`, `owner`, `due`, `evidence`), `open_questions[]` (`question`, `evidence`).
- `SUMMARY_JSON_SCHEMA` is sent as `response_format: json_schema` with `strict: true`, inside Azure OpenAI's strict subset: every object lists all properties as required and sets `additionalProperties: false`; optional values are `["string", "null"]`; no length keywords. Lengths and counts are enforced afterwards by Pydantic (`extra="forbid"`). Unit tests keep the schema and the models naming the same fields.
- Grounding after validation (`ground()`): an evidence timestamp must fall inside a transcript segment, and an owner must be named in the transcript or be an attendee; otherwise the field becomes null and a warning says why. Items are kept, only the unsupported field goes. Empty lists are a valid answer, and a meeting where nothing was decided must produce none (D7).
- The transcript is untrusted input (anyone in a meeting can say "ignore your instructions"): it goes inside a `<transcript>` block that its own text cannot close, and the system prompt says it is data. Errors about an invalid answer name the field and the problem, never the content.
- Transcripts longer than `TRANSCRIPT_MAX_CHARS` (40,000 characters, roughly an hour of speech) are refused before any model call; splitting long meetings is M3's work. An answer cut off by the token limit is reported as such.

## D5 — The model: one OpenAI-compatible client
- One `openai` SDK client (as in Projects 3 and 4): Ollama's `/v1` locally, the Azure OpenAI v1 endpoint with Entra ID on Azure. `CHAT_REASONING_EFFORT` switches the request to the reasoning-model shape (`reasoning_effort` + `max_completion_tokens`, no `temperature`); empty locally.
- Local model to start: `phi4-mini:3.8b` on Ollama 0.40.15 (MIT, no thinking mode, already on disk from Projects 3 and 4), temperature 0, at most 1,500 output tokens, 16k context. Azure: gpt-5.4-mini (Project 3 D19). Comparing models on real meetings is M3.

## D6 — Owners come from what was said, not from who spoke
- Whisper does not tell speakers apart, and Azure's diarization labels speakers `Guest-1`, `Guest-2`, not by name. A name only reaches the summary when someone says it ("Omar, please send…") or when it is on the attendee list. So the owner of an action item is the name the meeting gives it; "I will update the release notes" has an owner only if the speaker can be identified from the text.
- Speaker labels, when a transcriber provides them, are shown in the transcript (`[00:12] Guest-1: …`); they are never turned into names.

## D7 — Test meetings are synthetic, scripted, and carry their answers
- `eval/meetings/<ID>.json` holds a script (speaker, line) and what a correct summary contains (`expect`: number of decisions and open questions, each action item's owner and task keywords). `scripts/make_meeting.py` speaks it with Piper, one voice per participant from the multi-speaker `en_US-libritts_r-medium` model (904 speakers; dataset licence CC BY 4.0), a 0.7 s pause between turns, fixed seed.
- M01: a planning meeting with 2 decisions, 3 action items, 2 open questions. M02: a status check where nothing is decided or assigned, which catches a model that invents items.
- What this measures: the pipeline end to end, and whether the summary finds what is certainly there. Not recognition of real speakers (clean synthetic audio, no overlap or noise) and not summary quality in general: real recordings and a scored evaluation come in M3.
- The M1 check (`src/meeting/expect.py`): transcript WER ≤ 15 % against the script; counts within one of the script, but zero must be exactly zero; every scripted action item found with its owner and a keyword; at most one action item more than the script.

## D8 — Configuration from environment variables; the local lab
- `src/meeting/settings.py` reads everything from the environment; the defaults are the laptop values.
- `docker-compose.yml` (project `meeting-lab`): Azurite 3.37.0 and the Cosmos DB vNext emulator (the digest pinned in Project 3) always; Ollama with `--profile ai`. Ports bound to 127.0.0.1 and the same as the ticket-triage lab's, so the two labs never run together. Emulator well-known keys only in local files that are gitignored or that say they are the emulator's.

## D9 — Model files are pinned by a lock, reused from Project 4
- `src/meeting/modelstore.py`, `src/meeting/download.py` and `scripts/fetch_models.py` come from Project 4 (its D4 and D33: lock with revision and SHA-256 per file, resumable downloads). The lock entries for `stt-small` and `stt-tiny` are copied from Project 4's lock, so the files already on disk there are the same bytes here.
- New entry: `tts-en-libritts`, for the test meetings only.

## D10 — One dependency group per job
- `pyproject.toml`: the package itself needs only `pydantic` and `openai`; `stt` (faster-whisper, PyAV), `storage` (Blob, Cosmos), `fixtures` (Piper), `models` (hub client), `dev`. The Function app (M2) ships the package with `stt` and `storage`. Piper is GPL and only makes test meetings on the laptop, so it never ships.

## D11 — A decisions index from day one
- `docs/decisions-index.md` is generated from the headings of this file by `scripts/decisions_index.py` (Project 4's script, D58 there), and `tests/unit/test_decisions.py` fails when the index is stale or a number is missing or repeated. A decision's status lives in the decision (`- **Status:** …`); updates are new decisions whose heading says `(updates Dx)`.

## D12 — Hosting on Azure: Flex Consumption, so the Blob trigger is the Event Grid one
- **Status:** proposed: confirmed or changed in M2
- Flex Consumption is the serverless plan for Python 3.13 (Linux Consumption gets no Python above 3.12 and is retiring; Project 3 D1), and it supports only the event-based Blob trigger: `@app.blob_trigger(..., source="EventGrid")` with an Event Grid subscription on the storage account that calls the Functions blob extension's webhook. The polling trigger (`LogsAndContainerScan`) is not available there.
- Locally there is no Event Grid. To keep the same trigger code in both places, M2 adds a small stub (as in Project 3) that watches Azurite and posts `BlobCreated` events to the local webhook.
- Open for M2: a long recording on the Function (Flex has a 30-second host start limit and a configurable function timeout), where faster-whisper's model files live on Azure, and whether the job is split into stages (transcribe, then summarise) so a retry does not redo the transcription.

## D13 — Long recordings: pieces cut at pauses, word times, sentences as segments
- faster-whisper has two ways through a recording. `sequential` is Whisper's own: a 30-second window that slides on by the timestamps the model writes. `batched` (`BatchedInferencePipeline`) cuts the recording at pauses into pieces of at most 30 seconds and transcribes each on its own.
- Measured on M01 (`scripts/stt_modes.py`, the same script spoken with Piper seeds 0–4): on the laptop (`docs/evidence/m1-stt-modes.md`, i7-9750H, 8 threads) `sequential` went above 15 % WER in 1 of 5 runs (24.9 %) and took 48–119 s per run against 27–37 s for `batched`; in the sandbox run that set this decision (2 vCPU) it was 3 of 5 (20–45 %). Each time it skipped ahead: whole lines, including a decision and an action item, were missing from the transcript. A transcript that drops lines silently is the worst failure for a summarizer, because the summary looks complete. (`scripts/stt_modes.py`, the same script spoken with Piper seeds 0–4, `docs/evidence/m1-stt-modes.md`): `sequential` went above 15 % WER in 3 of 5 runs (20–45 %), each time by skipping ahead: whole lines, including a decision and an action item, were missing from the transcript. A transcript that drops lines silently is the worst failure for a summarizer, because the summary looks complete.
- `batched` with segment timestamps (timestamp tokens inside each piece) skipped once in 5 (13 %; measured while choosing, not kept as evidence). `batched` as plain text, with times from word alignment afterwards, stayed at 3–5 % in all 5 runs and was faster than `sequential`: that is the default (`STT_MODE=batched`). Word alignment uses the model's cross-attention after decoding, so it cannot change the words; it needs `alignment_heads` in the model's `config.json` (the Systran conversion has them; the transcriber refuses a model without).
- The timed words are regrouped into sentences (at `.`, `?`, `!`): those are the segments, and the evidence times the summary cites. `sequential` stays selectable for comparison.

## D14 — Evidence is an enum of the transcript's times; an unnamed owner stays empty (updates D4, D7)
- First real run (M01 on `phi4-mini:3.8b`, 2026-11-21, `docs/evidence/m1-M01.md`): all 7 evidence fields held quotes from the transcript instead of `mm:ss` times, one of them 130 words long. Grounding removed every one (D4 worked), so the summary kept no evidence at all, and the quotes cost output tokens (622 completion tokens, 174 s on 8 threads).
- The schema is now built per transcript (`summary_schema(stamps)`): `evidence` is `anyOf` [a string `enum` of the transcript's segment times, `null`]. Locally Ollama turns the schema into a grammar, so any other value cannot be generated; Azure strict mode supports `enum` and `anyOf` the same way (`pattern` it does not). `ground()` still checks the result. The enum grows with the transcript; Azure's limits on enum size meet the long-meeting work in M3, where transcripts are split anyway.
- The same run gave "I will update the release notes" the owner `Unknown`, which grounding removed (D4 again). That line names nobody, and the summary cannot know who spoke (D6), so the script's answer for it is now `owner: null`: the check requires the item and requires it to have no owner. A guessed name would fail it, even the right one, because nothing in the words supports it.
- Not changed: the prompt. One run is not an evaluation (D7); prompt work comes with M3's.
