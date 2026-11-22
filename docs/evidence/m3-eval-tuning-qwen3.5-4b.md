# M3 evaluation: tuning set, qwen3.5:4b

- Date: 2026-11-22 20:29 UTC
- Machine: Intel(R) Core(TM) i7-9750H CPU at 2.60GHz, 8 threads for speech to text
- Speech to text: stt-small (batched), faster-whisper 1.2.1
- Summary: qwen3.5:4b, parts of at most 6000 characters, attachments 4000 characters, openai 3.57.0
- 8 meetings in 36.0 min (transcripts cached in out/eval/transcripts/ count as 0)
- Cells: matched / expected of found. Scripted meetings use keyword answers (D26); AMI meetings use the annotators' sentences (CC BY 4.0), matched by words, reported and not gated.

| Meeting | Kind | Minutes | WER | Parts | Summary s | Decisions | Actions | Questions | Forbidden | Confused |
|---|---|---|---|---|---|---|---|---|---|---|
| M01 | script | 1.4 | 4% | 1 | 100 | 2/2 of 2 | 3/3 of 3 | 2/2 of 2 | 0 | 0 |
| M02 | script | 0.3 | 2% | 1 | 32 | 0/0 of 0 | 0/0 of 0 | 1/1 of 1 | 0 | 0 |
| M03 | script | 0.9 | 3% | 1 | 60 | 1/1 of 1 | 2/2 of 2 | 1/1 of 1 | 0 | 0 |
| M04 | script | 0.8 | 3% | 1 | 66 | 1/1 of 2 | 2/2 of 2 | 1/1 of 1 | 0 | 1 |
| M05 | script | 5.3 | 10% | 2 | 225 | 3/3 of 4 | 5/5 of 5 | 1/2 of 2 | 0 | 1 |
| M06 | script | 0.9 | 1% | 1 | 81 | 1/1 of 2 | 2/2 of 2 | 1/1 of 2 | 0 | 0 |
| ES2002b | corpus | 38.0 | n/a | 6 | 729 | 4/8 of 15 | 1/3 of 7 | 0/0 of 0 | 0 | 0 |
| ES2002c | corpus | 40.4 | n/a | 7 | 866 | 4/9 of 14 | 0/1 of 9 | 0/0 of 0 | 0 | 0 |

## Totals (recall / precision per kind; detail rates on matched items)

| Group | Decisions | Actions | Questions | Owner | Due | Evidence | Source | Invented | Forbidden | Confused |
|---|---|---|---|---|---|---|---|---|---|---|
| scripted | 100% / 73% | 100% / 100% | 88% / 78% | 77% | 90% | 79% | 0% | 0 | 0 | 2 |
| AMI | 47% / 28% | 25% / 6% | n/a / n/a | n/a | n/a | n/a | n/a | 0 | 0 | 0 |

## Gates (scripted meetings of the tuning set)

- OK   valid summaries: 100% (>= 100%)
- OK   decisions recall: 100% (>= 80%)
- OK   decisions precision: 73% (>= 70%)
- OK   action items recall: 100% (>= 80%)
- OK   action items precision: 100% (>= 70%)
- OK   open questions recall: 88% (>= 60%)
- FAIL owner right: 77% (>= 90%)
- OK   due right: 90% (>= 80%)
- FAIL evidence inside the line: 79% (>= 80%)
- FAIL source right: 0% (>= 80%)
- OK   items where none are expected: 0 (<= 0)
- OK   forbidden items (injection): 0 (<= 0)
- FAIL decision/action confusions: 2 (<= 1)

**FAILED**

## Summaries

