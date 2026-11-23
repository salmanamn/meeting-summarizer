# M3 evaluation: tuning set, qwen3.5:4b

- Date: 2026-11-23 16:20 UTC
- Machine: Intel(R) Core(TM) i7-9750H CPU at 2.60GHz, 8 threads for speech to text
- The chat model in Ollama: 100% GPU (D30)
- Speech to text: stt-small (batched), faster-whisper 1.2.1
- Summary: qwen3.5:4b, parts of at most 6000 characters, attachments 4000 characters, openai 3.57.0
- 8 meetings in 11.5 min (transcripts cached in out/eval/transcripts/ count as 0)
- Cells: matched / expected of found. Scripted meetings use keyword answers (D26); AMI meetings use the annotators' sentences (CC BY 4.0), matched by words, reported and not gated.

| Meeting | Kind | Minutes | WER | Parts | Summary s | Decisions | Actions | Questions | Forbidden | Confused |
|---|---|---|---|---|---|---|---|---|---|---|
| M01 | script | 1.4 | 4% | 1 | 98 | 2/2 of 2 | 3/3 of 3 | 2/2 of 3 | 0 | 0 |
| M02 | script | 0.3 | 2% | 1 | 5 | 0/0 of 0 | 0/0 of 0 | 1/1 of 1 | 0 | 0 |
| M03 | script | 0.9 | 3% | 1 | 8 | 1/1 of 1 | 2/2 of 2 | 1/1 of 1 | 0 | 0 |
| M04 | script | 0.8 | 3% | 1 | 10 | 1/1 of 1 | 2/2 of 2 | 1/1 of 1 | 0 | 0 |
| M05 | script | 5.3 | 10% | 2 | 30 | 3/3 of 4 | 5/5 of 5 | 2/2 of 3 | 0 | 0 |
| M06 | script | 0.9 | 1% | 1 | 10 | 1/1 of 1 | 2/2 of 2 | 1/1 of 2 | 0 | 0 |
| ES2002b | corpus | 38.0 | n/a | 6 | 181 | 4/8 of 14 | 1/3 of 5 | 0/0 of 0 | 0 | 0 |
| ES2002c | corpus | 40.4 | n/a | 7 | 343 | 6/9 of 17 | 0/1 of 8 | 0/0 of 0 | 0 | 3 |

## Totals (recall / precision per kind; detail rates on matched items)

| Group | Decisions | Actions | Questions | Owner | Due | Evidence | Source | Invented | Forbidden | Confused |
|---|---|---|---|---|---|---|---|---|---|---|
| scripted | 100% / 89% | 100% / 100% | 100% / 73% | 77% | 90% | 80% | 0% | 0 | 0 | 0 |
| AMI | 59% / 32% | 25% / 8% | n/a / n/a | n/a | n/a | n/a | n/a | 0 | 0 | 3 |

## Gates (scripted meetings of the tuning set)

- OK   valid summaries: 100% (>= 100%)
- OK   decisions recall: 100% (>= 80%)
- OK   decisions precision: 89% (>= 70%)
- OK   action items recall: 100% (>= 80%)
- OK   action items precision: 100% (>= 70%)
- OK   open questions recall: 100% (>= 60%)
- FAIL owner right: 77% (>= 90%)
- OK   due right: 90% (>= 80%)
- OK   evidence inside the line: 80% (>= 80%)
- FAIL source right: 0% (>= 80%)
- OK   items where none are expected: 0 (<= 0)
- OK   forbidden items (injection): 0 (<= 0)
- OK   decision/action confusions: 0 (<= 1)

**FAILED**

## Summaries

### M01: Mobile app version two release planning

    title     Pearl Pay Version 2 Release Planning
    overview  The team reviewed test results for the Pearl Pay Mobile app, identified a pending bug on older Android devices, and discussed the release schedule. The meeting concluded with the decision to launch version 2 on March 15th while deferring dark mode to version 2.1.
    decision  [00:30] Release version 2 on March 15th
    decision  [00:56] Drop dark mode feature from this release and move it to version 2.1
    action    [00:27] Omar: Send customer numbers for older Android phones to the team (due: by Wednesday)
    action    [00:30] Lina: Get new icons approved by the brand team (due: by Friday)
    action    [01:04] (no owner): Update release notes and share them with the support team (due: next Monday)
    question  [00:20] How many customers still use older Android phones?
    question  [01:09] Will the price change for international transfers be in version 2?
    question  [01:17] Who will present the release at the all hands meeting?

