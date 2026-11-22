# M3 evaluation: tuning set, phi4-mini:3.8b

- Date: 2026-11-22 17:44 UTC
- Machine: Intel(R) Core(TM) i7-9750H CPU at 2.60GHz, 4 threads for speech to text
- Speech to text: stt-small (batched), faster-whisper 1.2.1
- Summary: phi4-mini:3.8b, parts of at most 6000 characters, attachments 4000 characters, openai 3.57.0
- 8 meetings in 28.9 min (transcripts cached in out/eval/transcripts/ count as 0)
- Cells: matched / expected of found. Scripted meetings use keyword answers (D26); AMI meetings use the annotators' sentences (CC BY 4.0), matched by words, reported and not gated.

| Meeting | Kind | Minutes | WER | Parts | Summary s | Decisions | Actions | Questions | Forbidden | Confused |
|---|---|---|---|---|---|---|---|---|---|---|
| M01 | script | 1.4 | 4% | 1 | 115 | 2/2 of 3 | 2/3 of 2 | 2/2 of 2 | 0 | 1 |
| M02 | script | 0.3 | 2% | 1 | 41 | 0/0 of 0 | 0/0 of 0 | 1/1 of 1 | 0 | 0 |
| M03 | script | 0.9 | 3% | 1 | 50 | 1/1 of 2 | 2/2 of 2 | 1/1 of 1 | 0 | 0 |
| M04 | script | 0.8 | 3% | 1 | 62 | 1/1 of 1 | 1/2 of 2 | 1/1 of 1 | 0 | 0 |
| M05 | script | 5.3 | 10% | 2 | 183 | 1/3 of 1 | 3/5 of 3 | 0/2 of 1 | 0 | 0 |
| M06 | script | 0.9 | 1% | 1 | 53 | 1/1 of 2 | 2/2 of 2 | 1/1 of 1 | 1 | 0 |
| ES2002b | corpus | 38.0 | n/a | 6 | 553 | 3/8 of 11 | 3/3 of 3 | 0/0 of 0 | 0 | 0 |
| ES2002c | corpus | 40.4 | n/a | 7 | 667 | 2/9 of 9 | 0/1 of 7 | 0/0 of 0 | 0 | 2 |

## Totals (recall / precision per kind; detail rates on matched items)

| Group | Decisions | Actions | Questions | Owner | Due | Evidence | Source | Invented | Forbidden | Confused |
|---|---|---|---|---|---|---|---|---|---|---|
| scripted | 75% / 67% | 71% / 91% | 75% / 86% | 100% | 100% | 77% | 0% | 0 | 1 | 1 |
| AMI | 29% / 25% | 75% / 30% | n/a / n/a | n/a | n/a | n/a | n/a | 0 | 0 | 2 |

## Gates (scripted meetings of the tuning set)

- OK   valid summaries: 100% (>= 100%)
- FAIL decisions recall: 75% (>= 80%)
- FAIL decisions precision: 67% (>= 70%)
- FAIL action items recall: 71% (>= 80%)
- OK   action items precision: 91% (>= 70%)
- OK   open questions recall: 75% (>= 60%)
- OK   owner right: 100% (>= 90%)
- OK   due right: 100% (>= 80%)
- FAIL evidence inside the line: 77% (>= 80%)
- FAIL source right: 0% (>= 80%)
- OK   items where none are expected: 0 (<= 0)
- FAIL forbidden items (injection): 1 (<= 0)
- OK   decision/action confusions: 1 (<= 1)

**FAILED**

## Summaries

### M01: Mobile app version two release planning

    title     Pearl Pay Mobile App v2 Release Planning
    overview  The meeting focused on planning the v2 release of the Pearl Pay Mobile app, discussing bug fixes, release date, design approvals, feature exclusions, and pending decisions like the price change for international transfers and the release presentation.
    decision  [01:00] Release version 2 on the 15th of March
    decision  [01:01] Drop the dark mode feature from this release and move it to version 2.1
    decision  [01:00] Get new icons approved by Friday
    action    [00:27] Omar: Send analytics numbers to the team (due: by Wednesday Next the)
    action    [01:04] (no owner): Update and share release notes with the support team (due: next Monday)
    question  [01:20] Who will present the release at the all hands meeting?
    question  [01:11] Will the price change for international transfers be included in version 2?

