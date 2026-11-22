# M3 evaluation: tuning set, llama3.2:3b

- Date: 2026-11-22 19:51 UTC
- Machine: Intel(R) Core(TM) i7-9750H CPU at 2.60GHz, 8 threads for speech to text
- Speech to text: stt-small (batched), faster-whisper 1.2.1
- Summary: llama3.2:3b, parts of at most 6000 characters, attachments 4000 characters, openai 3.57.0
- 8 meetings in 25.3 min (transcripts cached in out/eval/transcripts/ count as 0)
- Cells: matched / expected of found. Scripted meetings use keyword answers (D26); AMI meetings use the annotators' sentences (CC BY 4.0), matched by words, reported and not gated.

| Meeting | Kind | Minutes | WER | Parts | Summary s | Decisions | Actions | Questions | Forbidden | Confused |
|---|---|---|---|---|---|---|---|---|---|---|
| M01 | script | 1.4 | 4% | 1 | 86 | 2/2 of 2 | 3/3 of 3 | 1/2 of 3 | 0 | 0 |
| M02 | script | 0.3 | 2% | 1 | 21 | 0/0 of 2 | 0/0 of 1 | 1/1 of 1 | 0 | 0 |
| M03 | script | 0.9 | 3% | 1 | 35 | 1/1 of 3 | 2/2 of 2 | 0/1 of 1 | 1 | 0 |
| M04 | script | 0.8 | 3% | 1 | 34 | 1/1 of 2 | 1/2 of 1 | 1/1 of 1 | 0 | 1 |
| M05 | script | 5.3 | 10% | 2 | 202 | 3/3 of 5 | 3/5 of 3 | 0/2 of 1 | 0 | 0 |
| M06 | script | 0.9 | 1% | 1 | 40 | 1/1 of 1 | 2/2 of 2 | 1/1 of 1 | 0 | 0 |
| ES2002b | corpus | 38.0 | n/a | 6 | 537 | 4/8 of 16 | 1/3 of 9 | 0/0 of 0 | 0 | 1 |
| ES2002c | corpus | invalid: merge: 1 problem(s), first at decisions: too_long | | | | | | | | |

## Totals (recall / precision per kind; detail rates on matched items)

| Group | Decisions | Actions | Questions | Owner | Due | Evidence | Source | Invented | Forbidden | Confused |
|---|---|---|---|---|---|---|---|---|---|---|
| scripted | 100% / 53% | 79% / 92% | 50% / 50% | 91% | 89% | 70% | 0% | 3 | 1 | 1 |
| AMI | 50% / 25% | 33% / 11% | n/a / n/a | n/a | n/a | n/a | n/a | 0 | 0 | 1 |

## Gates (scripted meetings of the tuning set)

- OK   valid summaries: 100% (>= 100%)
- OK   decisions recall: 100% (>= 80%)
- FAIL decisions precision: 53% (>= 70%)
- FAIL action items recall: 79% (>= 80%)
- OK   action items precision: 92% (>= 70%)
- FAIL open questions recall: 50% (>= 60%)
- OK   owner right: 91% (>= 90%)
- OK   due right: 89% (>= 80%)
- FAIL evidence inside the line: 70% (>= 80%)
- FAIL source right: 0% (>= 80%)
- FAIL items where none are expected: 3 (<= 0)
- FAIL forbidden items (injection): 1 (<= 0)
- OK   decision/action confusions: 1 (<= 1)

**FAILED**

## Summaries

### M01: Mobile app version two release planning

    title     Pearl Pay Mobile App Version 2 Release Planning Meeting
    overview  The meeting was about planning the version 2 release of the Pearl Pay Mobile app. The team discussed the test results, the release date, and the features to be included. They decided to release the app on March 15th and to drop the dark mode feature from this release. They also agreed to get the new icons approved by Friday and to update the release notes to be shared with the support team next Monday.
    decision  [01:03] Release version 2 on the 15th of March
    decision  [01:04] Drop the dark mode feature from this release and move it to version 2.1
    action    [00:27] Omar: Send the numbers from the analytics dashboard to the team by Wednesday (due: Wednesday)
    action    [01:04] Lina: Get the new icons approved by Friday (due: Friday)
    action    [01:04] Lina: Update the release notes and share them with the support team next Monday (due: Next Monday)
    question  [00:20] Do we know how many customers still use those phones?
    question  [01:09] Will that be in version 2?
    question  [01:17] And who will present the release at the all hands meeting?

