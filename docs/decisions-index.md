# Decisions index

Generated from the headings of [decisions.md](decisions.md) by `scripts/decisions_index.py`; don't edit it by
hand. `tests/unit/test_decisions.py` fails when this file and the headings disagree, or when a number is
missing or used twice.

43 decisions (D1–D43): 21 updated by a later one, 2 with a status of
their own (open questions, workarounds); the rest accepted as written.

| # | Decision | Status |
|---|---|---|
| [D1](decisions.md#d1--shape-a-recording-in-a-summary-out) | Shape: a recording in, a summary out | accepted |
| [D2](decisions.md#d2--transcription-on-the-laptop-faster-whisper-whisper-small-english) | Transcription on the laptop: faster-whisper, Whisper small, English | accepted |
| [D3](decisions.md#d3--transcription-on-azure-speech-batch-transcription-rest-api-2025-10-15) | Transcription on Azure: Speech batch transcription, REST API 2025-10-15 | planned for M6: checked against the docs on 2026-11-21, not run yet |
| [D4](decisions.md#d4--the-summary-contract-strict-schema-limits-afterwards-grounded-in-the-transcript) | The summary contract: strict schema, limits afterwards, grounded in the transcript | accepted; updated by D14, D23, D24, D25 |
| [D5](decisions.md#d5--the-model-one-openai-compatible-client) | The model: one OpenAI-compatible client | accepted |
| [D6](decisions.md#d6--owners-come-from-what-was-said-not-from-who-spoke) | Owners come from what was said, not from who spoke | accepted; updated by D29 |
| [D7](decisions.md#d7--test-meetings-are-synthetic-scripted-and-carry-their-answers) | Test meetings are synthetic, scripted, and carry their answers | accepted; updated by D14, D26 |
| [D8](decisions.md#d8--configuration-from-environment-variables-the-local-lab) | Configuration from environment variables; the local lab | accepted; updated by D20, D30, D34 |
| [D9](decisions.md#d9--model-files-are-pinned-by-a-lock-reused-from-project-4) | Model files are pinned by a lock, reused from Project 4 | accepted |
| [D10](decisions.md#d10--one-dependency-group-per-job) | One dependency group per job | accepted |
| [D11](decisions.md#d11--a-decisions-index-from-day-one) | A decisions index from day one | accepted |
| [D12](decisions.md#d12--hosting-on-azure-flex-consumption-so-the-blob-trigger-is-the-event-grid-one) | Hosting on Azure: Flex Consumption, so the Blob trigger is the Event Grid one | accepted; updated by D15 |
| [D13](decisions.md#d13--long-recordings-pieces-cut-at-pauses-word-times-sentences-as-segments) | Long recordings: pieces cut at pauses, word times, sentences as segments | accepted |
| [D14](decisions.md#d14--evidence-is-an-enum-of-the-transcripts-times-an-unnamed-owner-stays-empty-updates-d4-d7) | Evidence is an enum of the transcript's times; an unnamed owner stays empty | accepted; updates D4, D7; updated by D23, D25 |
| [D15](decisions.md#d15--the-upload-contract-the-manifest-goes-last-and-is-the-only-blob-that-triggers-updates-d12) | The upload contract: the manifest goes last and is the only blob that triggers | accepted; updates D12 |
| [D16](decisions.md#d16--limits-and-checks-before-any-model-runs) | Limits and checks before any model runs | accepted; updated by D22, D24 |
| [D17](decisions.md#d17--stores-one-job-record-per-meeting-in-cosmos-db-transcripts-as-blobs) | Stores: one job record per meeting in Cosmos DB, transcripts as blobs | accepted; updated by D38 |
| [D18](decisions.md#d18--stages-in-cosmos-rather-than-durable-functions-deliveries-are-at-least-once) | Stages in Cosmos rather than Durable Functions; deliveries are at least once | accepted; updated by D21 |
| [D19](decisions.md#d19--whisper-inside-the-function-on-azure-measured-now-decided-in-m7) | Whisper inside the Function on Azure: measured now, decided in M7 | open: decided in M7 with these numbers and M7's own; updated by D20, D37 |
| [D20](decisions.md#d20--lab-limits-ollama-capped-at-6-cpus-whisper-at-4-threads-updates-d8-d19) | Lab limits: Ollama capped at 6 CPUs, Whisper at 4 threads | accepted; updates D8, D19; updated by D30 |
| [D21](decisions.md#d21--a-model-error-waits-before-the-hosts-retry-updates-d18) | A model error waits before the host's retry | accepted; updates D18 |
| [D22](decisions.md#d22--attachments-docx-through-docling-pdf-through-its-text-layer-updates-d16) | Attachments: DOCX through Docling, PDF through its text layer | accepted; updates D16; updated by D33 |
| [D23](decisions.md#d23--attachments-in-the-prompt-background-with-references-never-the-source-of-a-decision-updates-d4-d14) | Attachments in the prompt: background with references, never the source of a decision | accepted; updates D4, D14; updated by D28 |
| [D24](decisions.md#d24--long-meetings-summarised-in-parts-cut-at-pauses-merged-without-a-second-summary-updates-d4-d16) | Long meetings: summarised in parts cut at pauses, merged without a second summary | accepted; updates D4, D16; updated by D28, D29 |
| [D25](decisions.md#d25--two-more-grounding-checks-due-in-the-meetings-words-a-decision-that-repeats-an-action-item-updates-d4-d14) | Two more grounding checks: `due` in the meeting's words, a decision that repeats an action item | accepted; updates D4, D14; updated by D28 |
| [D26](decisions.md#d26--the-evaluation-answers-per-meeting-scored-matching-gates-on-a-tuning-set-a-holdout-real-meetings-from-ami-updates-d7) | The evaluation: answers per meeting, scored matching, gates on a tuning set, a holdout, real meetings from AMI | accepted; updates D7 |
| [D27](decisions.md#d27--local-chat-models-compared-on-the-tuning-set) | Local chat models compared on the tuning set | accepted; updated by D33 |
| [D28](decisions.md#d28--tuning-round-1-from-the-first-phi4-mini-runs-on-the-tuning-set-updates-d23-d24-d25) | Tuning round 1, from the first phi4-mini runs on the tuning set | accepted; updates D23, D24, D25; updated by D29 |
| [D29](decisions.md#d29--tuning-round-2-from-the-four-models-runs-grounding-that-every-model-needs-updates-d6-d24-d28) | Tuning round 2, from the four models' runs: grounding that every model needs | accepted; updates D6, D24, D28; updated by D31, D32 |
| [D30](decisions.md#d30--ollama-on-the-laptops-gpu-opt-in-updates-d8-d20) | Ollama on the laptop's GPU, opt-in | accepted; updates D8, D20 |
| [D31](decisions.md#d31--tuning-round-3-from-granite43b-and-qwen354b-on-the-gpu-updates-d29) | Tuning round 3, from granite4:3b and qwen3.5:4b on the GPU | accepted; updates D29; updated by D32 |
| [D32](decisions.md#d32--tuning-round-4-from-the-round-3-runs-updates-d29-d31) | Tuning round 4, from the round-3 runs | accepted; updates D29, D31 |
| [D33](decisions.md#d33--the-local-model-qwen354b-with-thinking-off-m3-closes-with-two-gates-unmet-updates-d22-d27) | The local model: qwen3.5:4b, with thinking off; M3 closes with two gates unmet | accepted; updates D22, D27 |
| [D34](decisions.md#d34--ci-and-branch-protection-every-lab-image-pinned-by-digest-updates-d8) | CI and branch protection; every lab image pinned by digest | accepted; updates D8; updated by D43 |
| [D35](decisions.md#d35--known-bad-changes-must-fail) | Known-bad changes must fail | accepted |
| [D36](decisions.md#d36--the-pipeline-in-ci-the-labs-own-compose-file-whisper-tiny-a-stand-in-model) | The pipeline in CI: the lab's own compose file, Whisper tiny, a stand-in model | accepted; updated by D43 |
| [D37](decisions.md#d37--the-deployment-package-gate-updates-d19) | The deployment package gate | accepted; updates D19 |
| [D38](decisions.md#d38--the-azure-stack-in-terraform-one-composition-root-three-storage-accounts-updates-d17) | The Azure stack in Terraform: one composition root, three storage accounts | accepted; updates D17 |
| [D39](decisions.md#d39--network-posture-public-endpoints-entra-id-only-one-named-trusted-instance) | Network posture: public endpoints, Entra ID only, one named trusted instance | accepted |
| [D40](decisions.md#d40--the-manifest-subscription-a-system-topic-the-blobs-webhook-and-its-key) | The manifest subscription: a system topic, the blobs webhook, and its key | accepted |
| [D41](decisions.md#d41--models-and-speech-on-azure-settings-now-code-in-m6) | Models and speech on Azure: settings now, code in M6 | accepted |
| [D42](decisions.md#d42--identities-and-roles) | Identities and roles | accepted |
| [D43](decisions.md#d43--iac-checks-floci-az-checkov-conftest-known-bad-plans-updates-d34-d36) | IaC checks: floci-az, Checkov, Conftest, known-bad plans | accepted; updates D34, D36 |
