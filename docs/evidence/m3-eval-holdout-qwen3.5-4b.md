# M3 evaluation: holdout set, qwen3.5:4b

- Date: 2026-11-23 16:55 UTC
- Machine: Intel(R) Core(TM) i7-9750H CPU at 2.60GHz, 8 threads for speech to text
- The chat model in Ollama: 100% GPU (D30)
- Speech to text: stt-small (batched), faster-whisper 1.2.1
- Summary: qwen3.5:4b, parts of at most 6000 characters, attachments 4000 characters, openai 3.57.0
- 4 meetings in 2.9 min (transcripts cached in out/eval/transcripts/ count as 0)
- Cells: matched / expected of found. Scripted meetings use keyword answers (D26); AMI meetings use the annotators' sentences (CC BY 4.0), matched by words, reported and not gated.

| Meeting | Kind | Minutes | WER | Parts | Summary s | Decisions | Actions | Questions | Forbidden | Confused |
|---|---|---|---|---|---|---|---|---|---|---|
| H01 | script | 0.7 | 8% | 1 | 18 | 2/2 of 2 | 2/2 of 2 | 1/1 of 1 | 0 | 0 |
| H02 | script | 0.4 | 0% | 1 | 4 | 0/0 of 0 | 0/0 of 0 | 1/1 of 1 | 0 | 0 |
| IS1009b | corpus | 34.2 | n/a | 6 | 84 | 2/4 of 14 | 0/1 of 6 | 0/0 of 0 | 0 | 0 |
| IS1009c | corpus | 30.3 | n/a | 4 | 64 | 0/3 of 7 | 2/4 of 5 | 0/0 of 0 | 0 | 0 |

## Totals (recall / precision per kind; detail rates on matched items)

| Group | Decisions | Actions | Questions | Owner | Due | Evidence | Source | Invented | Forbidden | Confused |
|---|---|---|---|---|---|---|---|---|---|---|
| scripted | 100% / 100% | 100% / 100% | 100% / 100% | 100% | 100% | 83% | n/a | 0 | 0 | 0 |
| AMI | 29% / 10% | 40% / 18% | n/a / n/a | n/a | n/a | n/a | n/a | 0 | 0 | 0 |

Reported only: the holdout set is never tuned against (D26).

## Summaries

### H01: Card printing vendor review

    title     Card printing vendor review and backup plan
    overview  The team discussed delays in card production caused by machine failures and decided to keep the current vendor until September while searching for a backup. Omar was assigned to gather quotes from other vendors, and the group confirmed ordering 50,000 cards instead of 70,000.
    decision  [00:11] Keep the current vendor until September
    decision  [00:25] Order 50,000 cards for the next batch
    action    [00:16] Omar: Get two quotes from other vendors (due: by the end of the month)
    action    [00:23] (no owner): Write to the current vendor about the delays
    question  [00:25] Does the new chip supplier change the price?

- grounding: action_items[1]: owner 'Sara' is not named where the task is said, removed
- grounding: open_questions[0]: evidence '00:36' (a line that says less of it) moved to '00:25'

### H02: Summer campaign brainstorm, nothing decided

    title     Summer campaign brainstorming session
    overview  Noor, Yusuf, and Hana discussed potential ideas for a summer campaign, including sponsoring a football tournament or organizing a beach clean-up day with customers. They noted that the clean-up day is likely cheaper but agreed to postpone proper discussion until another time.
    question  [00:11] What would a football tournament cost?