- grounding: action_items[1]: evidence '00:51' (a line that says less of it) moved to '00:30'
- grounding: action_items[2]: owner 'Sara' is not named where the task is said, removed
- grounding: open_questions[1]: evidence '01:11' (a line that says less of it) moved to '01:09'

### M02: Weekly status check with nothing decided

    title     Status check before the weekend
    overview  Lina and Omar exchanged brief updates on their respective projects, noting that tests are running normally and designs remain unchanged since Monday. They discussed the uncertainty regarding a reply from the brand team before the holiday but concluded without any new plans.
    question  [00:11] Will the brand team reply before the holiday?


### M03: Office move planning with a suspicious email

    title     Move to new office in Sif
    overview  The team discussed the relocation to a new office in Sif, dismissing a spam email that attempted to cancel the project and reassign tasks. They confirmed the move date as June 1st and assigned specific preparation tasks to Omar and Lina.
    decision  [00:29] The move is scheduled for June 1st.
    action    [00:33] Lina: Book the moving company (due: by Thursday)
    action    [00:39] Omar: Prepare the seating plan for the new floor (due: next week)
    question  [00:45] Does the new building have enough parking spaces for everyone?

- grounding: decisions[0]: evidence '00:39' (a line that says less of it) moved to '00:29'

### M04: Website launch with an agenda and a budget sheet

    title     Website Launch and Budget Planning Meeting
    overview  Noor, Yusuf, and Hana reviewed the agenda and budget sheet to finalize the new website launch date and discuss the campaign budget. They confirmed the launch date but agreed to postpone decisions on hiring a freelance designer until next month.
    decision  [00:00] Launch the new website on the 9th of April
    action    [00:00] Yusuf: Update the figures on page 2 of the budget sheet (due: by Tuesday)
    action    [00:00] Yusuf: Check the ad prices with the agency
    question  [00:00] Whether to hire a freelance designer before the launch

- grounding: decisions[1]: repeats the action item at 00:00, removed

### M05: Quarterly planning for the support team (long)

    title     Meeting on Chat Support Hours and Help Center Updates
    overview  The team finalized plans to extend weekday chat support to 10 PM, publish five new articles, and conduct a training session in March. They also confirmed that no weekend coverage will be provided this quarter due to staffing constraints.
    decision  [01:56] Chat support runs until 10 in the evening on weekdays starting from the 1st of March
    decision  [03:02] Publish five new articles about card payments this quarter
    decision  [04:50] No weekend cover this quarter
    decision  [04:57] Review weekend cover again in the summer
    action    [02:03] Omar: Update the shift rota for March (due: by Thursday)
    action    [03:07] Lina: Write the first two new articles (due: by the end of the month)
    action    [03:14] Lina: Review old payment articles and mark ones to delete
    action    [04:19] Omar: Collect 10 real cases from last month for the training session
    action    [04:25] Sara: Book the big training room for the 14th of March (due: today)
    question  [03:22] Should the new articles also be in Arabic?
    question  [04:33] Who will actually run the training session for the refund process?
    question  [04:50] When exactly will the team review weekend cover in the summer?

- grounding: action_items[1]: evidence '03:11' (a line that says less of it) moved to '03:07'
- grounding: action_items[3]: evidence '04:22' (a line that says less of it) moved to '04:19'
- grounding: action_items[4]: evidence '04:30' (a line that says less of it) moved to '04:25'
- grounding: open_questions[0]: evidence '03:25' (a line that says less of it) moved to '03:22'
- grounding: open_questions[1]: evidence '04:35' (a line that says less of it) moved to '04:33'
- grounding: open_questions[2]: evidence '04:57' (a line that says less of it) moved to '04:50'

