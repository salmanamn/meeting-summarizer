# Decisions index

Generated from the headings of [decisions.md](decisions.md) by `scripts/decisions_index.py`; don't edit it by
hand. `tests/unit/test_decisions.py` fails when this file and the headings disagree, or when a number is
missing or used twice.

14 decisions (D1–D14): 2 updated by a later one, 2 with a status of
their own (open questions, workarounds); the rest accepted as written.

| # | Decision | Status |
|---|---|---|
| [D1](decisions.md#d1--shape-a-recording-in-a-summary-out) | Shape: a recording in, a summary out | accepted |
| [D2](decisions.md#d2--transcription-on-the-laptop-faster-whisper-whisper-small-english) | Transcription on the laptop: faster-whisper, Whisper small, English | accepted |
| [D3](decisions.md#d3--transcription-on-azure-speech-batch-transcription-rest-api-2025-10-15) | Transcription on Azure: Speech batch transcription, REST API 2025-10-15 | planned for M6: checked against the docs on 2026-11-21, not run yet |
| [D4](decisions.md#d4--the-summary-contract-strict-schema-limits-afterwards-grounded-in-the-transcript) | The summary contract: strict schema, limits afterwards, grounded in the transcript | accepted; updated by D14 |
| [D5](decisions.md#d5--the-model-one-openai-compatible-client) | The model: one OpenAI-compatible client | accepted |
| [D6](decisions.md#d6--owners-come-from-what-was-said-not-from-who-spoke) | Owners come from what was said, not from who spoke | accepted |
| [D7](decisions.md#d7--test-meetings-are-synthetic-scripted-and-carry-their-answers) | Test meetings are synthetic, scripted, and carry their answers | accepted; updated by D14 |
| [D8](decisions.md#d8--configuration-from-environment-variables-the-local-lab) | Configuration from environment variables; the local lab | accepted |
| [D9](decisions.md#d9--model-files-are-pinned-by-a-lock-reused-from-project-4) | Model files are pinned by a lock, reused from Project 4 | accepted |
| [D10](decisions.md#d10--one-dependency-group-per-job) | One dependency group per job | accepted |
| [D11](decisions.md#d11--a-decisions-index-from-day-one) | A decisions index from day one | accepted |
| [D12](decisions.md#d12--hosting-on-azure-flex-consumption-so-the-blob-trigger-is-the-event-grid-one) | Hosting on Azure: Flex Consumption, so the Blob trigger is the Event Grid one | proposed: confirmed or changed in M2 |
| [D13](decisions.md#d13--long-recordings-pieces-cut-at-pauses-word-times-sentences-as-segments) | Long recordings: pieces cut at pauses, word times, sentences as segments | accepted |
| [D14](decisions.md#d14--evidence-is-an-enum-of-the-transcripts-times-an-unnamed-owner-stays-empty-updates-d4-d7) | Evidence is an enum of the transcript's times; an unnamed owner stays empty | accepted; updates D4, D7 |