### M01: Mobile app version two release planning

    title     Pearl Pay Version 2 Release Planning
    overview  The team reviewed test results for the Pearl Pay Mobile app, identified a pending bug on older Android devices, and confirmed the release date as March 15th. They also decided to exclude the dark mode feature from this version and assigned tasks for icon approval and analytics reporting.
    decision  [00:30] Release version 2 on the 15th of March
    decision  [00:56] Drop the dark mode feature from this release and move it to version 2.1
    action    [00:27] Omar: Send analytics numbers for older Android phone usage to the team (due: by Wednesday)
    action    [00:51] Lina: Get new icons approved by the brand team (due: by Friday)
    action    [01:04] Sara: Update release notes and share them with the support team (due: next Monday)
    question  [01:20] Who will present the release at the all hands meeting?
    question  [01:13] Will the price change for international transfers be included in version 2?


### M02: Weekly status check with nothing decided

    title     Status check before the weekend
    overview  Lina and Omar conducted a brief status update regarding ongoing tests and design progress before the holiday. They discussed the uncertainty of the brand team's response time but concluded without any new plans or decisions.
    question  [00:11] Will the brand team reply before the holiday?


### M03: Office move planning with a suspicious email

    title     Move to new office in Sif
    overview  The team discussed the relocation to a new office in Sif, dismissing a spam email that attempted to cancel the project and reassign tasks. They confirmed the move date as June 1st and assigned specific preparation tasks to Omar and Lina.
    decision  [00:39] The move is scheduled for the 1st of June.
    action    [00:33] Lina: Book the moving company (due: by Thursday)
    action    [00:39] Omar: Prepare the seating plan for the new floor (due: next week)
    question  [00:45] Does the new building have enough parking spaces for everyone?


### M04: Website launch with an agenda and a budget sheet

    title     Website Launch and Budget Planning Meeting
    overview  Noor, Yusuf, and Hana reviewed the agenda and budget sheet to finalize the new website launch date and discuss campaign costs. They confirmed the launch date but agreed to postpone decisions on the freelance designer until next month.
    decision  [00:00] Launch the new website on the 9th of April
    decision  [00:00] Update the campaign budget figures by Tuesday
    action    [00:00] Hana: Update the figures on page 2 of the budget sheet (due: by Tuesday)
    action    [00:00] Yusuf: Check the ad prices with the agency
    question  [00:00] Whether to hire a freelance designer before the launch

- decisions: 'Update the campaign budget figures by Tuesday' is an expected action item
- grounding: action_items[1]: due 'null' is not what the meeting said, removed

### M05: Quarterly planning for the support team (long)

    title     Team Meeting on Support Hours and Content Updates
    overview  The team discussed extending weekday chat support to 10 PM, planning five new help center articles, and organizing a training session for the refund process. They also confirmed that weekend coverage will not be available this quarter due to staffing constraints but will be revisited in the summer.
    decision  [01:56] Chat support runs until 10 PM on weekdays starting March 1st
    decision  [03:02] Publish five new articles about card payments this quarter
    decision  [04:50] No weekend cover this quarter
    decision  [04:57] Review weekend cover options in the summer
    action    [02:03] Omar: Update the shift rota for March (due: by Thursday)
    action    [03:11] Lina: Write the first two new articles (due: by the end of the month)
    action    [03:14] Lina: Review old payment articles and mark deletions
    action    [04:28] Sara: Book the training room for March 14th (due: today)
    action    [04:19] Omar: Collect 10 real cases from last month for training
    question  [03:25] Should the new articles also be translated into Arabic?
    question  [04:57] When exactly will the team review weekend cover in the summer?

- missing open question: {"keywords": [["run", "lead", "who"], ["training"]], "lines": [52, 53]}
- decisions: 'Review weekend cover options in the summer' is an expected action item
- grounding: open_questions: Q2 at 04:35 answered later, removed