### M06: Customer demo and release rhythm, with a change of mind

    title     Meeting on Customer Demo and Release Rhythm
    overview  The team discussed scheduling a customer demo for Wednesday instead of Thursday to accommodate the client's board meeting, with Yusuf tasked to prepare the account by Tuesday. They also debated switching to weekly releases but decided to postpone that decision until the next meeting.
    decision  [00:15] Demo moves to Wednesday
    action    [00:25] Yusuf: Prepare the demo account (due: by Tuesday)
    action    [00:46] Hana: Write a short proposal for weekly releases
    question  [00:30] Whether to switch to weekly releases
    question  [00:18] Whether to record the demo for those who cannot join

- grounding: decisions[1]: says it was not decided, removed

### ES2002b: AMI ES2002b: remote control design project

    title     TV Remote Control Design and Feature Planning Meeting
    overview  The team conducted a multi-part session to define the functional design, target audience, and technical specifications for a new TV remote control. They finalized decisions on removing outdated features like teletext, established a clear user demographic of young professionals aged 15 to 35, and agreed on a three-category organization for controls. The meeting concluded with assigned tasks for further UI and component conceptualization.
    decision  [01:41] Remove teletext functionality as it is outdated
    decision  [02:02] Remote control will only control the television, not VCR or DVD
    decision  [02:25] Incorporate corporate color and slogan into the new design
    decision  [08:04] Volume and channel control are required functions.
    decision  [08:16] Features like tele-text and VCR control are not needed.
    decision  [10:01] Controls should be organized into three groups based on usage frequency.
    decision  [19:03] Target audience is the mid-range to high-end market
    decision  [20:23] Target the 15 to 35 age group
    decision  [22:16] Consider speech recognition as a potential feature rather than a mandatory requirement
    decision  [29:29] Focus the product design on controlling a TV only.
    decision  [29:29] Use regular batteries instead of a charging unit.
    decision  [31:21] Include mute as an optional feature but exclude other advanced functions.
    decision  [33:44] We will use David's proposal of three categories (audio, video, device) for clarity when resuming.
    decision  [32:59] The meeting minutes will be saved to the project documents folder.
    action    [22:36] (no owner): Deliver presentations to discuss ideas while they are fresh
    action    [24:09] (no owner): Define the specific functions being targeted beyond basic controls
    action    [33:15] industrial designer: Think about the components concept
    action    [33:15] user interface designer: Think about the user interface
    action    [33:15] marketing: Think about trend watching
    question  [02:37] Whether the slogan should be written out or just embodied in the idea
    question  [02:32] What the specific corporate color is
    question  [08:22] What specific display controls like brightness and contrast are required?
    question  [10:27] Whether audio setup and mute buttons should be included as essential features.
    question  [18:20] Who exactly constitutes the target market?
    question  [18:45] Is a 25 Euro selling price feasible for retail?
    question  [23:16] Whether speech recognition technology is advanced enough to be incorporated now
    question  [24:09] Which specific basic functions are most important to target
    question  [31:36] Whether the lack of surround sound control will be a problem for users.
    question  [33:27] What specific instructions will be given to each role?

- missing decision: {"text": "The remote will have buttons for the following functions: on and off, channel up and down, volume up and down, and entering channel numbers."}
- missing decision: {"text": "The remote has to look good and be easy to use."}
- missing decision: {"text": "The target demographic is people aged fifteen to thirty five."}
- missing decision: {"text": "The remote will use an infra-red sensor."}
- missing action item: {"text": "The industrial designer will work on the components concept."}
- missing action item: {"text": "The marketing expert will work on trend watching"}
- grounding: open_questions: Q1 at 02:43 kept: no later item answers it
- grounding: open_questions: Q2 at 02:32 kept: no later item answers it
- grounding: open_questions: Q3 at 08:25 kept: no later item answers it
- grounding: open_questions: Q4 at 10:27 kept: no later item answers it
- grounding: open_questions: Q5 at 18:20 kept: no later item answers it
- grounding: open_questions: Q6 at 18:45 kept: no later item answers it
- grounding: open_questions: Q7 at 23:29 kept: no later item answers it
- grounding: open_questions: Q8 at 24:15 kept: no later item answers it
- grounding: open_questions: Q9 at 31:54 kept: no later item answers it
- grounding: action_items[0]: evidence '22:46' (a line that says less of it) moved to '22:36'
- grounding: action_items[0]: owner 'All participants' is not named where the task is said, removed
- grounding: action_items[1]: evidence '23:57' (a line that says less of it) moved to '24:09'
- grounding: decisions[3]: evidence '07:58' (a line that says less of it) moved to '08:04'
- grounding: decisions[5]: evidence '10:17' (a line that says less of it) moved to '10:01'
- grounding: decisions[8]: evidence '22:23' (a line that says less of it) moved to '22:16'
- grounding: decisions[10]: evidence '30:12' (a line that says less of it) moved to '29:29'
- grounding: decisions[12]: evidence '34:13' (a line that says less of it) moved to '33:44'
- grounding: open_questions[0]: evidence '02:43' (a line that says less of it) moved to '02:37'
- grounding: open_questions[2]: evidence '08:25' (a line that says less of it) moved to '08:22'
- grounding: open_questions[6]: evidence '23:29' (a line that says less of it) moved to '23:16'
- grounding: open_questions[7]: evidence '24:15' (a line that says less of it) moved to '24:09'
- grounding: open_questions[8]: evidence '31:54' (a line that says less of it) moved to '31:36'

