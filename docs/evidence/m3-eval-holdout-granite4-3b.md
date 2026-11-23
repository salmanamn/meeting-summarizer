# M3 evaluation: holdout set, granite4:3b

- Date: 2026-11-23 16:29 UTC
- Machine: Intel(R) Core(TM) i7-9750H CPU at 2.60GHz, 8 threads for speech to text
- The chat model in Ollama: 100% GPU (D30)
- Speech to text: stt-small (batched), faster-whisper 1.2.1
- Summary: granite4:3b, parts of at most 6000 characters, attachments 4000 characters, openai 3.57.0
- 4 meetings in 2.2 min (transcripts cached in out/eval/transcripts/ count as 0)
- Cells: matched / expected of found. Scripted meetings use keyword answers (D26); AMI meetings use the annotators' sentences (CC BY 4.0), matched by words, reported and not gated.

| Meeting | Kind | Minutes | WER | Parts | Summary s | Decisions | Actions | Questions | Forbidden | Confused |
|---|---|---|---|---|---|---|---|---|---|---|
| H01 | script | 0.7 | 8% | 1 | 20 | 2/2 of 2 | 2/2 of 2 | 1/1 of 1 | 0 | 0 |
| H02 | script | 0.4 | 0% | 1 | 3 | 0/0 of 0 | 0/0 of 0 | 1/1 of 2 | 0 | 0 |
| IS1009b | corpus | 34.2 | n/a | 6 | 62 | 1/4 of 7 | 0/1 of 7 | 0/0 of 0 | 0 | 0 |
| IS1009c | corpus | 30.3 | n/a | 4 | 45 | 0/3 of 9 | 2/4 of 4 | 0/0 of 0 | 0 | 1 |

## Totals (recall / precision per kind; detail rates on matched items)

| Group | Decisions | Actions | Questions | Owner | Due | Evidence | Source | Invented | Forbidden | Confused |
|---|---|---|---|---|---|---|---|---|---|---|
| scripted | 100% / 100% | 100% / 100% | 100% / 67% | 100% | 100% | 67% | n/a | 0 | 0 | 0 |
| AMI | 14% / 6% | 40% / 18% | n/a / n/a | n/a | n/a | n/a | n/a | 0 | 0 | 1 |

Reported only: the holdout set is never tuned against (D26).

## Summaries

### H01: Card printing vendor review

    title     Review of Card Printing Vendor
    overview  The meeting reviewed the current card printing vendor, which had two delays this year due to machine failure. The team decided to keep the current vendor until the contract ends in September and look for a backup. They also agreed to order 50,000 cards for the next batch and asked Omar to get quotes from other vendors by the end of the month.
    decision  [00:11] Keep the current vendor until the contract ends in September and look for a backup.
    decision  [00:25] Order 50,000 cards for the next batch.
    action    [00:16] Omar: Get two quotes from other vendors by the end of the month (due: by the end of the month)
    action    [00:23] (no owner): Write to the current vendor about the delays
    question  [00:25] Does the new chip supplier change the price?

- grounding: action_items[1]: owner 'Sara' is not named where the task is said, removed
- grounding: action_items[1]: due '00:23' is not what the meeting said, removed
- grounding: decisions[1]: evidence '00:36' (a line that says less of it) moved to '00:25'
- grounding: open_questions[0]: evidence '00:36' (a line that says less of it) moved to '00:25'

### H02: Summer campaign brainstorm, nothing decided

    title     Brainstorming Ideas for Summer Campaign
    overview  The meeting was a brainstorming session for ideas to promote the company during the summer. No decisions were made, and the discussion focused on potential campaign activities.
    question  [00:05] What would the cost of sponsoring a football tournament be?
    question  [00:07] What is the estimated cost of organizing a beach clean-up day with customers?

- grounding: open_questions[0]: evidence '00:11' (a line that says less of it) moved to '00:05'
- grounding: open_questions[1]: evidence '00:13' (a line that says less of it) moved to '00:07'

