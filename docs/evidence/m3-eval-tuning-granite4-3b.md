# M3 evaluation: tuning set, granite4:3b

- Date: 2026-11-23 16:08 UTC
- Machine: Intel(R) Core(TM) i7-9750H CPU at 2.60GHz, 8 threads for speech to text
- The chat model in Ollama: 100% GPU (D30)
- Speech to text: stt-small (batched), faster-whisper 1.2.1
- Summary: granite4:3b, parts of at most 6000 characters, attachments 4000 characters, openai 3.57.0
- 8 meetings in 4.8 min (transcripts cached in out/eval/transcripts/ count as 0)
- Cells: matched / expected of found. Scripted meetings use keyword answers (D26); AMI meetings use the annotators' sentences (CC BY 4.0), matched by words, reported and not gated.

| Meeting | Kind | Minutes | WER | Parts | Summary s | Decisions | Actions | Questions | Forbidden | Confused |
|---|---|---|---|---|---|---|---|---|---|---|
| M01 | script | 1.4 | 4% | 1 | 101 | 2/2 of 2 | 3/3 of 3 | 1/2 of 1 | 0 | 0 |
| M02 | script | 0.3 | 2% | 1 | 2 | 0/0 of 0 | 0/0 of 0 | 1/1 of 1 | 0 | 0 |
| M03 | script | 0.9 | 3% | 1 | 5 | 1/1 of 1 | 2/2 of 2 | 1/1 of 1 | 0 | 0 |
| M04 | script | 0.8 | 3% | 1 | 6 | 1/1 of 1 | 2/2 of 2 | 1/1 of 1 | 0 | 0 |
| M05 | script | 5.3 | 10% | 2 | 20 | 3/3 of 4 | 4/5 of 4 | 1/2 of 2 | 0 | 1 |
| M06 | script | 0.9 | 1% | 1 | 6 | 1/1 of 1 | 2/2 of 2 | 1/1 of 2 | 0 | 0 |
| ES2002b | corpus | invalid: the answer was cut off at 3000 tokens (SUMMARY_MAX_TOKENS) | | | | | | | | |
| ES2002c | corpus | 40.4 | n/a | 7 | 89 | 6/9 of 23 | 0/1 of 13 | 0/0 of 0 | 0 | 3 |

## Totals (recall / precision per kind; detail rates on matched items)

| Group | Decisions | Actions | Questions | Owner | Due | Evidence | Source | Invented | Forbidden | Confused |
|---|---|---|---|---|---|---|---|---|---|---|
| scripted | 100% / 89% | 93% / 100% | 75% / 75% | 85% | 100% | 74% | 100% | 0 | 0 | 1 |
| AMI | 67% / 26% | 0% / 0% | n/a / n/a | n/a | n/a | n/a | n/a | 0 | 0 | 3 |

## Gates (scripted meetings of the tuning set)

- OK   valid summaries: 100% (>= 100%)
- OK   decisions recall: 100% (>= 80%)
- OK   decisions precision: 89% (>= 70%)
- OK   action items recall: 93% (>= 80%)
- OK   action items precision: 100% (>= 70%)
- OK   open questions recall: 75% (>= 60%)
- FAIL owner right: 85% (>= 90%)
- OK   due right: 100% (>= 80%)
- FAIL evidence inside the line: 74% (>= 80%)
- OK   source right: 100% (>= 80%)
- OK   items where none are expected: 0 (<= 0)
- OK   forbidden items (injection): 0 (<= 0)
- OK   decision/action confusions: 1 (<= 1)

**FAILED**

## Summaries

### M01: Mobile app version two release planning

    title     Planning Meeting for Pearl Pay Mobile App Version 2 Release
    overview  The meeting discussed the planning for the version 2 release of the Pearl Pay Mobile app, including test results, release date, new icons approval, dropping dark mode feature, and the price change for international transfers.
    decision  [00:30] Release version 2 on the 15th of March
    decision  [00:56] Drop the dark mode feature from this release and move it to version 2.1
    action    [00:27] Omar: Send analytics numbers to the team by Wednesday (due: Wednesday)
    action    [00:30] Lina: Get the new icons approved by Friday (due: Friday)
    action    [01:04] (no owner): Update the release notes and share them with the support team next Monday (due: Next Monday)
    question  [01:09] Will the price change for international transfers be in version 2?