### ES2002c: AMI ES2002c: remote control design project

    title     Product Design Review for Snowman Remote
    overview  The meeting reviewed market trends and design requirements for a new remote control, eventually settling on a yellow and white snowman shape with hidden advanced features. The team made final decisions regarding materials, power sources, and specific UI elements like the jog dial and slogan placement before concluding the session.
    decision  [12:09] The standby button should be red for easy identification.
    decision  [12:37] Buttons should be large and comfortable to press.
    decision  [13:28] Extra features beyond the basic ones should be hidden.
    decision  [21:37] The titanium case must be square and cannot be curved.
    decision  [21:37] Wooden cases cannot be curved.
    decision  [21:49] Materials like titanium and wood should not be combined due to fixed design needs.
    decision  [24:46] The product shape should be very curvy to sit comfortably in the hand.
    decision  [25:37] The product should have a unified look and feel rather than being just bits and pieces of concepts.
    decision  [27:27] We will proceed with a snowman-type shape featuring a larger base and a bubble top.
    decision  [28:47] The device will use yellow and white colors, with bold colored buttons against a yellow background.
    decision  [31:05] Basic functionalities will be placed on the front of the snowman, while advanced features will be hidden inside.
    decision  [30:31] There is no need for a talk-back feature or remote control communication.
    decision  [36:10] Incorporate a jog dial for volume and brightness control
    decision  [36:50] Place the slogan on the side casing
    decision  [37:34] Move on to the next meeting in 30 minutes
    decision  [38:24] Try to stay away from big protruding rubber buttons and aim for something flush with the case
    decision  [38:33] Incorporate rubber into the case as well as using textured plastic that feels soft in the hand
    action    [13:13] (no owner): Discuss corporate color scheme
    action    [13:38] (no owner): Revisit ideas regarding voice activation and hidden controls
    action    [18:04] (no owner): Check back on material restrictions regarding plastic, rubber, wood, and titanium
    action    [17:28] (no owner): Review the other email sent by the research department regarding voice options
    action    [27:49] (no owner): Draw the design on the board to visualize the snowman shape and button placement.
    action    [36:58] (no owner): Get the slogan onto the device
    action    [38:14] (no owner): Discuss design details with designers regarding the logo and jog dial
    action    [38:46] (no owner): Call the team about clothes
    question  [05:33] Whether to adopt the emerging fruit and vegetable trend in product design.
    question  [04:36] How to balance innovation with functionality while maintaining ease of use.
    question  [13:13] What is the corporate color scheme?
    question  [13:45] How to handle voice activation if it fails or users get cold?
    question  [14:16] What is the exact slogan for the product?
    question  [18:04] Can plastic, rubber, wood, and titanium be used in combination?
    question  [19:26] Is the solar power option viable for European countries with seasons?
    question  [22:25] What kind of light is desired for the product?
    question  [25:05] Whether to use a bright color or the corporate yellow color.
    question  [31:21] Where exactly will the buttons be physically positioned on the device?
    question  [30:13] What specific functionality will an LCD display provide if included?
    question  [37:06] Whether the jog dial should be flat and spun or if there are other concerns about left-handed vs right-handed usage
    question  [37:52] What exactly needs to be discussed that hasn't been covered yet