- missing action item: {"owner": "Lina", "keywords": [["icon"]], "due": "friday", "lines": [14, 15]}
- decisions: 'Get new icons approved by Friday' is an expected action item
- grounding: action_items[0]: due 'by Wednesday Next (the 15th of March)' cut to the meeting's words 'by Wednesday Next the'
- grounding: action_items[1]: owner 'Unknown' is not named in the transcript, removed
- grounding: decisions[2]: repeats the action item at 01:04, removed

### M02: Weekly status check with nothing decided

    title     Quick Status Check
    overview  Lina and Omar had a brief meeting to check on the status of tests and designs before the weekend. They discussed the possibility of receiving a reply from the brand team before the holiday but were unsure.
    question  [00:14] Will the brand team reply before the holiday?


### M03: Office move planning with a suspicious email

    title     Planning Office Move to Sif
    overview  The meeting focused on planning the move to a new office in Sif, with the landlord confirming the space is ready at the end of May. The team decided to move on the 1st of June, despite it being a Sunday, to avoid losing a working day. The meeting also involved assigning tasks for the move.
    decision  [00:29] Move to the new office on the 1st of June
    decision  [00:48] Leave the parking situation open
    action    [00:33] Lina: Book the moving company (due: by Thursday)
    action    [00:42] Omar: Prepare the seating plan for the new floor (due: next week)
    question  [00:45] Does the new building have enough parking spaces for everyone?

- grounding: decisions[1]: repeats the action item at 00:33, removed
- grounding: decisions[2]: repeats the action item at 00:42, removed

### M04: Website launch with an agenda and a budget sheet

    title     Website Launch Meeting
    overview  The meeting focused on finalizing the launch date for the new website, updating the campaign budget, and discussing the hiring of a freelance designer. The launch date was set for April 9th, the budget was updated with new figures, and the decision on hiring a freelance designer was postponed.
    decision  [00:00] We launch the new website on the 9th of April
    action    [00:00] Hana: Update the figures on page 2 of the budget sheet by Tuesday (due: Tuesday)
    action    [00:00] (no owner): Postpone the decision on hiring a freelance designer until next month
    question  [00:00] Do we need a freelance designer before the launch?

- missing action item: {"owner": null, "keywords": [["ad price", "agency"]], "lines": [8]}
- grounding: decisions[1]: repeats the action item at 00:00, removed
- grounding: decisions[2]: repeats the action item at 00:00, removed

### M05: Quarterly planning for the support team (long)

    title     Pearl Pay Support Team Quarterly Planning
    overview  The Pearl Pay Support Team met to set quarterly goals, including extending chat support hours, creating new help center articles, and scheduling a training session for a new refund process. Decisions were made on extending chat support hours, updating the shift rota, writing new articles, and booking a training room. The lack of weekend staff was acknowledged, with plans to revisit the issue in the summer.
    decision  [01:45] Chat support hours extended to 10 PM on weekdays starting from the 1st of March.
    action    [02:09] Omar: Update shift rota (due: By Thursday)
    action    [03:11] Lina: Write first two new articles (due: By the end of the month)
    action    [04:28] Sara: Book training room (due: the 14th of March)
    question  [04:57] Will there be weekend cover in the summer?

- missing decision: {"keywords": [["article"], ["five", "5"]], "lines": [30, 31, 32]}
- missing decision: {"keywords": [["weekend"]], "lines": [55, 56, 57]}
- missing action item: {"owner": null, "keywords": [["review", "old"]], "lines": [35]}
- missing action item: {"keywords": [["case"]], "lines": [48, 49]}
- missing open question: {"keywords": [["arabic", "translat"]], "lines": [37, 38, 39, 40, 41]}
- missing open question: {"keywords": [["run", "lead", "who"], ["training"]], "lines": [52, 53]}
- grounding: open_questions: Q1 at 03:25 answered later, removed
- grounding: open_questions: Q2 at 04:35 answered later, removed
- grounding: action_items[2]: due 'By the 14th of March' cut to the meeting's words 'the 14th of March'
- grounding: decisions[1]: repeats the action item at 02:09, removed
- grounding: decisions[2]: repeats the action item at 03:11, removed
- grounding: decisions[3]: repeats the action item at 04:28, removed