### IS1009b: AMI IS1009b: remote control design project

    title     Christmas Remote Controller Product Planning Meeting
    overview  The marketing team brainstormed features for an affordable Christmas gift remote controller, eventually deciding on a single universal design with cosmetic variations to target all TV owners. The discussion covered specific hardware requirements like integrated clocks and light indicators while eliminating complex functions such as teletext and child locks.
    decision  [00:48] Gather suggestions from everyone first, then filter based on feasibility, cost, and time.
    decision  [03:46] The product must go to market by September to sell for Christmas.
    decision  [03:33] The target price point is 25 euros.
    decision  [06:02] Eliminate teletext functionality; focus only on TV control
    decision  [07:36] Address user complaints about complex remotes by making them simple, obvious, and intuitive to use
    decision  [07:45] Incorporate features to help users find the remote, such as light emitting indicators or beeps
    decision  [08:52] Position the product as an attractive impulse purchase at 25 euros
    decision  [09:09] Consider using a motto like 'fashion in electronics' for marketing
    decision  [15:04] The child lock feature will be eliminated from the remote controller.
    decision  [16:48] The clock display feature will be included in the integrated circuit.
    decision  [26:14] The target group is defined as everyone who has a television.
    decision  [30:57] The basic electronics will remain the same for all designs, with differences only in the plastic case shape and button size.
    decision  [32:59] Target group is basically everybody if money permits
    decision  [32:25] Design one remote with functional cosmetic changes
    action    [05:11] (no owner): Provide specific feature suggestions instead of broad concepts like 'whole house control'.
    action    [05:29] (no owner): Confirm feasibility for controlling TV, VCR, stereo, and one other appliance.
    action    [09:42] Number two: Get the full screen slideshow up
    action    [10:08] (no owner): Talk about the working design of the remote controller
    action    [15:38] (no owner): Discuss button count and mode changes with the user interface person.
    action    [19:13] (no owner): Visit the referenced website to review working designs and gather new ideas
    question  [05:22] Can extended electronic entertainment control be implemented within the budget?
    question  [04:38] Which specific features will make customers take out their wallet for an impulse purchase?
    question  [11:49] How to design a remote controller for multiple devices given management's decision to eliminate multi-device compatibility
    question  [14:35] Whether it is possible to have the same machine with different shapes while keeping the budget impact low.
    question  [15:44] How many buttons are needed versus how many features can be supported.
    question  [20:10] Whether the group wants to view the website in full screen mode
    question  [30:12] Whether the budget allows for multiple distinct remote designs or if a single universal design is required.
    question  [29:36] How to practically accommodate elderly users with big buttons and children within a single device without compromising functionality.
    question  [32:59] Whether money will determine if features for subgroups can be implemented
    question  [32:59] When the next meeting will take place to revisit specific points

- missing decision: {"text": "They cannot make a device that works on the whole house- will need a focus."}
- missing decision: {"text": "They will maintain the corporate image by using the proper designs and colors."}
- missing action item: {"text": "*NA*"}
- grounding: open_questions: Q1 at 05:29 kept: no later item answers it
- grounding: open_questions: Q2 at 04:38 kept: no later item answers it
- grounding: open_questions: Q3 at 11:56 kept: no later item answers it
- grounding: open_questions: Q4 at 14:35 kept: no later item answers it
- grounding: open_questions: Q5 at 15:33 kept: no later item answers it
- grounding: open_questions: Q6 at 20:13 kept: no later item answers it
- grounding: open_questions: Q7 at 30:22 kept: no later item answers it
- grounding: action_items[0]: owner 'Marketing Manager' is not named where the task is said, removed
- grounding: action_items[1]: owner 'Industrial Engineer' is not named where the task is said, removed
- grounding: action_items[2]: evidence '09:34' (a line that says less of it) moved to '09:42'
- grounding: action_items[3]: owner 'Speaker (Number three)' is not named where the task is said, removed
- grounding: action_items[4]: owner 'null' is not named where the task is said, removed
- grounding: action_items[5]: evidence '19:24' (a line that says less of it) moved to '19:13'
- grounding: action_items[5]: owner 'Betsy' is not named where the task is said, removed
- grounding: decisions[1]: evidence '03:55' (a line that says less of it) moved to '03:46'
- grounding: decisions[2]: evidence '03:36' (a line that says less of it) moved to '03:33'
- grounding: decisions[3]: evidence '06:58' (a line that says less of it) moved to '06:02'
- grounding: decisions[4]: evidence '07:33' (a line that says less of it) moved to '07:36'
- grounding: decisions[5]: evidence '07:51' (a line that says less of it) moved to '07:45'
- grounding: decisions[8]: evidence '14:35' (a line that says less of it) moved to '15:04'
- grounding: decisions[9]: evidence '16:58' (a line that says less of it) moved to '16:48'
- grounding: decisions[11]: evidence '30:55' (a line that says less of it) moved to '30:57'
- grounding: open_questions[0]: evidence '05:29' (a line that says less of it) moved to '05:22'
- grounding: open_questions[2]: evidence '11:56' (a line that says less of it) moved to '11:49'
- grounding: open_questions[4]: evidence '15:33' (a line that says less of it) moved to '15:44'
- grounding: open_questions[5]: evidence '20:13' (a line that says less of it) moved to '20:10'
- grounding: open_questions[6]: evidence '30:22' (a line that says less of it) moved to '30:12'
- grounding: open_questions[7]: evidence '29:17' (a line that says less of it) moved to '29:36'
- grounding: open_questions[8]: evidence '33:27' (a line that says less of it) moved to '32:59'

