# M2: meeting jobs through the Functions host on the laptop

## A. Two attachments read at received, cited as sources: `m04-1`

- Checked 2026-11-22 21:24 UTC through GET /api/meetings/m04-1; result: summarised

    m04-1  no job yet (waiting)
    m04-1  received     3 file(s), 46.5 s of audio, attachments read: 7 block(s)
    m04-1  transcribed  1 segments, 46.5 s of audio in 12.1 s (faster-whisper stt-small batched; Whisper runs so far: 1)
    m04-1  summarised   phi4-mini:3.8b, 54.5 s, 353 completion tokens
    m04-1  attempts 1, deliveries 1, ignored uploads 0, earlier errors 0
    title     Website Launch Meeting
    overview  The meeting focused on finalizing the launch date for the new website, updating the campaign budget, and discussing the hiring of a freelance designer. The launch date was set for April 9th, the budget was updated with new figures, and the decision on hiring a freelance designer was postponed.
    decision  [00:00] We launch the new website on the 9th of April
    action    [00:00] Hana: Update the figures on page 2 of the budget sheet by Tuesday (due: Tuesday)
    action    [00:00] (no owner): Postpone the decision on hiring a freelance designer until next month
    question  [00:00] Do we need a freelance designer before the launch?
    grounding   decisions[1]: repeats the action item at 00:00, removed
    grounding   decisions[2]: repeats the action item at 00:00, removed

## B. A long meeting in parts: `m05-1`

- Checked 2026-11-22 21:28 UTC through GET /api/meetings/m05-1; result: summarised

    m05-1  no job yet (waiting)
    m05-1  received     1 file(s), 315.7 s of audio
    m05-1  transcribed  96 segments, 315.7 s of audio in 59.9 s (faster-whisper stt-small batched; Whisper runs so far: 1)
    m05-1  summarised   phi4-mini:3.8b, 149.2 s, 637 completion tokens, 2 parts + merge
    m05-1  attempts 1, deliveries 1, ignored uploads 0, earlier errors 0
    title     Pearl Pay Support Team Quarterly Planning
    overview  The Pearl Pay Support Team met to set quarterly goals, including extending chat support hours, creating new help center articles, and arranging training for a new refund process. Decisions were made to extend chat support hours, update the shift rota, write new articles, and book a training room. The lack of weekend staff was acknowledged and will be revisited in the summer.
    decision  [01:44] Chat support hours extended to 10 PM on weekdays starting from the 1st of March.
    action    [02:09] Omar: Update shift rota (due: By Thursday)
    action    [03:11] Lina: Write first two articles (due: By the end of the month)
    action    [04:28] Sara: Book training room (due: the 14th of March)
    question  [04:57] Will there be weekend cover in the summer?
    grounding   open_questions: Q1 at 03:25 answered later, removed
    grounding   open_questions: Q2 at 04:35 answered later, removed
    grounding   action_items[2]: due 'By the 14th of March' cut to the meeting's words 'the 14th of March'
    grounding   decisions[1]: repeats the action item at 02:09, removed
    grounding   decisions[2]: repeats the action item at 03:11, removed
    grounding   decisions[3]: repeats the action item at 04:28, removed

## C. A ZIP that is not a Word document: `m02-zip`

- Checked 2026-11-22 21:29 UTC through GET /api/meetings/m02-zip; result: failed

    m02-zip  failed       unsupported_type at received: photos.docx is a ZIP file but not a Word document
    m02-zip  attempts 0, deliveries 1, ignored uploads 0, earlier errors 0