### IS1009b: AMI IS1009b: remote control design project

    title     Meeting on Remote Control Design and Features
    overview  The meeting focused on designing a universal remote control for various user groups, including elderly people and children. The team decided to create a single remote with customizable features like larger buttons, illuminated buttons, or different shapes to cater to specific demographics. The goal is to make the remote easy to use and an attractive impulse purchase by September.
    decision  [02:10] Gather suggestions from everyone involved and be open to various ideas
    decision  [03:46] Ensure product is available for purchase by September to sell as a Christmas gift
    decision  [05:54] Eliminate teletext feature
    decision  [11:49] Design for a single device with minimal buttons
    decision  [25:42] The target group is essentially everyone with a TV.
    decision  [27:17] The design should be adaptable for different user groups, such as elderly people needing larger buttons and children needing smaller, more precise buttons.
    decision  [32:25] Design one universal remote with customizable features for different user groups, such as larger buttons, illuminated buttons, or differently shaped buttons for specific demographics like children.
    action    [02:36] (no owner): Consult industrial engineer for input on feasibility of suggestions based on design and budget
    action    [03:55] (no owner): Consult user interface expert for input on prioritizing features and appearance
    action    [10:08] (no owner): Prepare the slideshow (due: 10)
    action    [16:48] (no owner): Display a clock on the remote controller
    action    [19:13] (no owner): Review the website for design ideas
    action    [30:44] (no owner): Determine the feasibility of creating a single remote with adjustable buttons for different user groups.
    action    [31:16] (no owner): Explore the possibility of designing different plastic cases for the remote, similar to removable covers for mobile phones.
    question  [04:54] What specific features should be included in the product?
    question  [08:49] How to best incorporate features that help users find the remote easily?
    question  [16:06] Will different shapes for buttons significantly improve usability for elderly or arthritic users?
    question  [10:26] What specific design elements should be prioritized for the remote control?
    question  [29:17] How much will it cost to design and produce different button sizes and colors for the remote?
    question  [30:44] Is it feasible to create a single remote that can be used by all user groups, or should we design separate remotes for each group?
    question  [32:09] Will the customizable features be effective if we design a single remote with all the different features for different people or if we design three different remotes for three different categories of people?

- missing decision: {"text": "They cannot make a device that works on the whole house- will need a focus."}
- missing decision: {"text": "They will maintain the corporate image by using the proper designs and colors."}
- missing decision: {"text": "Their target group is basically everybody who owns a TV."}
- missing action item: {"text": "*NA*"}
- grounding: open_questions: Q1 at 04:54 kept: no later item answers it
- grounding: open_questions: Q2 at 08:52 kept: no later item answers it
- grounding: open_questions: Q6 at 30:52 kept: no later item answers it
- grounding: action_items[0]: evidence '02:26' (a line that says less of it) moved to '02:36'
- grounding: action_items[1]: evidence '03:36' (a line that says less of it) moved to '03:55'
- grounding: action_items[2]: owner 'Not specified' is not named where the task is said, removed
- grounding: action_items[2]: due 'Not specified (asked to get the slideshow up, 10:08-10:13 and 10:23-10:28)' cut to the meeting's words '10'
- grounding: action_items[3]: evidence '17:01' (a line that says less of it) moved to '16:48'
- grounding: action_items[4]: evidence '19:12' (a line that says less of it) moved to '19:13'
- grounding: decisions[0]: evidence '02:03' (a line that says less of it) moved to '02:10'
- grounding: decisions[1]: evidence '02:26' (a line that says less of it) moved to '02:36'
- grounding: decisions[1]: repeats the action item at 02:36, removed
- grounding: decisions[2]: evidence '03:36' (a line that says less of it) moved to '03:55'
- grounding: decisions[2]: repeats the action item at 03:55, removed
- grounding: decisions[3]: evidence '03:55' (a line that says less of it) moved to '03:46'
- grounding: decisions[4]: evidence '06:18' (a line that says less of it) moved to '05:54'
- grounding: decisions[6]: evidence '17:01' (a line that says less of it) moved to '16:48'
- grounding: decisions[6]: repeats the action item at 16:48, removed
- grounding: decisions[7]: evidence '19:01' (a line that says less of it) moved to '19:13'
- grounding: decisions[7]: repeats the action item at 19:13, removed
- grounding: decisions[9]: evidence '28:08' (a line that says less of it) moved to '27:17'
- grounding: decisions[10]: evidence '32:59' (a line that says less of it) moved to '32:25'
- grounding: open_questions[1]: evidence '08:52' (a line that says less of it) moved to '08:49'
- grounding: open_questions[2]: evidence '16:31' (a line that says less of it) moved to '16:06'
- grounding: open_questions[3]: evidence missing, set to '10:26'
- grounding: open_questions[4]: evidence '28:47' (a line that says less of it) moved to '29:17'
- grounding: open_questions[5]: evidence '30:52' (a line that says less of it) moved to '30:44'

