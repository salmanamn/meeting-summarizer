# M3 evaluation: holdout set, phi4-mini:3.8b

- Date: 2026-11-22 21:19 UTC
- Machine: Intel(R) Core(TM) i7-9750H CPU at 2.60GHz, 4 threads for speech to text
- Speech to text: stt-small (batched), faster-whisper 1.2.1
- Summary: phi4-mini:3.8b, parts of at most 6000 characters, attachments 4000 characters, openai 3.57.0
- 4 meetings in 29.0 min (transcripts cached in out/eval/transcripts/ count as 0)
- Cells: matched / expected of found. Scripted meetings use keyword answers (D26); AMI meetings use the annotators' sentences (CC BY 4.0), matched by words, reported and not gated.

| Meeting | Kind | Minutes | WER | Parts | Summary s | Decisions | Actions | Questions | Forbidden | Confused |
|---|---|---|---|---|---|---|---|---|---|---|
| H01 | script | 0.7 | 8% | 1 | 194 | 2/2 of 2 | 2/2 of 2 | 1/1 of 1 | 0 | 0 |
| H02 | script | 0.4 | 0% | 1 | 17 | 0/0 of 0 | 0/0 of 0 | 1/1 of 1 | 0 | 0 |
| IS1009b | corpus | invalid: merge: 1 problem(s), first at decisions: too_long | | | | | | | | |
| IS1009c | corpus | 30.3 | n/a | 4 | 280 | 0/3 of 4 | 1/4 of 1 | 0/0 of 0 | 0 | 0 |

## Totals (recall / precision per kind; detail rates on matched items)

| Group | Decisions | Actions | Questions | Owner | Due | Evidence | Source | Invented | Forbidden | Confused |
|---|---|---|---|---|---|---|---|---|---|---|
| scripted | 100% / 100% | 100% / 100% | 100% / 100% | 50% | 100% | 83% | n/a | 0 | 0 | 0 |
| AMI | 0% / 0% | 25% / 100% | n/a / n/a | n/a | n/a | n/a | n/a | 0 | 0 | 0 |

Reported only: the holdout set is never tuned against (D26).

## Summaries

### H01: Card printing vendor review

    title     Review Card Printing Vendor and Backup Plan
    overview  The meeting focused on addressing delays from the current card printing vendor and deciding to look for a backup vendor. Omar was tasked with getting quotes from other vendors by the end of the month, and Sara was to communicate the delays to the current vendor. The order quantity for the next batch was also confirmed at 50,000 cards.
    decision  [00:10] Keep the current vendor until the contract ends in September and look for a backup.
    decision  [00:36] Order 50,000 cards for the next batch.
    action    [00:16] Omar: Omar to get two quotes from other vendors by the end of the month. (due: by the end of the month)
    action    [00:23] Sara: Sara to write to the current vendor about the delays.
    question  [00:36] Do we know if the new chip supplier changes the price?

- grounding: action_items[1]: due 'null' is not what the meeting said, removed
- grounding: decisions[1]: repeats the action item at 00:16, removed
- grounding: decisions[2]: repeats the action item at 00:23, removed

### H02: Summer campaign brainstorm, nothing decided

    title     Summer Campaign Brainstorm
    overview  Attendees Noor, Yusuf, and Hana brainstormed ideas for a summer campaign, considering a football tournament and a beach clean-up day. They found both ideas interesting but couldn't decide on a cost for the tournament. They agreed to discuss the ideas further at a later time.
    question  [00:13] What would a tournament cost?


### IS1009c: AMI IS1009c: remote control design project

    title     Remote Control Design Meeting
    overview  Participants discussed features, designs, and technical aspects of a new remote control, focusing on simplicity, attractiveness, and user-friendliness. They considered push buttons, voice recognition, and compact design, and decided to use modeling clay for prototype development.
    decision  [22:51] We will just go for push buttons for interest of cost.
    decision  [25:44] Decide on the concept of the remote, including voice recognition as a potential feature, pending further research on cost and feasibility.
    decision  [27:39] Agree on the case design to be compact, trendy, and strong with a bright, colorful, and trendy appearance.
    decision  [29:02] Conclude the meeting with instructions for the next meeting and prototype development using modeling clay.
    action    [29:10] Jana and Francine: Design the user interface and create a prototype using modeling clay. (due: 30 minutes)
    question  [13:09] Who wants to go next?
    question  [25:59] How expensive and feasible is the implementation of voice recognition as a feature?

- missing decision: {"text": "They decided that the product should be bright, colorful, trendy in design, strong, compact, have push buttons, and contain supplement features (possibly mute button, swapping button, voice recognition)."}
- missing decision: {"text": "The power source will be batteries because it is cost-effective."}
- missing decision: {"text": "They will have the industrial engineer do more research on the cost of voice recognition before deciding whether to include that function."}
- missing action item: {"text": "The marketing expert will do the product evaluation."}
- missing action item: {"text": "The industrial designer will come up with a user interface design."}
- missing action item: {"text": "Their coaches will send specific instructions and answer questions."}
- grounding: open_questions: Q1 at 04:44 answered later, removed
- grounding: open_questions: Q3 at 22:33 answered later, removed
- grounding: action_items[0]: due '30 minutes from 29:47' cut to the meeting's words '30 minutes'