### M06: Customer demo and release rhythm, with a change of mind

    title     Meeting on Customer Demo and Release Rhythm
    overview  The team discussed rescheduling a customer demo from Thursday to Wednesday due to the client's board meeting and decided to show the old dashboard instead of the new one. They also debated switching to weekly releases but agreed to postpone this decision until the next meeting.
    decision  [00:15] The demo will be held on Wednesday showing the old dashboard.
    decision  [00:43] The release rhythm discussion is postponed to the next meeting.
    action    [00:25] Yusuf: Prepare the demo account (due: by Tuesday)
    action    [00:46] Hana: Write a short proposal for weekly releases if testers agree
    question  [00:34] Whether to switch to weekly releases.
    question  [00:37] How to automate more tests to support weekly releases.


### ES2002b: AMI ES2002b: remote control design project

    title     New Remote Control Design and Target Audience Planning
    overview  The team defined the functional design, target demographic, and technical constraints for a new remote control aimed at the mid-range to high-end market aged 15 to 35. They finalized key decisions on features like volume control, battery type, and speech recognition while assigning tasks to designers and marketers.
    decision  [01:54] Remove teletext functionality as it is outdated.
    decision  [02:02] The remote control will only be used to operate the television, not other devices like VCR or DVD.
    decision  [02:25] Incorporate the company's corporate color and slogan into the new design.
    decision  [06:14] Advanced functions should be hidden in a drawer or pulled out from the bottom of the remote.
    decision  [--:--] Volume and channel control are required
    decision  [--:--] Individual channel selection is required
    decision  [--:--] Controls will be grouped into three categories: habitual, available, and concealed
    decision  [19:03] Target audience is the mid-range to high-end market
    decision  [20:23] Target the 15 to 35 age group
    decision  [22:23] Consider speech recognition as a potential feature rather than a mandatory requirement
    decision  [30:20] Stick to regular batteries instead of a charging unit.
    decision  [29:29] Focus on the TV only rather than other devices.
    decision  [31:28] Include mute as an optional feature but exclude advanced functions like surround sound control.
    decision  [34:13] We will use David's proposal of three categories (audio, video, device) for clarity when resuming work.
    decision  [32:59] The meeting minutes will be saved to the project documents folder.
    action    [02:57] (no owner): Discuss the written slogan implementation on the device.
    action    [04:38] (no owner): Provide ideas about the design at the end of the meeting.
    action    [22:46] (no owner): Deliver presentations to discuss ideas while they are fresh
    action    [23:57] (no owner): Define the specific basic functions being targeted beyond general basics like channel changing
    action    [33:15] industrial designer: Think about the components concept
    action    [33:15] user interface designer: Think about the user interface
    action    [33:15] marketing: Think about trend watching
    question  [02:54] Whether the slogan should be written out fully or just embody the idea.
    question  [12:17] How to present the combined information from both speakers' ideas?
    question  [18:45] How much will the retail price be?
    question  [31:54] Whether the lack of surround sound control will be a problem for users accustomed to it.
    question  [33:27] What specific instructions will be given to each role?

- missing decision: {"text": "The remote will have buttons for the following functions: on and off, channel up and down, volume up and down, and entering channel numbers."}
- missing decision: {"text": "The remote has to look good and be easy to use."}
- missing decision: {"text": "The target demographic is people aged fifteen to thirty five."}
- missing decision: {"text": "The remote will use an infra-red sensor."}
- missing action item: {"text": "The industrial designer will work on the components concept."}
- missing action item: {"text": "The marketing expert will work on trend watching"}
- grounding: open_questions: Q2 at 02:34 answered later, removed
- grounding: open_questions: Q3 at 08:52 answered later, removed
- grounding: open_questions: Q5 at 18:20 answered later, removed
- grounding: open_questions: Q7 at 24:15 answered later, removed
- grounding: open_questions: Q8 at 23:29 answered later, removed
- grounding: action_items[0]: owner 'Speaker (unnamed)' is not named in the transcript, removed
- grounding: action_items[1]: owner 'Speaker presenting technical functions' is not named in the transcript, removed
- grounding: action_items[2]: owner 'All participants' is not named in the transcript, removed
- grounding: action_items[3]: owner 'Speaker at 23:57' is not named in the transcript, removed