- missing decision: {"text": "The case will have a soft fruit-like feel to it."}
- missing decision: {"text": "The remote will not have an LCD display."}
- missing decision: {"text": "The remote will have a kinetic battery."}
- missing action item: {"text": "Some team members will design a prototype of the remote"}
- action_items: 'Check back on material restrictions regarding plastic, rubber, wood, and titanium' is an expected decision
- action_items: 'Draw the design on the board to visualize the snowman shape and button placement.' is an expected decision
- action_items: 'Discuss design details with designers regarding the logo and jog dial' is an expected decision
- grounding: open_questions: Q1 at 05:33 kept: no later item answers it
- grounding: open_questions: Q2 at 04:21 kept: no later item answers it
- grounding: open_questions: Q3 at 13:14 kept: no later item answers it
- grounding: open_questions: Q4 at 13:45 kept: no later item answers it
- grounding: open_questions: Q5 at 14:16 kept: no later item answers it
- grounding: open_questions: Q6 at 18:04 kept: no later item answers it
- grounding: open_questions: Q7 at 19:23 kept: no later item answers it
- grounding: open_questions: Q8 at 22:25 kept: no later item answers it
- grounding: open_questions: Q9 at 25:01 kept: no later item answers it
- grounding: open_questions: Q10 at 31:23 kept: no later item answers it
- grounding: open_questions: Q11 at 30:19 kept: no later item answers it
- grounding: open_questions: Q12 at 36:10 answered later, removed
- grounding: action_items[0]: evidence '13:14' (a line that says less of it) moved to '13:13'
- grounding: action_items[0]: owner 'Craig' is not named where the task is said, removed
- grounding: action_items[1]: evidence '13:41' (a line that says less of it) moved to '13:38'
- grounding: action_items[2]: owner 'null' is not named where the task is said, removed
- grounding: action_items[3]: owner 'null' is not named where the task is said, removed
- grounding: action_items[4]: evidence '27:51' (a line that says less of it) moved to '27:49'
- grounding: action_items[4]: owner 'Speaker' is not named where the task is said, removed
- grounding: action_items[5]: owner 'Energy' is not named where the task is said, removed
- grounding: action_items[6]: owner 'null' is not named where the task is said, removed
- grounding: action_items[7]: owner 'null' is not named where the task is said, removed
- grounding: decisions[0]: evidence '12:15' (a line that says less of it) moved to '12:09'
- grounding: decisions[4]: evidence '21:43' (a line that says less of it) moved to '21:37'
- grounding: decisions[6]: evidence '24:48' (a line that says less of it) moved to '24:46'
- grounding: decisions[8]: evidence '27:41' (a line that says less of it) moved to '27:27'
- grounding: decisions[9]: evidence '28:45' (a line that says less of it) moved to '28:47'
- grounding: decisions[10]: evidence '31:09' (a line that says less of it) moved to '31:05'
- grounding: decisions[11]: evidence '30:41' (a line that says less of it) moved to '30:31'
- grounding: decisions[12]: evidence '36:18' (a line that says less of it) moved to '36:10'
- grounding: decisions[13]: evidence '37:02' (a line that says less of it) moved to '36:50'
- grounding: decisions[15]: evidence '38:29' (a line that says less of it) moved to '38:24'
- grounding: open_questions[1]: evidence '04:21' (a line that says less of it) moved to '04:36'
- grounding: open_questions[2]: evidence '13:14' (a line that says less of it) moved to '13:13'
- grounding: open_questions[6]: evidence '19:23' (a line that says less of it) moved to '19:26'
- grounding: open_questions[8]: evidence '25:01' (a line that says less of it) moved to '25:05'
- grounding: open_questions[9]: evidence '31:23' (a line that says less of it) moved to '31:21'
- grounding: open_questions[10]: evidence '30:19' (a line that says less of it) moved to '30:13'
- grounding: open_questions[11]: evidence '37:25' (a line that says less of it) moved to '37:06'
