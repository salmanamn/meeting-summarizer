# M2: meeting jobs through the Functions host on the laptop

## A. Upload, then a summary (laptop restarted during the summary): `m01-1`

- Checked 2026-11-21 19:27 UTC through GET /api/meetings/m01-1; result: failed

    m01-1  received     1 file(s), 84.2 s of audio
    m01-1  transcribed  30 segments, 84.2 s of audio in 16.6 s (faster-whisper stt-small batched; Whisper runs so far: 1)
    m01-1  failed       retries_exhausted at transcribed: APITimeoutError on attempt 5 of 5 (retryable)
    m01-1  attempts 5, deliveries 5, ignored uploads 0, earlier errors 0

## A2. The same folder again after the model timeouts: `m01-1`

- Checked 2026-11-21 20:07 UTC through GET /api/meetings/m01-1; result: summarised

    m01-1  received     1 file(s), 84.2 s of audio
    m01-1  transcribed  30 segments, 84.2 s of audio in 16.6 s (faster-whisper stt-small batched; Whisper runs so far: 1)
    m01-1  summarised   phi4-mini:3.8b, 52.0 s, 417 completion tokens
    m01-1  attempts 1, deliveries 6, ignored uploads 0, earlier errors 1
    title     Pearl Pay Mobile App v2 Release Planning Meeting
    overview  The meeting focused on planning the release of version 2 of the Pearl Pay Mobile app, discussing bug fixes, feature decisions, and release details. The team decided to drop the dark mode feature for this release and move it to version 2.1, and they discussed the upcoming all-hands meeting presentation.
    decision  [00:30] Release version 2 on the 15th of March
    decision  [01:00] Drop the dark mode feature from this release and move it to version 2.1
    decision  [01:04] Update the release notes and share them with the support team next Monday
    action    [00:26] Omar: Send analytics numbers to the team (due: Wednesday Next, the 15th of March (00:27 mentioned as 'Wednesday'))
    action    [00:51] Lina: Get new icons approved by Friday (due: Friday)
    action    [01:04] (no owner): Update release notes and share with support team (due: Next Monday)
    question  [01:20] Who will present the release at the all-hands meeting?
    question  [01:11] Will the price change for international transfers be included in version 2?
    grounding   action_items[2]: owner 'Unknown' is not named in the transcript, removed

## B. The same event delivered twice: `m01-1`


- Checked 2026-11-21 20:07 UTC through GET /api/meetings/m01-1; result: summarised

    m01-1  received     1 file(s), 84.2 s of audio
    m01-1  transcribed  30 segments, 84.2 s of audio in 16.6 s (faster-whisper stt-small batched; Whisper runs so far: 1)
    m01-1  summarised   phi4-mini:3.8b, 52.0 s, 417 completion tokens
    m01-1  attempts 1, deliveries 7, ignored uploads 0, earlier errors 1
    title     Pearl Pay Mobile App v2 Release Planning Meeting
    overview  The meeting focused on planning the release of version 2 of the Pearl Pay Mobile app, discussing bug fixes, feature decisions, and release details. The team decided to drop the dark mode feature for this release and move it to version 2.1, and they discussed the upcoming all-hands meeting presentation.
    decision  [00:30] Release version 2 on the 15th of March
    decision  [01:00] Drop the dark mode feature from this release and move it to version 2.1
    decision  [01:04] Update the release notes and share them with the support team next Monday
    action    [00:26] Omar: Send analytics numbers to the team (due: Wednesday Next, the 15th of March (00:27 mentioned as 'Wednesday'))
    action    [00:51] Lina: Get new icons approved by Friday (due: Friday)
    action    [01:04] (no owner): Update release notes and share with support team (due: Next Monday)
    question  [01:20] Who will present the release at the all-hands meeting?
    question  [01:11] Will the price change for international transfers be included in version 2?
    grounding   action_items[2]: owner 'Unknown' is not named in the transcript, removed

## B2. The replay from Step 11 (the same event again): `m01-1`