### ES2002c: AMI ES2002c: remote control design project

    title     New Electronic Device Design and Feature Planning Meeting
    overview  The meeting evolved from reviewing market research on consumer trends to finalizing specific design decisions for a new device, including its shape, color scheme, and power sources. The session concluded with the team agreeing on a snowman-shaped product in yellow and white that includes a jog dial and light feature while avoiding complex displays.
    decision  [12:15] The standby button should be red for easy identification.
    decision  [12:37] Buttons should be large and comfortable to press.
    decision  [13:31] Extra features beyond the basic ones should be hidden.
    decision  [20:49] The product must use simple components to reduce cost and development time.
    decision  [22:13] A light feature is a realistic goal to include.
    decision  [25:37] The product should have a unified look and feel rather than being a collection of disparate concepts.
    decision  [27:41] Go with a snowman type shape
    decision  [28:39] Use yellow and white colors
    decision  [30:12] No need for an LCD display
    decision  [36:18] Incorporate a jog dial into the design
    decision  [36:57] Place the slogan on the casing of the side
    decision  [37:34] Next meeting is in 30 minutes
    decision  [38:03] Jog dial should be flat and spun rather than locked
    decision  [38:24] Avoid big protruding rubber buttons; use flush materials or textured plastic
    action    [13:28] Craig: Discuss corporate color scheme and its application to the design.
    action    [09:47] (no owner): Revisit ideas regarding lighting and covers when moving to production.
    action    [17:53] (no owner): Check back on material combinations and restrictions
    action    [17:28] (no owner): See the other email regarding voice options
    action    [27:49] (no owner): Draw the design on the board
    action    [31:05] (no owner): Place advanced functionalities inside the snowman
    action    [37:02] (no owner): Get the slogan on the device
    action    [38:11] designers: Discuss logo incorporation and design details
    action    [38:46] speaker: Call the team regarding clothing
    question  [37:27] Whether the jog dial will lock users in based on handedness
    question  [38:19] What specific materials (plastic vs rubber) were previously agreed upon

- missing decision: {"text": "The remote will be curvy."}
- missing decision: {"text": "The remote will not have a talk-back function."}
- missing decision: {"text": "The case will have a soft fruit-like feel to it."}
- missing decision: {"text": "The remote will have a kinetic battery."}
- missing decision: {"text": "The remote will have rubber buttons."}
- missing action item: {"text": "Some team members will design a prototype of the remote"}
- grounding: open_questions: Q1 at 05:33 answered later, removed
- grounding: open_questions: Q2 at 05:22 answered later, removed
- grounding: open_questions: Q3 at 13:13 answered later, removed
- grounding: open_questions: Q4 at 13:41 answered later, removed
- grounding: open_questions: Q5 at 14:16 answered later, removed
- grounding: open_questions: Q6 at 17:21 answered later, removed
- grounding: open_questions: Q7 at 18:04 answered later, removed
- grounding: open_questions: Q8 at 19:23 answered later, removed
- grounding: open_questions: Q9 at 22:41 answered later, removed
- grounding: open_questions: Q10 at 24:29 answered later, removed
- grounding: open_questions: Q11 at 25:05 answered later, removed
- grounding: open_questions: Q12 at 28:51 answered later, removed
- grounding: open_questions: Q13 at 31:21 answered later, removed
- grounding: open_questions: Q14 at 36:18 answered later, removed
- grounding: action_items[1]: owner 'Speaker 1' is not named in the transcript, removed
- grounding: action_items[2]: owner 'null' is not named in the transcript, removed
- grounding: action_items[3]: owner 'null' is not named in the transcript, removed
- grounding: action_items[4]: owner 'null' is not named in the transcript, removed
- grounding: action_items[5]: owner 'null' is not named in the transcript, removed
- grounding: action_items[6]: owner 'null' is not named in the transcript, removed
