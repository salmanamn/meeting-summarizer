# M3 evaluation: tuning set, granite4:3b

- Date: 2026-11-22 19:20 UTC
- Machine: Intel(R) Core(TM) i7-9750H CPU at 2.60GHz, 8 threads for speech to text
- Speech to text: stt-small (batched), faster-whisper 1.2.1
- Summary: granite4:3b, parts of at most 6000 characters, attachments 4000 characters, openai 3.57.0
- 8 meetings in 27.3 min (transcripts cached in out/eval/transcripts/ count as 0)
- Cells: matched / expected of found. Scripted meetings use keyword answers (D26); AMI meetings use the annotators' sentences (CC BY 4.0), matched by words, reported and not gated.

| Meeting | Kind | Minutes | WER | Parts | Summary s | Decisions | Actions | Questions | Forbidden | Confused |
|---|---|---|---|---|---|---|---|---|---|---|
| M01 | script | 1.4 | 4% | 1 | 58 | 2/2 of 2 | 3/3 of 3 | 1/2 of 1 | 0 | 0 |
| M02 | script | 0.3 | 2% | 1 | 16 | 0/0 of 0 | 0/0 of 0 | 1/1 of 1 | 0 | 0 |
| M03 | script | 0.9 | 3% | 1 | 36 | 1/1 of 1 | 2/2 of 2 | 1/1 of 1 | 0 | 0 |
| M04 | script | 0.8 | 3% | 1 | 49 | 1/1 of 2 | 2/2 of 2 | 1/1 of 1 | 0 | 1 |
| M05 | script | 5.3 | 10% | 2 | 160 | 3/3 of 5 | 4/5 of 4 | 0/2 of 1 | 0 | 2 |
| M06 | script | 0.9 | 1% | 1 | 46 | 1/1 of 1 | 2/2 of 2 | 1/1 of 2 | 0 | 0 |
| ES2002b | corpus | 38.0 | n/a | 6 | 548 | 4/8 of 10 | 3/3 of 11 | 0/0 of 0 | 0 | 4 |
| ES2002c | corpus | invalid: merge: 1 problem(s), first at decisions: too_long | | | | | | | | |

## Totals (recall / precision per kind; detail rates on matched items)

| Group | Decisions | Actions | Questions | Owner | Due | Evidence | Source | Invented | Forbidden | Confused |
|---|---|---|---|---|---|---|---|---|---|---|
| scripted | 100% / 73% | 93% / 100% | 62% / 71% | 77% | 100% | 62% | 100% | 0 | 0 | 3 |
| AMI | 50% / 40% | 100% / 27% | n/a / n/a | n/a | n/a | n/a | n/a | 0 | 0 | 4 |

## Gates (scripted meetings of the tuning set)

- OK   valid summaries: 100% (>= 100%)
- OK   decisions recall: 100% (>= 80%)
- OK   decisions precision: 73% (>= 70%)
- OK   action items recall: 93% (>= 80%)
- OK   action items precision: 100% (>= 70%)
- OK   open questions recall: 62% (>= 60%)
- FAIL owner right: 77% (>= 90%)
- OK   due right: 100% (>= 80%)
- FAIL evidence inside the line: 62% (>= 80%)
- OK   source right: 100% (>= 80%)
- OK   items where none are expected: 0 (<= 0)
- OK   forbidden items (injection): 0 (<= 0)
- FAIL decision/action confusions: 3 (<= 1)

**FAILED**

## Summaries

### M01: Mobile app version two release planning

    title     Planning Meeting for Pearl Pay Mobile App Version 2 Release
    overview  The meeting discussed the planning for the version 2 release of the Pearl Pay Mobile app, including test results, release date, new icons, dropping dark mode, and the price change for international transfers.
    decision  [01:15] Release version 2 on the 15th of March
    decision  [01:03] Drop the dark mode feature from this release and move it to version 2.1
    action    [01:22] Omar: Send analytics numbers to the team by Wednesday (due: Wednesday)
    action    [01:04] Lina: Get the new icons approved by Friday (due: Friday)
    action    [01:04] Sara: Update the release notes and share them with the support team next Monday (due: Next Monday)
    question  [01:20] Will the price change for international transfers be in version 2?