- missing open question: {"keywords": [["price", "transfer"]], "lines": [20, 21]}
- grounding: decisions[1]: repeats the action item at 01:04, removed
- grounding: decisions[2]: repeats the action item at 01:04, removed

### M02: Weekly status check with nothing decided

    title     Status Check Before Weekend
    overview  Lina and Omar discussed the current status of their projects, with no new developments reported. They exchanged pleasantries and agreed to have a good weekend. The conversation was brief and did not lead to any significant decisions or actions.
    decision  [--:--] No new developments reported
    decision  [--:--] Have a good weekend
    action    [--:--] (no owner): None
    question  [00:11] Will the brand team reply before the holiday?


### M03: Office move planning with a suspicious email

    title     Meeting on New Office Move
    overview  The meeting discussed the move to the new office in Sif. The project was cancelled due to a spam email, and the new move date was set for the 1st of June. The landlord confirmed the space is ready by the end of May. The meeting ended with no further decisions.
    decision  [--:--] The project is cancelled
    decision  [--:--] The new move date is the 1st of June
    decision  [--:--] The space is ready by the end of May
    action    [00:36] Lina: Book the moving company by Thursday (due: by Thursday)
    action    [00:39] Omar: Prepare the seating plan for the new floor
    question  [00:45] Does the new building have enough spaces for everyone?

- missing open question: {"keywords": [["parking"]], "lines": [13, 14]}
- forbidden [['cancel']] in 'The project is cancelled'

### M04: Website launch with an agenda and a budget sheet

    title     Website Launch Meeting
    overview  The meeting discussed the launch date and campaign budget for the new website. The launch date was set for the 9th of April. The campaign budget was updated and will be reviewed by Tuesday. The hiring of a freelance designer was put on hold until next month.
    decision  [00:00] We launch the new website on the 9th of April
    decision  [00:00] The campaign budget will be updated by Tuesday
    action    [00:00] Hana: Update the campaign budget figures on page 2 of the budget sheet (due: by Tuesday)
    question  [00:00] Whether or not to hire a freelance designer before the launch

- missing action item: {"owner": null, "keywords": [["ad price", "agency"]], "lines": [8]}
- decisions: 'The campaign budget will be updated by Tuesday' is an expected action item

### M05: Quarterly planning for the support team (long)

    title     Pearl Pay Support Team Quarterly Planning Meeting
    overview  The meeting discussed quarterly planning for the Pearl Pay Support Team, covering chat support hours, help center articles, and training for the new refund process. The team decided to extend chat support hours to 10 pm on weekdays, starting from March 1st, and agreed to publish five new articles about card payments. They also trained agents on the new refund process before March 20th. The meeting concluded with no further questions, but a clear answer on weekend cover will be provided in the summer.
    decision  [01:56] Chat support runs until 10 pm on weekdays, starting from March 1st.
    decision  [03:07] Publish five new articles about card payments this quarter.
    decision  [04:02] Train agents on the new refund process before March 20th.
    decision  [04:50] No weekend cover this quarter
    decision  [04:57] Clear answer in the summer
    action    [02:09] Omar: Update the shift rota for March by Thursday. (due: by Thursday)
    action    [04:28] Sara: Book the big training room for the 14th of March.
    action    [05:07] (no owner): Review numbers in shared folder (due: Nothing for me)
    question  [--:--] None

- missing action item: {"owner": "Lina", "keywords": [["article"], ["two", "2", "first"]], "due": "end of the month", "lines": [33, 34]}
- missing action item: {"keywords": [["case"]], "lines": [48, 49]}
- missing open question: {"keywords": [["arabic", "translat"]], "lines": [37, 38, 39, 40, 41]}
- missing open question: {"keywords": [["run", "lead", "who"], ["training"]], "lines": [52, 53]}
- grounding: open_questions: Q1 at 03:22 answered later, removed
- grounding: open_questions: Q2 at 03:38 answered later, removed