### IS1009c: AMI IS1009c: remote control design project

    title     Remote Control Product Requirements and Design Meeting
    overview  The team discussed the requirements, interface concepts, and internal components for a new remote control product, ultimately deciding on push buttons and voice recognition as key features. The session concluded with specific tasks assigned to create prototypes and finalize designs.
    decision  [12:32] The decision-making process will be finalized after a week.
    decision  [22:51] We will use push buttons instead of scroll wheels for cost reasons.
    decision  [24:40] We must narrow the product features down to two key selling points to avoid consumer confusion.
    decision  [28:19] Voice recognition is selected as a potential star feature, pending further research on its cost and reliability.
    decision  [27:10] The product will use battery power as the energy source.
    decision  [27:19] The design must be bright, colorful, compact, and trendy.
    decision  [27:54] The user interface will utilize push buttons as the primary input method.
    action    [04:54] (no owner): Present the interface design
    action    [28:19] Industrial engineer: Conduct research on the cost and reliability of speech recognition technology.
    action    [28:45] Marketing expert: Create the look and feel design.
    action    [28:45] UID: Develop the user interface design.
    action    [29:02] Jana and Francine: Work together on a prototype using modeling clay.
    question  [04:40] Are we all in agreement that that's about what we discussed last time?
    question  [09:35] Can you go on to the next slide?
    question  [12:07] Whether any additional suggestions were needed to narrow down the options.
    question  [22:54] The marketing expert needs to present her findings on competition and consumer preferences.
    question  [25:53] How reliable will the speech recognition feature be in practice?
    question  [27:43] What does 'supplements' mean in the context of interface types?

- missing decision: {"text": "They decided that the product should be bright, colorful, trendy in design, strong, compact, have push buttons, and contain supplement features (possibly mute button, swapping button, voice recognition)."}
- missing decision: {"text": "The power source will be batteries because it is cost-effective."}
- missing decision: {"text": "They will have the industrial engineer do more research on the cost of voice recognition before deciding whether to include that function."}
- missing action item: {"text": "The marketing expert will do the product evaluation."}
- missing action item: {"text": "Their coaches will send specific instructions and answer questions."}
- grounding: open_questions: Q1 at 04:40 kept: no later item answers it
- grounding: open_questions: Q2 at 09:35 kept: no later item answers it
- grounding: open_questions: Q3 at 12:07 kept: no later item answers it
- grounding: open_questions: Q4 at 22:54 kept: no later item answers it
- grounding: action_items[0]: owner 'Francina' is not named where the task is said, removed
- grounding: decisions[0]: evidence '12:36' (a line that says less of it) moved to '12:32'
- grounding: decisions[6]: evidence '27:58' (a line that says less of it) moved to '27:54'
- grounding: open_questions[5]: evidence '28:09' (a line that says less of it) moved to '27:43'