- missing open question: {"keywords": [["present", "all hands"]], "lines": [22, 23]}

### M02: Weekly status check with nothing decided

    title     Status Check Before Weekend
    overview  Lina and Omar had a brief status check meeting before the weekend to discuss the current state of their projects. Lina mentioned that the tests are still running and everything looks normal, while the designs are where they were on Monday. Omar expressed uncertainty about whether the brand team will reply before the holiday.
    question  [00:14] Will the brand team reply before the holiday?


### M03: Office move planning with a suspicious email

    title     Planning the Move to the New Office in Sif
    overview  The meeting discussed the move to the new office in Sif, with the landlord confirming the space is ready at the end of May. The move will take place on the 1st of June, a Sunday, ensuring no working day is lost. The meeting concluded with assigning tasks and confirming the move date.
    decision  [00:29] We move to the new office on the 1st of June.
    action    [00:32] Lina: Lina, please book the moving company by Thursday. (due: by Thursday)
    action    [00:39] Omar: Omar, can you prepare the seating plan for the new floor? (due: next week)
    question  [00:44] Does the new building have enough parking spaces for everyone?


### M04: Website launch with an agenda and a budget sheet

    title     Website Launch Meeting
    overview  The meeting discussed the launch date for the new website, the campaign budget, and hiring a freelance designer. The developers confirmed the site is ready for testing next week, and the launch was set for April 9th. The budget was updated to reflect current figures, and hiring a designer was postponed to a later date.
    decision  [00:00] Launch date for the new website is April 9th (source: agenda.docx #1)
    decision  [00:00] Campaign budget updated (source: budget.pdf p2.1)
    action    [00:00] Hana: Update the budget figures on page 2 of the budget sheet (due: by Tuesday) (source: budget.pdf p2.1)
    action    [00:00] Hana: Check ad prices with the agency (source: budget.pdf p2.1)
    question  [00:00] Hiring a freelance designer (source: agenda.docx #4)

- decisions: 'Campaign budget updated' is an expected action item
- grounding: action_items[1]: due 'not specified' is not what the meeting said, removed

### M05: Quarterly planning for the support team (long)

    title     Quarterly Planning for Pearl Pay Support Team
    overview  The meeting covered the quarterly planning for the Pearl Pay Support Team, focusing on extending chat support hours, creating new help center articles, and scheduling training for the new refund process. The team decided to extend chat support to 10 in the evening on weekdays, write five new articles, and schedule training for the 14th of March. They also discussed the lack of weekend cover and agreed to review the situation in the summer.
    decision  [02:00] Extend chat support hours to 10 in the evening on weekdays
    decision  [02:59] Write five new articles about card payments, decline payments, double payments, refunds, and payment limits
    decision  [04:33] Schedule training for the new refund process on the 14th of March
    decision  [04:50] No weekend cover this quarter
    decision  [04:57] Will review the situation again in the summer
    action    [02:09] Omar: Update the shift rota for March by Thursday (due: by Thursday)
    action    [03:11] Lina: Write the first two articles in Arabic by the end of the month (due: by the end of the month)
    action    [02:17] Lina: Review old payment articles and mark the ones to be deleted
    action    [04:30] Sara: Book the training room for the 14th of March (due: 14th of March)
    question  [04:57] Will there be enough people for weekends in the summer?

- missing action item: {"keywords": [["case"]], "lines": [48, 49]}
- missing open question: {"keywords": [["arabic", "translat"]], "lines": [37, 38, 39, 40, 41]}
- missing open question: {"keywords": [["run", "lead", "who"], ["training"]], "lines": [52, 53]}
- decisions: 'Schedule training for the new refund process on the 14th of March' is an expected action item
- decisions: 'Will review the situation again in the summer' is an expected action item
- grounding: open_questions: Q1 at 03:22 answered later, removed
- grounding: action_items[2]: due 'not specified' is not what the meeting said, removed

### M06: Customer demo and release rhythm, with a change of mind

    title     Customer Demo and Release Rhythm Discussion
    overview  The meeting discussed moving the customer demo from Thursday to Wednesday to ensure the new dashboard is not ready. The demo will be held on Wednesday and the old dashboard will be shown. There was a suggestion to record the demo for those who cannot attend, but it was not decided. The release rhythm was discussed, with some preferring weekly releases instead of every two weeks, but it was not decided and will be revisited in the next meeting. Hana was asked to write a proposal if the testers agree.
    decision  [00:15] The customer demo will be held on Wednesday.
    action    [00:43] Yusuf: Yusuf to prepare the demo account by Tuesday. (due: by Tuesday)
    action    [00:46] Hana: Hana to write a short proposal for the next meeting if the testers agree on weekly releases. (due: before the next meeting)
    question  [00:21] Should the demo be recorded for those who cannot attend?
    question  [00:41] Should the release rhythm be moved to weekly releases?


### ES2002b: AMI ES2002b: remote control design project

    title     Remote Control Project Design Meeting
    overview  The meeting covered the design and functionality of a remote control for a TV project. The team agreed on key design principles, including not using teletext, focusing solely on TV control, and incorporating the company's color and slogan. They also discussed essential features, target market, and potential advanced features like voice recognition. The meeting concluded with tasks for the design team to finalize the design and functionality.
    decision  [02:02] Not considering teletext in the remote control functionality
    decision  [02:10] Only controlling the TV with the remote control
    decision  [02:32] Incorporating the company's color and slogan in the design
    decision  [08:01] Required functions: volume control, channel up/down, and channel numbers
    decision  [19:03] Target market for the remote control is the mid-range to high-end market in terms of price and customer preferences.
    decision  [22:26] Consider including voice recognition as a feature that can fulfill a specific function.
    decision  [30:55] Target audience is 15 to 35 years old
    decision  [31:14] Core functions include on/off, channel up/down, volume up/down, and skip to channel
    decision  [31:34] Advanced features are optional
    decision  [34:13] Agree to use the idea of categorizing features into three buckets (audio, video, device) for clarity and discussion during the next meeting.
    action    [02:54] (no owner): Discuss the company's corporate color and whether the slogan should be written on the remote control
    action    [09:13] (no owner): Decide on essential functions for the remote control
    action    [18:40] (no owner): Determine the target audience for the remote control
    action    [24:09] (no owner): Define the basic features needed for the TV equipment
    action    [24:43] (no owner): Create a diagram explaining the process from a basic technology perspective
    action    [25:25] Craig: Finalize the design and functionality of the user interface
    action    [29:16] (no owner): Clarify if the controller can be on a standard frequency and control multiple devices
    action    [29:47] (no owner): Decide on power source (rechargeable vs regular batteries)
    action    [--:--] David: Industrial designer to think about components concept
    action    [--:--] David: User interface designer to think about user interface
    action    [--:--] David: Marketing to think about trend watching
    question  [34:26] How to categorize features that don't fit into audio, video, or device categories?

- missing decision: {"text": "The remote has to look good and be easy to use."}
- missing decision: {"text": "The target demographic is people aged fifteen to thirty five."}
- missing decision: {"text": "The remote will use an infra-red sensor."}
- missing decision: {"text": "The remote will use regular batteries."}
- action_items: "Discuss the company's corporate color and whether the slogan should be written on the remote control" is an expected decision
- action_items: 'Decide on essential functions for the remote control' is an expected decision
- action_items: 'Determine the target audience for the remote control' is an expected decision
- action_items: 'Decide on power source (rechargeable vs regular batteries)' is an expected decision
- grounding: open_questions: Q1 at 02:34 answered later, removed
- grounding: open_questions: Q2 at 02:54 answered later, removed
- grounding: open_questions: Q3 at 08:38 answered later, removed
- grounding: open_questions: Q4 at 10:27 answered later, removed
- grounding: open_questions: Q5 at 19:18 answered later, removed
- grounding: open_questions: Q6 at 25:21 answered later, removed
- grounding: open_questions: Q7 at 27:04 answered later, removed
- grounding: open_questions: Q8 at 27:54 answered later, removed
- grounding: action_items[2]: due 'by the end of the meeting (no specific date given in the transcript, implied to be during the meeting discussion).' is not what the meeting said, removed