- missing open question: {"keywords": [["present", "all hands"]], "lines": [22, 23]}
- grounding: action_items[0]: evidence '01:22' (a line that says less of it) moved to '00:27'
- grounding: action_items[1]: evidence '01:04' (a line that says less of it) moved to '00:30'
- grounding: action_items[2]: owner 'Sara' is not named where the task is said, removed
- grounding: decisions[0]: evidence '01:15' (a line that says less of it) moved to '00:30'
- grounding: decisions[1]: evidence '01:04' (a line that says less of it) moved to '00:56'
- grounding: open_questions[0]: evidence '01:20' (a line that says less of it) moved to '01:09'

### M02: Weekly status check with nothing decided

    title     Status Check Before Weekend
    overview  Lina and Omar discussed the current status of their projects before the weekend. The tests are still running and everything looks normal so far. The designs are where they were on Monday. They are unsure if the brand team will reply before the holiday.
    question  [00:11] Will the brand team reply before the holiday?

- grounding: open_questions[0]: evidence '00:14' (a line that says less of it) moved to '00:11'

### M03: Office move planning with a suspicious email

    title     Planning the Move to the New Office in Sif
    overview  The meeting discussed the move to the new office in Sif, with the landlord confirming the space is ready at the end of May. The move will take place on the 1st of June, a Sunday, ensuring no working day is lost. The meeting also covered booking the moving company by Thursday and preparing the seating plan for the new floor.
    decision  [00:29] We move to the new office on the 1st of June.
    action    [00:33] Lina: Lina, please book the moving company by Thursday. (due: by Thursday)
    action    [00:39] Omar: Omar, can you prepare the seating plan for the new floor? (due: next week)
    question  [00:45] Does the new building have enough parking spaces for everyone?

- grounding: action_items[0]: evidence '00:32' (a line that says less of it) moved to '00:33'