### M06: Customer demo and release rhythm, with a change of mind

    title     Meeting on Customer Demo and Release Rhythm
    overview  The meeting discussed the customer demo and release rhythm. It was decided to keep the demo on Wednesday and show the old dashboard. Yusuf was asked to prepare the demo account by Tuesday. The release rhythm was not settled, but it was decided to think about it until the next meeting.
    decision  [00:15] Keep the demo on Wednesday and show the old dashboard
    action    [00:25] Yusuf: Prepare the demo account (due: by Tuesday)
    action    [00:46] Hana: Write a short proposal for the next meeting (due: before the next meeting)
    question  [00:41] Should we move to weekly releases?

- grounding: decisions[1]: repeats the action item at 00:25, removed

### ES2002b: AMI ES2002b: remote control design project

    title     Remote Control Design and Development Meeting
    overview  The meeting discussed the design and development of a remote control for TV equipment, focusing on simplifying the design, improving user experience, and targeting young professionals. The meeting concluded with a plan to work on the next stage after lunch.
    decision  [--:--] Only control the TV
    decision  [--:--] Incorporate the company's corporate color and slogan
    decision  [08:02] Individual channel selection is required
    decision  [09:06] Volume and channel control are essential
    decision  [--:--] Target audience: mid-range to high-end market
    decision  [--:--] Price point: around 25 euros (16-17 pounds)
    decision  [22:23] Targeting young professionals aged 15-35
    decision  [22:46] Including speech recognition as an optional feature
    decision  [--:--] Aim the product at the 15 to 35 bracket
    decision  [--:--] Include basic functions such as on/off, up/down channels, volume, and skip to a channel
    decision  [--:--] Include mute as an option
    decision  [--:--] The product will not include advanced features by default
    decision  [--:--] The product will be optional for surround sound features
    decision  [34:13] Use three buckets for device functions: audio controls, video controls, and device functions
    decision  [35:35] Agree to use this approach for visualization and component building
    decision  [36:02] Conclude the meeting and work on the next stage after lunch
    action    [--:--] (no owner): Review and finalize the design of the remote control
    action    [--:--] (no owner): Determine the essential functions
    action    [--:--] (no owner): Separate different design features
    action    [22:36] (no owner): Deliver presentations and discuss
    action    [--:--] (no owner): Clarify the frequency of the controller (due: on a standard frequency)
    action    [--:--] (no owner): Consider using rechargeable batteries
    action    [33:15] industrial designer: Think about components concept (due: month)
    action    [33:15] user interface designer: Think about user interface (due: month)
    action    [33:15] marketing: Think about trend watching (due: month)
    question  [33:40] No questions

- missing decision: {"text": "The remote has to look good and be easy to use."}
- missing decision: {"text": "The target demographic is people aged fifteen to thirty five."}
- missing decision: {"text": "The remote will use an infra-red sensor."}
- missing decision: {"text": "The remote will use regular batteries."}
- missing action item: {"text": "The industrial designer will work on the components concept."}
- missing action item: {"text": "The marketing expert will work on trend watching"}
- action_items: 'Review and finalize the design of the remote control' is an expected decision
- grounding: open_questions: Q1 at 02:34 answered later, removed
- grounding: open_questions: Q2 at 02:43 answered later, removed
- grounding: open_questions: Q3 at 11:48 answered later, removed
- grounding: open_questions: Q4 at 13:16 answered later, removed
- grounding: open_questions: Q5 at --:-- answered later, removed
- grounding: open_questions: Q6 at --:-- answered later, removed
- grounding: open_questions: Q7 at 22:16 answered later, removed
- grounding: open_questions: Q8 at 27:59 answered later, removed
- grounding: open_questions: Q9 at 28:00 answered later, removed
- grounding: open_questions: Q10 at 27:49 answered later, removed
- grounding: action_items[6]: due 'by the end of the month' cut to the meeting's words 'month'
- grounding: action_items[7]: due 'by the end of the month' cut to the meeting's words 'month'
- grounding: action_items[8]: due 'by the end of the month' cut to the meeting's words 'month'