- Checked 2026-11-21 20:46 UTC through GET /api/meetings/m01-1; result: summarised

    m01-1  received     1 file(s), 84.2 s of audio
    m01-1  transcribed  30 segments, 84.2 s of audio in 16.6 s (faster-whisper stt-small batched; Whisper runs so far: 1)
    m01-1  summarised   phi4-mini:3.8b, 52.0 s, 417 completion tokens
    m01-1  attempts 1, deliveries 8, ignored uploads 0, earlier errors 1
    title     Pearl Pay Mobile App v2 Release Planning Meeting
    overview  The meeting focused on planning the release of version 2 of the Pearl Pay Mobile app, discussing bug fixes, feature decisions, and release details. The team decided to drop the dark mode feature for this release and move it to version 2.1, and they discussed the upcoming all-hands meeting presentation.
    decision  [00:30] Release version 2 on the 15th of March
    decision  [01:00] Drop the dark mode feature from this release and move it to version 2.1
    decision  [01:04] Update the release notes and share them with the support team next Monday
    action    [00:26] Omar: Send analytics numbers to the team (due: Wednesday Next, the 15th of March (00:27 mentioned as 'Wednesday'))
    action    [00:51] Lina: Get new icons approved by Friday (due: Friday)
    action    [01:04] (no owner): Update release notes and share with support team (due: Next Monday)
    question  [01:20] Who will present the release at the all-hands meeting?
    question  [01:11] Will the price change for international transfers be included in version 2?
    grounding   action_items[2]: owner 'Unknown' is not named in the transcript, removed

## C. The folder uploaded again after the summary: `m01-1`

- Checked 2026-11-21 20:46 UTC through GET /api/meetings/m01-1; result: summarised

    m01-1  received     1 file(s), 84.2 s of audio
    m01-1  transcribed  30 segments, 84.2 s of audio in 16.6 s (faster-whisper stt-small batched; Whisper runs so far: 1)
    m01-1  summarised   phi4-mini:3.8b, 52.0 s, 417 completion tokens
    m01-1  attempts 1, deliveries 8, ignored uploads 1, earlier errors 1
    title     Pearl Pay Mobile App v2 Release Planning Meeting
    overview  The meeting focused on planning the release of version 2 of the Pearl Pay Mobile app, discussing bug fixes, feature decisions, and release details. The team decided to drop the dark mode feature for this release and move it to version 2.1, and they discussed the upcoming all-hands meeting presentation.
    decision  [00:30] Release version 2 on the 15th of March
    decision  [01:00] Drop the dark mode feature from this release and move it to version 2.1
    decision  [01:04] Update the release notes and share them with the support team next Monday
    action    [00:26] Omar: Send analytics numbers to the team (due: Wednesday Next, the 15th of March (00:27 mentioned as 'Wednesday'))
    action    [00:51] Lina: Get new icons approved by Friday (due: Friday)
    action    [01:04] (no owner): Update release notes and share with support team (due: Next Monday)
    question  [01:20] Who will present the release at the all-hands meeting?
    question  [01:11] Will the price change for international transfers be included in version 2?
    grounding   action_items[2]: owner 'Unknown' is not named in the transcript, removed

## D. Random bytes named .wav: `broken-1`

- Checked 2026-11-21 20:47 UTC through GET /api/meetings/broken-1; result: failed

    broken-1  failed       unsupported_type at received: broken.wav: its content is not one of wav, mp3, m4a, ogg, flac, webm
    broken-1  attempts 0, deliveries 1, ignored uploads 0, earlier errors 0

## E. A recording that differs from its manifest: `m02-1`

- Checked 2026-11-21 20:47 UTC through GET /api/meetings/m02-1; result: failed

    m02-1  failed       hash_mismatch at received: M02.wav: the SHA-256 differs from the manifest
    m02-1  attempts 0, deliveries 1, ignored uploads 0, earlier errors 0

## F. The same folder uploaded again, correctly: `m02-1`

- Checked 2026-11-21 20:48 UTC through GET /api/meetings/m02-1; result: summarised

    m02-1  received     1 file(s), 20.8 s of audio
    m02-1  transcribed  8 segments, 20.8 s of audio in 4.5 s (faster-whisper stt-small batched; Whisper runs so far: 1)
    m02-1  summarised   phi4-mini:3.8b, 44.8 s, 101 completion tokens
    m02-1  attempts 1, deliveries 2, ignored uploads 0, earlier errors 1
    title     Status Check Before Weekend
    overview  Lina and Omar had a brief status check before the weekend, discussing the progress of tests and designs, and inquiring about a response from the brand team before the holiday.
    question  [00:14] Will the brand team reply before the holiday?

