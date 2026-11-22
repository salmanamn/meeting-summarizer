# M3: local chat models on the tuning set

- Compared on 2026-11-22 from `out/eval/tuning-phi4-mini-3.8b.json`, `out/eval/tuning-granite4-3b.json`, `out/eval/tuning-llama3.2-3b.json`, `out/eval/tuning-qwen3.5-4b.json`
- Recall / precision on the scripted meetings; summary minutes for every meeting of the set, same machine, same cached transcripts.

| Model | Valid | Decisions | Actions | Questions | AMI recall (decisions / actions) | Summary min | Gates |
|---|---|---|---|---|---|---|---|
| phi4-mini:3.8b | 8/8 | 75% / 67% | 71% / 91% | 75% / 86% | 29% / 75% | 28.8 | FAILED: decisions recall, decisions precision, action items recall, evidence inside the line, source right, forbidden items (injection) |
| granite4:3b | 7/8 | 100% / 73% | 93% / 100% | 62% / 71% | 50% / 100% | 15.2 | FAILED: owner right, evidence inside the line, decision/action confusions |
| llama3.2:3b | 7/8 | 100% / 53% | 79% / 92% | 50% / 50% | 50% / 33% | 15.9 | FAILED: decisions precision, action items recall, open questions recall, evidence inside the line, source right, items where none are expected, forbidden items (injection) |
| qwen3.5:4b | 8/8 | 100% / 73% | 100% / 100% | 88% / 78% | 47% / 25% | 36.0 | FAILED: owner right, evidence inside the line, source right, decision/action confusions |
