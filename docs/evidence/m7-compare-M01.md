# M7: Speech against Whisper on M01 (Azure job `m7-m01-1`)

- Compared 2026-11-24 23:39 UTC by scripts/compare_engines.py (D50). Synthetic meeting from a script (D7): one meeting is a smoke test of the comparison, not a quality ranking.
- Attendees on the manifest: Sara, Omar, Lina. Whisper got them as hotwords; Speech batch transcription takes no phrase list (D44).
- `laptop/*` summaries use the stack's chat deployment from the laptop (D49), so `laptop/speech` against `laptop/whisper` differs only in the transcript; `azure` against `laptop/speech` only in the model's own variation.

## Transcripts

| Transcript | Engine | Segments | Words | Audio s | Took s | WER vs script | Speakers found | Names heard |
|---|---|---|---|---|---|---|---|---|
| speech | azure-speech batch 2025-10-15 uaenorth | 35 | 267 | 84.2 | 95.0 | 5.2% | 3 (script: 3) | 1 of 3: Omar |
| whisper | faster-whisper stt-small batched | 30 | 267 | 84.2 | 28.6 | 4.5% | none (script: 3) | 2 of 3: Omar, Lina |

## Summaries

| Summary | Transcript | Model | Decisions | Actions | Questions | Owners | Checks passed | Grounding fixes | Took s | Completion tokens |
|---|---|---|---|---|---|---|---|---|---|---|
| azure | speech | gpt-5.4-mini | 2 | 3 | 2 | Omar, (none), (none) | 11 of 8 | 3 | 2.9 | 358 |
| laptop/speech | speech | gpt-5.4-mini | 3 | 3 | 2 | Omar, (none), (none) | 11 of 8 | 4 | 7.1 | 516 |
| laptop/whisper | whisper | gpt-5.4-mini | 2 | 3 | 2 | Omar, Lina, (none) | 11 of 8 | 1 | 2.7 | 438 |

### speech: first 8 lines

    [00:00] Guest-1: Good morning, everyone.
    [00:01] Guest-1: This is the planning meeting for the version 2 release of the Pearl Pay mobile app.
    [00:05] Guest-1: Omar, Lena, thanks for joining.
    [00:07] Guest-2: Morning.
    [00:08] Guest-2: I have the test results from last week so I can start with those.
    [00:11] Guest-1: Please go ahead.
    [00:13] Guest-2: I found three bugs in the payment screen.
    [00:15] Guest-2: 2 are fixed, the third one only happens on older Android phones and we are still looking at it.

### whisper: first 8 lines

    [00:00] Good morning, everyone.
    [00:01] This is the planning meeting for the version 2 release of the Pearl Pay Mobile app.
    [00:05] Omar, Lina, thanks for joining.
    [00:07] Morning.
    [00:08] I have the test results from last week, so I can start with those.
    [00:11] Please go ahead.
    [00:13] I have three bugs in the payment screen.
    [00:15] Two are fixed.

### azure

    title     Pearl Pay v2 release planning
    overview  The team reviewed test results, discussed a few release-blocking issues, and set the plan for the Pearl Pay mobile app version 2 release. They agreed on the release date, removed Dark mode from this release, and left the international transfer price change and All Hands presenter unresolved.
    decision  [00:42] Release version 2 on the 15th of March.
    decision  [00:56] Drop the Dark mode feature from this release and move it to version 2.1.
    action    [00:26] Omar: Pull the numbers from the analytics dashboard and send them to the team (due: by Wednesday)
    action    [00:48] (no owner): Get the new icons approved (due: by Friday)
    action    [01:05] (no owner): Update the release notes and share them with the support team (due: next Monday)
    question  [01:09] Will the price change for international transfers be in version 2?
    question  [01:17] Who will present the release at the All Hands meeting?

- OK: transcript WER 5.2% <= 15%
- OK: decisions: 2 of 2 expected found (2 in the summary)
- OK: action_items: 3 of 3 expected found (3 in the summary)
- OK: open_questions: 2 of 2 expected found (2 in the summary)
- FAIL: owner right on 2 of 3 found items
- OK: due right on 3 of 3 found items
- OK: evidence right on 7 of 7 found items
- OK: forbidden items: 0
- grounding: action_items[1]: owner 'Lina' is not named where the task is said, removed
- grounding: action_items[2]: owner 'Sara' is not named where the task is said, removed
- grounding: open_questions[0]: evidence '01:11' (a line that says less of it) moved to '01:09'

### laptop/speech

    title     Version 2 release planning
    overview  The team reviewed bug status, release readiness, and a few release decisions for the Pearl Pay mobile app version 2. They ended by setting the release date, removing Dark mode from this release, and assigning follow-up work on analytics, icons, and release notes. Two items were left unresolved: whether the international transfer price change is included and who will present at All Hands.
    decision  [00:42] Version 2 will be released on the 15th of March.
    decision  [00:56] The Dark mode feature will be dropped from this release and moved to version 2.1.
    decision  [01:09] The price change for international transfers will be kept open for now.
    action    [00:26] Omar: Send the analytics numbers for older Android phone usage to the team (due: by Wednesday)
    action    [00:48] (no owner): Get the new icons approved (due: by Friday)
    action    [01:05] (no owner): Update the release notes and share them with the support team (due: next Monday)
    question  [01:09] Will the price change for international transfers be in version 2?
    question  [01:17] Who will present the release at the All Hands meeting?

- OK: transcript WER 5.2% <= 15%
- OK: decisions: 2 of 2 expected found (3 in the summary)
- OK: action_items: 3 of 3 expected found (3 in the summary)
- OK: open_questions: 2 of 2 expected found (2 in the summary)
- FAIL: owner right on 2 of 3 found items
- OK: due right on 3 of 3 found items
- OK: evidence right on 7 of 7 found items
- OK: forbidden items: 0
- grounding: action_items[1]: owner 'Lina' is not named where the task is said, removed
- grounding: action_items[2]: owner 'Sara' is not named where the task is said, removed
- grounding: decisions[2]: evidence '01:15' (a line that says less of it) moved to '01:09'
- grounding: open_questions[0]: evidence '01:11' (a line that says less of it) moved to '01:09'

### laptop/whisper

    title     Version 2 Release Planning
    overview  The team reviewed test results for the Pearl Pay Mobile app version 2 release, including bugs on the payment screen and a possible issue on older Android phones. They then settled the release date, removed dark mode from this release, and left the international transfer price change and all-hands presenter unresolved.
    decision  [00:30] Version 2 will be released on the 15th of March.
    decision  [00:56] The dark mode feature will be dropped from this release and moved to version 2.1.
    action    [00:27] Omar: Send the analytics numbers on older Android phone usage to the team (due: by Wednesday)
    action    [00:30] Lina: Get the new icons approved (due: by Friday)
    action    [01:04] (no owner): Update the release notes and share them with the support team (due: next Monday)
    question  [01:09] Whether the price change for international transfers will be in version 2
    question  [01:17] Who will present the release at the all hands meeting

- OK: transcript WER 4.5% <= 15%
- OK: decisions: 2 of 2 expected found (2 in the summary)
- OK: action_items: 3 of 3 expected found (3 in the summary)
- OK: open_questions: 2 of 2 expected found (2 in the summary)
- OK: owner right on 3 of 3 found items
- OK: due right on 3 of 3 found items
- FAIL: evidence right on 5 of 7 found items
- OK: forbidden items: 0
- grounding: open_questions[0]: evidence '01:11' (a line that says less of it) moved to '01:09'
