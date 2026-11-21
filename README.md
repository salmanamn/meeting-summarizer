# meeting-summarizer

A meeting recording goes into Blob storage; out comes a summary you can act on: the **decisions**, the **action items with their owners**, and the **open questions**, as strict JSON in Cosmos DB, each item pointing at the moment in the recording that supports it. Built from open components on a laptop (faster-whisper, an LLM on Ollama, Azurite and the Cosmos DB emulator), then the same code serverless on Azure (Functions, Azure AI Speech batch transcription, Azure OpenAI).

**Status: M1 — the pipeline works in one process on the laptop.** No Function, trigger or stores yet.

| Step | Local | Planned on Azure |
|---|---|---|
| Recording arrives | Azurite blob container | Blob storage, Event Grid → Blob trigger (Flex Consumption) |
| Speech to text | faster-whisper 1.2.1, Whisper small, CPU, pieces cut at pauses | Azure AI Speech batch transcription (REST 2025-10-15), or the same Whisper |
| Summary | `phi4-mini:3.8b` on Ollama, strict JSON schema | gpt-5.4-mini on Azure OpenAI, strict structured outputs |
| Result | Cosmos DB emulator | Cosmos DB for NoSQL |

## Run it

Needs uv, Docker and about 3.5 GB of downloads on first use (packages, models).

    uv sync
    uv run python scripts/fetch_models.py stt-small tts-en-libritts
    uv run python scripts/make_meeting.py M01 M02            # synthetic test meetings -> out/meetings/
    docker compose --profile ai up -d && ./scripts/smoke-local.sh
    docker exec meeting-ollama ollama pull phi4-mini:3.8b
    uv run python scripts/summarize_file.py out/meetings/M01.wav --expect M01

`summarize_file.py` prints the transcript's numbers, the summary and the checks against the meeting's script; `out/M01.summary.json` is the result.

## What the summary promises

- The JSON shape is fixed (`src/meeting/summary.py`) and sent to the model as a strict schema; lengths and counts are checked after.
- Every evidence time must fall inside a transcript segment, and every owner must be a name that was said or is on the attendee list; anything else is removed and reported, never kept (D4).
- A meeting where nothing was decided gives empty lists: M02 is there to catch a model that invents.
- The transcript is treated as data: what is said in a meeting cannot change the instructions.

## What is measured so far

Two scripted meetings spoken by Piper with three voices ([eval/meetings](eval/meetings), D7) and the results in [docs/evidence](docs/evidence). Synthetic audio says nothing about real rooms, accents or people talking over each other; real recordings come in M3. One finding already shaped the code: Whisper's own sliding window silently dropped whole lines in 3 of 5 runs of the same meeting, so long recordings are cut at pauses instead (D13).

Design choices and their reasons: [docs/decisions.md](docs/decisions.md) ([index](docs/decisions-index.md)).