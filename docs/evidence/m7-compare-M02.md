# M7: Speech against Whisper on M02 (Azure job `m7-m02-1`)

- Compared 2026-11-24 23:39 UTC by scripts/compare_engines.py (D50). Synthetic meeting from a script (D7): one meeting is a smoke test of the comparison, not a quality ranking.
- Attendees on the manifest: Lina, Omar. Whisper got them as hotwords; Speech batch transcription takes no phrase list (D44).
- `laptop/*` summaries use the stack's chat deployment from the laptop (D49), so `laptop/speech` against `laptop/whisper` differs only in the transcript; `azure` against `laptop/speech` only in the model's own variation.

## Transcripts

| Transcript | Engine | Segments | Words | Audio s | Took s | WER vs script | Speakers found | Names heard |
|---|---|---|---|---|---|---|---|---|
| speech | azure-speech batch 2025-10-15 uaenorth | 11 | 64 | 20.8 | 61.0 | 3.1% | 2 (script: 2) | 1 of 2: Omar |
| whisper | faster-whisper stt-small batched | 8 | 63 | 20.8 | 13.1 | 1.6% | none (script: 2) | 2 of 2: Lina, Omar |

## Summaries

| Summary | Transcript | Model | Decisions | Actions | Questions | Owners | Checks passed | Grounding fixes | Took s | Completion tokens |
|---|---|---|---|---|---|---|---|---|---|---|
| azure | speech | gpt-5.4-mini | 0 | 0 | 1 | - | 6 of 6 | 0 | 1.6 | 204 |
| laptop/speech | speech | gpt-5.4-mini | 0 | 0 | 1 | - | 6 of 6 | 0 | 4.1 | 178 |
| laptop/whisper | whisper | gpt-5.4-mini | 0 | 0 | 1 | - | 6 of 6 | 0 | 1.7 | 134 |

### speech: first 8 lines

    [00:00] Guest-1: Hi, Omar.
    [00:01] Guest-1: Just a quick status check before the weekend.
    [00:03] Guest-2: Hi Lena, nothing new from my side.
    [00:05] Guest-2: The tests are still running and everything looks normal so far.
    [00:09] Guest-1: Same here, the designs are where they were on Monday do.
    [00:11] Guest-2: You think the brand team will reply before the holiday?
    [00:14] Guest-1: I really don't know.
    [00:15] Guest-1: We will see.

### whisper: first 8 lines

    [00:00] Hi Omar, just a quick status check before the weekend.
    [00:03] Hi Lina, nothing new from my side.
    [00:05] The tests are still running and everything looks normal so far.
    [00:08] Same here, the designs are where they were on Monday.
    [00:11] You think the brand team will reply before the holiday?
    [00:14] I really don't know, we will see.
    [00:16] Okay, have a good weekend.
    [00:18] You too, bye.

### azure

    title     Weekend status check
    overview  Lina and Omar did a brief status check before the weekend. Omar said the tests were still running normally, and Lina said the designs were unchanged since Monday. The meeting ended with an open question about whether the brand team would reply before the holiday.
    question  [00:11] Will the brand team reply before the holiday?

- OK: transcript WER 3.1% <= 15%
- OK: decisions: 0 of 0 expected found (0 in the summary), must be 0
- OK: action_items: 0 of 0 expected found (0 in the summary), must be 0
- OK: open_questions: 1 of 1 expected found (1 in the summary)
- OK: evidence right on 1 of 1 found items
- OK: forbidden items: 0

### laptop/speech

    title     Status check before the weekend
    overview  Lina and Omar did a quick status check before the weekend. Omar said the tests were still running normally, and Lina said the designs had not changed since Monday. They ended without any new decisions, with only uncertainty about whether the brand team would reply before the holiday.
    question  [00:11] Will the brand team reply before the holiday?

- OK: transcript WER 3.1% <= 15%
- OK: decisions: 0 of 0 expected found (0 in the summary), must be 0
- OK: action_items: 0 of 0 expected found (0 in the summary), must be 0
- OK: open_questions: 1 of 1 expected found (1 in the summary)
- OK: evidence right on 1 of 1 found items
- OK: forbidden items: 0

### laptop/whisper

    title     Weekend Status Check
    overview  Lina and Omar did a brief status check before the weekend. They confirmed that the tests were still running normally and that the designs had not changed since Monday. The meeting ended with no new decisions, just an open question about whether the brand team would respond before the holiday.
    question  [00:11] Will the brand team reply before the holiday?

- OK: transcript WER 1.6% <= 15%
- OK: decisions: 0 of 0 expected found (0 in the summary), must be 0
- OK: action_items: 0 of 0 expected found (0 in the summary), must be 0
- OK: open_questions: 1 of 1 expected found (1 in the summary)
- OK: evidence right on 1 of 1 found items
- OK: forbidden items: 0