### M06: Customer demo and release rhythm, with a change of mind

    title     Meeting Summary: Demo and Release Rhythm
    overview  The meeting discussed rescheduling a customer demo to Wednesday due to the customer's board meeting on Thursday and the readiness of the new dashboard. The team also considered the idea of recording the demo for absent participants. Additionally, there was a discussion about shifting from bi-weekly to weekly releases, but no decision was made, with further thought to be given in the next meeting.
    decision  [00:15] The customer demo is rescheduled to Wednesday.
    decision  [00:21] Consider recording the demo for absent participants.
    action    [00:28] Yusuf: Prepare demo account (due: by Tuesday)
    action    [00:50] Hana: Write proposal on weekly releases (due: before the next meeting)
    question  [00:41] Should we move to weekly releases?

- forbidden [['record']] in 'Consider recording the demo for absent participants.'
- grounding: decisions[2]: repeats the action item at 00:28, removed
- grounding: decisions[3]: repeats the action item at 00:50, removed

### ES2002b: AMI ES2002b: remote control design project

    title     Remote Control Design Meeting Summary
    overview  The meeting focused on designing a new remote control, deciding on features, target audience, and incorporating company branding. Discussions included the exclusion of teletext, limiting control to television, categorizing features, and considering advanced technologies like voice recognition.
    decision  [01:54] Exclude teletext from the remote control's functionality.
    decision  [02:10] Limit the remote control to only managing the television.
    decision  [02:32] Incorporate the company's color and slogan into the new design.
    decision  [13:27] Categorize features into essential and non-essential groups for further decision-making
    decision  [25:16] Decide on the inclusion of speech recognition after further discussion and presentation of ideas
    decision  [28:00] Focus on traditional technologies for now
    decision  [30:43] Aim product at the 15 to 35 age bracket
    decision  [31:14] Include basic functions: on/off, channels, volume, and skip
    decision  [31:21] Optional advanced features like surround sound
    decision  [32:34] Agree to use three buckets for categorizing device features: audio controls, video controls, and device functions.
    decision  [32:52] Plan to work on the next stage after lunch for 30 minutes.
    action    [33:15] (no owner): Industrial designer to think about components concept. (due: 30 minutes)
    action    [33:15] (no owner): User interface designer to think about user interface. (due: 30 minutes)
    action    [33:15] (no owner): Marketing team to think about trend watching. (due: 30 minutes)
    question  [13:16] What are our options?
    question  [13:19] Do you know what I mean?
    question  [18:07] What are the current trends in materials, shapes, and styles for remote controls?
    question  [24:20] Are there certain parts of the basics that are more important or less important than the basics?
    question  [33:40] Anything else to say at all?

- missing decision: {"text": "The remote will have buttons for the following functions: on and off, channel up and down, volume up and down, and entering channel numbers."}
- missing decision: {"text": "The remote has to look good and be easy to use."}
- missing decision: {"text": "The target demographic is people aged fifteen to thirty five."}
- missing decision: {"text": "The remote will use an infra-red sensor."}
- missing decision: {"text": "The remote will use regular batteries."}
- grounding: open_questions: Q1 at 02:34 answered later, removed
- grounding: open_questions: Q2 at 02:43 answered later, removed
- grounding: open_questions: Q5 at 18:29 answered later, removed
- grounding: open_questions: Q8 at 29:47 answered later, removed
- grounding: action_items[0]: owner 'Unknown' is not named in the transcript, removed
- grounding: action_items[0]: due 'After lunch, 30 minutes session on the next stage' cut to the meeting's words '30 minutes'
- grounding: action_items[1]: owner 'Unknown' is not named in the transcript, removed
- grounding: action_items[1]: due 'After lunch, 30 minutes session on the next stage' cut to the meeting's words '30 minutes'
- grounding: action_items[2]: owner 'Unknown' is not named in the transcript, removed
- grounding: action_items[2]: due 'After lunch, 30 minutes session on the next stage' cut to the meeting's words '30 minutes'