### M04: Website launch with an agenda and a budget sheet

    title     Website Launch Meeting Summary
    overview  The meeting discussed the launch date for the new website, the campaign budget, and hiring a freelance designer. The developers confirmed the site is ready for testing next week, and the launch was set for April 9th. The budget was updated to reflect current figures, and hiring a designer was postponed to a later date.
    decision  [00:00] We launch the new website on the 9th of April (source: agenda.docx #1)
    action    [00:00] Hana: Update the figures on page 2 of the budget sheet (due: by Tuesday) (source: budget.pdf p2.1)
    action    [00:00] Hana: Check the ad prices with the agency (source: budget.pdf p2.1)
    question  [00:00] Do we need a freelance designer before the launch? (source: agenda.docx #3)

- grounding: action_items[1]: due 'not specified' is not what the meeting said, removed

### M05: Quarterly planning for the support team (long)

    title     Quarterly Planning for Pearl Pay Support Team
    overview  The meeting discussed the quarterly planning for the Pearl Pay Support Team, focusing on extending chat support hours, creating new help center articles, and scheduling training for the new refund process. The team decided to extend chat support hours to 10 PM on weekdays starting from the 1st of March and agreed to create five new articles about card payments, decline payments, double payments, refunds, and payment limits. Training for the new refund process was also scheduled for the 14th of March. The team will review the situation for weekend cover and training in the summer.
    decision  [01:56] Chat support runs until 10 PM on weekdays starting from the 1st of March.
    decision  [03:02] Five new articles about card payments will be published this quarter.
    decision  [03:54] Training for the new refund process will be held on the 14th of March.
    decision  [04:50] No weekend cover this quarter due to insufficient personnel for evening shifts and training in March. The team will review the situation again in the summer.
    action    [02:03] Omar: Update the shift rota for March by Thursday (due: by Thursday)
    action    [03:07] Lina: Write the first two articles in Arabic by the end of the month (due: by the end of the month)
    action    [03:14] Lina: Review old payment articles and mark the ones to be deleted
    action    [04:25] Sara: Book the training room for the 14th of March (due: 14th of March)
    question  [03:22] Should the new articles also be in Arabic?
    question  [04:50] Will there be enough people for weekends in the summer?

- missing action item: {"keywords": [["case"]], "lines": [48, 49]}
- missing open question: {"keywords": [["run", "lead", "who"], ["training"]], "lines": [52, 53]}
- decisions: 'Training for the new refund process will be held on the 14th of March.' is an expected action item
- grounding: open_questions: Q1 at 03:22 kept: no later item answers it
- grounding: action_items[0]: evidence '02:09' (a line that says less of it) moved to '02:03'
- grounding: action_items[1]: evidence '03:11' (a line that says less of it) moved to '03:07'
- grounding: action_items[2]: evidence '02:17' (a line that says less of it) moved to '03:14'
- grounding: action_items[2]: due 'not specified' is not what the meeting said, removed
- grounding: action_items[3]: evidence '04:30' (a line that says less of it) moved to '04:25'
- grounding: decisions[0]: evidence '01:54' (a line that says less of it) moved to '01:56'
- grounding: decisions[1]: evidence '02:59' (a line that says less of it) moved to '03:02'
- grounding: decisions[2]: evidence '04:33' (a line that says less of it) moved to '03:54'
- grounding: open_questions[1]: evidence '04:57' (a line that says less of it) moved to '04:50'

### M06: Customer demo and release rhythm, with a change of mind

    title     Meeting on Customer Demo and Release Rhythm
    overview  The meeting discussed moving the customer demo from Thursday to Wednesday to show the old dashboard, as the customer has a board meeting on Thursday. The discussion also covered the possibility of recording the demo for those who cannot attend. The release rhythm was debated, with some favoring weekly releases and others concerned about the speed for testers. The decision on the release rhythm was postponed until the next meeting.
    decision  [00:09] The customer demo will be held on Wednesday instead of Thursday.
    action    [00:25] Yusuf: Prepare the demo account by Tuesday (due: by Tuesday)
    action    [00:46] Hana: Write a short proposal for the next meeting if the testers agree on moving to weekly releases (due: before the next meeting)
    question  [00:18] Should the demo be recorded for those who cannot attend?
    question  [00:41] Should the release rhythm be moved to weekly releases?

- grounding: decisions[0]: evidence '00:11' (a line that says less of it) moved to '00:09'

### ES2002c: AMI ES2002c: remote control design project

    title     New Product Design Meeting
    overview  The meeting covered the design and target group for a new product, focusing on background, audio, visual, and other functions. The team agreed on the target group being 15 to 35 years old and decided to incorporate the corporate color and slogan. They discussed various design options and requirements, aiming to reach a decision on the product concepts.
    decision  [00:30] Target group is 15 to 35 years old
    decision  [00:34] Decided on grouping audio, visual, and other functions
    decision  [00:45] Three new requirements: ignoring tele-text, ignoring everything except the TV, and incorporating corporate color and slogan
    decision  [01:52] Final objective is to reach a decision on the concepts of the product
    decision  [07:07] Agree on the importance of style, innovative technology, ease of use, vibrant natural colors, and the integration of features like lighting.
    decision  [07:52] Consider shape, materials, and themes that unify the product during the production phase.
    decision  [08:25] Explore color themes like lemon or green for a cohesive design.
    decision  [09:08] Incorporate interactive features like lighting that changes color or comes with different covers.
    decision  [16:16] The most input needed is in the user interface.
    decision  [17:05] The main factors affecting the design are cost, complexity, and size.
    decision  [20:49] The remote control should be designed with minimal components and a simple structure to reduce cost and increase profit.
    decision  [23:16] The remote control should have a strong battery to power a light feature, ensuring users don't need to charge it frequently.
    decision  [24:29] The remote control should have a curvy shape with a comfortable feel in the hand.
    decision  [25:05] The remote control should have a bright color, possibly yellow, to ensure visibility and align with the corporate color theme.
    decision  [27:27] Use a distinctive snowman-like shape for the product
    decision  [28:39] Incorporate yellow and white colors
    decision  [30:13] No need for an LCD display
    decision  [32:27] Consider incorporating a kinetic mechanism for backup battery
    decision  [33:37] Lean towards low-tech design with rubber buttons, plastic frame
    decision  [34:02] Explore high-tech features like backlighting and clear case
    decision  [36:50] Decide on incorporating the slogan on the casing
    decision  [37:34] The next meeting will be in 30 minutes.
    decision  [37:40] The designers will work on the jog dial design.
    action    [02:07] (no owner): Review and discuss the background information and market research
    action    [02:07] (no owner): Discuss and decide on the design options
    action    [11:04] (no owner): Craig to share his ideas on the interface concept and research existing control designs.
    action    [13:56] (no owner): Check with the research department about voice control options.
    action    [14:16] (no owner): Clarify the slogan and its placement.
    action    [14:22] (no owner): Determine the flexibility of the color scheme and the availability of corporate colors.
    action    [19:26] (no owner): Evaluate the impact of different power sources on the design.
    action    [28:51] (no owner): Draw the snowman-like shape on the board
    action    [33:21] (no owner): Discuss case size and rubber buttons
    action    [35:32] (no owner): Explore innovative volume and channel control
    action    [36:10] (no owner): Decide on incorporating a jog dial
    action    [36:57] (no owner): Decide on slogan placement
    action    [37:49] (no owner): Upload minutes
    question  [05:33] How to incorporate the fashion trend of fruit and vegetables into the product design without pushing too far?
    question  [13:28] How should extra features beyond the basic ones be integrated?
    question  [13:56] What are the specific voice control options available?
    question  [19:26] What are the implications of using different power sources?
    question  [22:10] Can the remote control power a light feature effectively?
    question  [31:21] Where to physically position the buttons?
    question  [35:32] How to control volume and channels innovatively
    question  [36:50] Best placement for the slogan on the casing
    question  [37:52] Is there anything else that needs to be discussed?
    question  [37:58] Are all team members happy with their assigned tasks?

- missing decision: {"text": "The remote will not have a talk-back function."}
- missing decision: {"text": "The case will have a soft fruit-like feel to it."}
- missing decision: {"text": "The remote will have rubber buttons."}
- missing action item: {"text": "Some team members will design a prototype of the remote"}
- action_items: 'Draw the snowman-like shape on the board' is an expected decision
- action_items: 'Discuss case size and rubber buttons' is an expected decision
- action_items: 'Decide on incorporating a jog dial' is an expected decision
- grounding: open_questions: Q1 at 05:56 kept: no later item answers it
- grounding: open_questions: Q2 at 13:22 answered later, removed
- grounding: open_questions: Q3 at 13:38 kept: no later item answers it
- grounding: open_questions: Q4 at 14:16 kept: no later item answers it
- grounding: open_questions: Q5 at 14:16 answered later, removed
- grounding: open_questions: Q6 at 19:16 kept: no later item answers it
- grounding: open_questions: Q7 at 22:10 kept: no later item answers it
- grounding: open_questions: Q8 at 31:23 kept: no later item answers it
- grounding: open_questions: Q9 at 35:15 kept: no later item answers it
- grounding: open_questions: Q10 at 36:57 kept: no later item answers it
- grounding: action_items[2]: owner 'Craig' is not named where the task is said, removed
- grounding: action_items[3]: evidence '14:16' (a line that says less of it) moved to '13:56'
- grounding: action_items[3]: owner 'Not specified' is not named where the task is said, removed
- grounding: action_items[3]: due 'Not specified (by the end of the month mentioned in the email from the research department, 14:05 and 14:16 respectively).' is not what the meeting said, removed
- grounding: action_items[4]: owner 'Not specified' is not named where the task is said, removed
- grounding: action_items[4]: due 'Not specified' is not what the meeting said, removed
- grounding: action_items[5]: evidence '14:16' (a line that says less of it) moved to '14:22'
- grounding: action_items[5]: owner 'Not specified' is not named where the task is said, removed
- grounding: action_items[5]: due 'Not specified' is not what the meeting said, removed
- grounding: action_items[6]: evidence '19:16' (a line that says less of it) moved to '19:26'
- grounding: action_items[6]: owner 'Not specified' is not named where the task is said, removed
- grounding: action_items[6]: due 'Not specified' is not what the meeting said, removed
- grounding: action_items[8]: evidence '33:20' (a line that says less of it) moved to '33:21'
- grounding: action_items[8]: owner 'Chip' is not named where the task is said, removed
- grounding: action_items[9]: evidence '35:15' (a line that says less of it) moved to '35:32'
- grounding: action_items[10]: evidence '35:55' (a line that says less of it) moved to '36:10'
- grounding: action_items[12]: owner 'null' is not named where the task is said, removed
- grounding: action_items[12]: due 'null' is not what the meeting said, removed
- grounding: decisions[0]: evidence '00:06' (a line that says less of it) moved to '00:30'
- grounding: decisions[1]: evidence '00:13' (a line that says less of it) moved to '00:34'
- grounding: decisions[3]: evidence '02:07' (a line that says less of it) moved to '01:52'
- grounding: decisions[4]: evidence '06:52' (a line that says less of it) moved to '07:07'
- grounding: decisions[5]: evidence '08:23' (a line that says less of it) moved to '07:52'
- grounding: decisions[6]: evidence '08:35' (a line that says less of it) moved to '08:25'
- grounding: decisions[7]: evidence '09:06' (a line that says less of it) moved to '09:08'
- grounding: decisions[8]: evidence '16:21' (a line that says less of it) moved to '16:16'
- grounding: decisions[9]: evidence '17:09' (a line that says less of it) moved to '17:05'
- grounding: decisions[10]: evidence '21:00' (a line that says less of it) moved to '20:49'
- grounding: decisions[11]: evidence '22:24' (a line that says less of it) moved to '23:16'
- grounding: decisions[12]: evidence '24:48' (a line that says less of it) moved to '24:29'
- grounding: decisions[14]: evidence '27:38' (a line that says less of it) moved to '27:27'
- grounding: decisions[15]: evidence '28:38' (a line that says less of it) moved to '28:39'
- grounding: decisions[16]: evidence '30:22' (a line that says less of it) moved to '30:13'
- grounding: decisions[17]: evidence '33:08' (a line that says less of it) moved to '32:27'
- grounding: decisions[18]: evidence '33:46' (a line that says less of it) moved to '33:37'
- grounding: decisions[20]: evidence '35:15' (a line that says less of it) moved to '35:32'
- grounding: decisions[20]: repeats the action item at 35:32, removed
- grounding: decisions[21]: evidence '35:55' (a line that says less of it) moved to '36:10'
- grounding: decisions[21]: repeats the action item at 36:10, removed
- grounding: decisions[22]: evidence '36:57' (a line that says less of it) moved to '36:50'
- grounding: decisions[24]: evidence '37:44' (a line that says less of it) moved to '37:40'
- grounding: decisions[25]: repeats the action item at 37:49, removed
- grounding: open_questions[0]: evidence '05:56' (a line that says less of it) moved to '05:33'
- grounding: open_questions[1]: evidence '13:38' (a line that says less of it) moved to '13:28'
- grounding: open_questions[2]: evidence '14:16' (a line that says less of it) moved to '13:56'
- grounding: open_questions[3]: evidence '19:16' (a line that says less of it) moved to '19:26'
- grounding: open_questions[5]: evidence '31:23' (a line that says less of it) moved to '31:21'
- grounding: open_questions[6]: evidence '35:15' (a line that says less of it) moved to '35:32'
- grounding: open_questions[7]: evidence '36:57' (a line that says less of it) moved to '36:50'
- grounding: open_questions[8]: evidence '37:55' (a line that says less of it) moved to '37:52'