### IS1009c: AMI IS1009c: remote control design project

    title     Remote Control Design Meeting
    overview  The meeting covered the design of a remote control for a product, focusing on user interface, features, and functionality. The marketing manager emphasized an attractive design and short learning curve, while the technical manager suggested incorporating a chip with infrared bits and an interface. The interface designer proposed an on-off button and a compact, t-shaped design. The discussion covered various features like channel lock, volume control, subtitles, and color adjustments. The meeting concluded with decisions on user-friendly design, oversized size for safety, and the inclusion of speech recognizers as a personal preference. The team also agreed on using simple buttons, considering different energy sources, and focusing on a small, simple, and eye-catching design with obvious button functions.
    decision  [10:10] The design of the remote control should be user-friendly and attractive, with a compact and colorful interface for children.
    decision  [11:07] The remote control should be oversized to prevent misplacement.
    decision  [11:17] The inclusion of speech recognizers for user voice commands is a personal preference.
    decision  [19:53] Use simple buttons with a basic chip and printed circuits on the board
    decision  [20:42] Consider different energy sources like batteries, dynamo, and solar cells
    decision  [21:43] Use materials such as plastic, rubber, wood, and electronics like infrared sender and speaker
    decision  [23:55] Focus on small, simple, and eye-catching design with obvious button functions
    decision  [28:19] Agree on speech recognition as a potential star feature, pending further research on cost and functionality.
    decision  [27:19] Agree on battery as the primary energy source and a bright, colorful, trendy design for the case.
    action    [13:09] (no owner): Focus on the components and technical side of the remote controller design
    action    [22:54] Marketing expert: Marketing expert to present findings on the competition's remote controllers (due: the first)
    action    [28:45] UID: Design and develop the look and feel of the product
    action    [29:02] Jana and Francine: Work together on a prototype using modeling clay
    question  [02:41] Are we all in agreement that that's about what we discussed last time?
    question  [04:54] Whoever is presenting the remote control design should emphasize the interface and its attractiveness to customers.
    question  [12:22] Will the oversized remote control be an impulse purchase at the checkout counter?
    question  [22:29] Can scrolling be achieved by repeatedly pushing a button?
    question  [25:59] How far will speech recognition work and how to handle different voices?

- missing decision: {"text": "They decided that the product should be bright, colorful, trendy in design, strong, compact, have push buttons, and contain supplement features (possibly mute button, swapping button, voice recognition)."}
- missing decision: {"text": "The power source will be batteries because it is cost-effective."}
- missing decision: {"text": "They will have the industrial engineer do more research on the cost of voice recognition before deciding whether to include that function."}
- missing action item: {"text": "The industrial designer will come up with a user interface design."}
- missing action item: {"text": "Their coaches will send specific instructions and answer questions."}
- decisions: 'The design of the remote control should be user-friendly and attractive, with a compact and colorful interface for children.' is an expected action item
- grounding: open_questions: Q1 at 02:41 kept: no later item answers it
- grounding: open_questions: Q2 at 05:50 kept: no later item answers it
- grounding: open_questions: Q4 at 22:29 kept: no later item answers it
- grounding: action_items[0]: owner 'Speaker 2' is not named where the task is said, removed
- grounding: action_items[1]: evidence '23:03' (a line that says less of it) moved to '22:54'
- grounding: action_items[1]: due 'by the end of the month (not specified in the transcript, but implied by the context of the meeting being part of a series of meetings for a project with a deadline of the first of June, as mentioned in the previous meeting summary part 2 of 4 of the meeting 18:07 to 24:10; summarise only this part.)' cut to the meeting's words 'the first'
- grounding: action_items[3]: evidence '29:10' (a line that says less of it) moved to '29:02'
- grounding: decisions[1]: evidence '11:00' (a line that says less of it) moved to '11:07'
- grounding: decisions[2]: evidence '11:13' (a line that says less of it) moved to '11:17'
- grounding: decisions[3]: evidence '19:02' (a line that says less of it) moved to '19:53'
- grounding: decisions[4]: evidence '21:19' (a line that says less of it) moved to '20:42'
- grounding: decisions[5]: evidence '22:17' (a line that says less of it) moved to '21:43'
- grounding: decisions[6]: evidence '23:47' (a line that says less of it) moved to '23:55'
- grounding: decisions[8]: evidence '27:05' (a line that says less of it) moved to '27:19'
- grounding: open_questions[1]: evidence '05:50' (a line that says less of it) moved to '04:54'
- grounding: open_questions[4]: evidence '26:42' (a line that says less of it) moved to '25:59'