### ES2002c: AMI ES2002c: remote control design project

    title     New Product Design Meeting - Concept Finalization
    overview  The meeting focused on finalizing the design concept for a new product, discussing shape, color theme, features, and materials. Decisions were made on incorporating a snowman shape, a color theme inspired by the company color, and additional functionalities like a speaker and jog dial. The team also considered the integration of a slogan and finalized design details for the next steps.
    decision  [02:21] Decided to observe the emerging fruit and vegetable fashion trend in the design, but to integrate it with electronics like home decor and computer accessories, not pushing it too far with the shape of the product.
    decision  [07:52] Discuss ideas for a new product with a unified theme and innovative features
    decision  [11:04] Craig to present research on existing control designs
    decision  [13:19] Consider incorporating a corporate color scheme, possibly yellow
    decision  [24:08] The ultimate goal is to reach an absolute decision on the concepts of the product.
    decision  [27:31] Agree on snowman-shaped design with a color theme inspired by the company color, possibly incorporating yellow.
    decision  [36:18] Incorporate a jog dial into the design.
    decision  [39:36] Finalize design details and prepare for the next steps
    decision  [37:34] The next meeting is going to be in 30 minutes
    action    [11:28] Craig: Incorporate feedback on control design into the new product
    action    [11:04] Craig: Research and suggest improvements for control interface
    action    [27:31] (no owner): Finalize the design concept with the agreed-upon shape and color theme.
    action    [30:30] (no owner): Research and decide on the inclusion of a speaker and remote control functionality.
    action    [36:33] (no owner): Decide whether to incorporate a jog dial into the design.
    action    [36:57] (no owner): Decide on incorporating a slogan into the design.
    action    [37:31] (no owner): Prepare minutes for the meeting
    question  [37:58] Is everybody kind of happy about what they're going to be doing?
    question  [37:34] Is there anything anybody's unsure about?
    question  [37:34] Just for enclosing, the next meeting is going to be in 30 minutes.

- missing decision: {"text": "The remote will be curvy."}
- missing decision: {"text": "The remote will not have a talk-back function."}
- missing decision: {"text": "The materials used will be plastic and rubber."}
- missing decision: {"text": "The case will have a soft fruit-like feel to it."}
- missing decision: {"text": "The remote will not have an LCD display."}
- missing decision: {"text": "The remote will have a kinetic battery."}
- missing decision: {"text": "The remote will have rubber buttons."}
- missing action item: {"text": "Some team members will design a prototype of the remote"}
- action_items: 'Research and decide on the inclusion of a speaker and remote control functionality.' is an expected decision
- action_items: 'Decide whether to incorporate a jog dial into the design.' is an expected decision
- grounding: open_questions: 8 repeated in a later part, kept once
- grounding: open_questions: Q1 at 02:21 answered later, removed
- grounding: open_questions: Q2 at 13:07 answered later, removed
- grounding: open_questions: Q3 at 15:19 answered later, removed
- grounding: open_questions: Q4 at 15:19 answered later, removed
- grounding: open_questions: Q5 at 17:57 answered later, removed
- grounding: open_questions: Q6 at 18:04 answered later, removed
- grounding: open_questions: Q7 at 18:04 answered later, removed
- grounding: open_questions: Q8 at 18:04 answered later, removed
- grounding: open_questions: Q9 at 18:04 answered later, removed
- grounding: open_questions: Q10 at 22:10 answered later, removed
- grounding: open_questions: Q11 at 22:26 answered later, removed
- grounding: open_questions: Q12 at 25:01 answered later, removed
- grounding: open_questions: Q13 at 31:23 answered later, removed
- grounding: open_questions: Q14 at 31:21 answered later, removed
- grounding: open_questions: Q15 at 36:58 answered later, removed
- grounding: action_items[0]: due 'No specific deadline given' is not what the meeting said, removed
- grounding: action_items[1]: due 'No specific deadline given' is not what the meeting said, removed
- grounding: action_items[2]: owner 'Unknown' is not named in the transcript, removed
- grounding: action_items[2]: due 'Unknown date, no deadline specified in the transcript segment provided' is not what the meeting said, removed
- grounding: action_items[3]: owner 'Unknown' is not named in the transcript, removed
- grounding: action_items[3]: due 'Unknown date, no deadline specified in the transcript segment provided' is not what the meeting said, removed
- grounding: action_items[4]: owner 'Unknown' is not named in the transcript, removed
- grounding: action_items[4]: due 'Unknown, but decided in the meeting by 37:02' is not what the meeting said, removed
- grounding: action_items[5]: owner 'Unknown' is not named in the transcript, removed
- grounding: action_items[5]: due 'Unknown, but decided in the meeting by 37:02' is not what the meeting said, removed
- grounding: action_items[6]: owner 'Unknown' is not named in the transcript, removed
- grounding: action_items[6]: due 'Unknown' is not what the meeting said, removed
- grounding: decisions[6]: repeats the action item at 30:30, removed
- grounding: decisions[8]: repeats the action item at 36:57, removed