## G. The model down: five attempts, then retries_exhausted: `m01-nollm`

- Checked 2026-11-21 20:50 UTC through GET /api/meetings/m01-nollm; result: failed

    m01-nollm  no job yet (waiting)
    m01-nollm  received     1 file(s), 84.2 s of audio
    m01-nollm  transcribed  30 segments, 84.2 s of audio in 16.3 s (faster-whisper stt-small batched; Whisper runs so far: 1)
    m01-nollm  failed       retries_exhausted at transcribed: APIConnectionError on attempt 5 of 5 (retryable)
    m01-nollm  attempts 5, deliveries 5, ignored uploads 0, earlier errors 0

## H. The same event again: a new round from the stored transcript: `m01-nollm`

- Checked 2026-11-21 20:52 UTC through GET /api/meetings/m01-nollm; result: summarised

    m01-nollm  received     1 file(s), 84.2 s of audio
    m01-nollm  transcribed  30 segments, 84.2 s of audio in 16.3 s (faster-whisper stt-small batched; Whisper runs so far: 1)
    m01-nollm  summarised   phi4-mini:3.8b, 93.3 s, 380 completion tokens
    m01-nollm  attempts 1, deliveries 6, ignored uploads 0, earlier errors 1
    title     Planning Meeting for Pearl Pay Mobile App v2 Release
    overview  The meeting focused on discussing the test results for the Pearl Pay Mobile app's v2 release, addressing bugs, especially in the payment screen, and making decisions on features and release details. The team decided to drop the dark mode feature for this release and postponed the decision on the price change for international transfers.
    decision  [00:30] Release version 2 on the 15th of March
    decision  [01:00] Drop the dark mode feature from this release and move it to version 2.1
    action    [00:27] Omar: Omar to send analytics numbers to the team (due: Wednesday Next, the 15th of March)
    action    [00:51] Lina: Lina to get new icons approved by Friday (due: Friday)
    action    [01:04] (no owner): Update and share release notes with the support team (due: Next Monday)
    question  [01:20] Who will present the release at the all hands meeting?
    question  [01:11] Will the price change for international transfers be included in version 2?
    grounding   action_items[2]: owner 'Unknown' is not named in the transcript, removed

## I. The host killed during speech to text: `m01-crash`

- Checked 2026-11-21 21:05 UTC through GET /api/meetings/m01-crash; result: summarised

    m01-crash  received     1 file(s), 84.2 s of audio
    m01-crash  transcribed  30 segments, 84.2 s of audio in 14.5 s (faster-whisper stt-small batched; Whisper runs so far: 1)
    m01-crash  summarised   phi4-mini:3.8b, 52.6 s, 417 completion tokens
    m01-crash  attempts 2, deliveries 2, ignored uploads 0, earlier errors 0
    title     Pearl Pay Mobile App v2 Release Planning Meeting
    overview  The meeting focused on planning the release of version 2 of the Pearl Pay Mobile app, discussing bug fixes, feature decisions, and release details. The team decided to drop the dark mode feature for this release and move it to version 2.1, and they discussed the upcoming all-hands meeting presentation.
    decision  [00:30] Release version 2 on the 15th of March
    decision  [01:00] Drop the dark mode feature from this release and move it to version 2.1
    decision  [01:04] Update the release notes and share them with the support team next Monday
    action    [00:26] Omar: Send analytics numbers to the team (due: Wednesday Next, the 15th of March (00:27 mentioned as 'Wednesday'))
    action    [00:51] Lina: Get new icons approved by Friday (due: Friday)
    action    [01:04] (no owner): Update release notes and share with support team (due: Next Monday)
    question  [01:20] Who will present the release at the all-hands meeting?
    question  [01:11] Will the price change for international transfers be included in version 2?
    grounding   action_items[2]: owner 'Unknown' is not named in the transcript, removed

