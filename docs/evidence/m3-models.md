# M3: local chat models on the tuning set

- Compared on 2026-11-23 from `out/eval/tuning-granite4-3b.json`, `out/eval/tuning-qwen3.5-4b.json`
- Recall / precision on the scripted meetings; summary minutes for every meeting of the set, same machine, same cached transcripts.

| Model | Valid | Decisions | Actions | Questions | AMI recall (decisions / actions) | Summary min | Where | Gates |
|---|---|---|---|---|---|---|---|---|
| granite4:3b | 7/8 | 100% / 89% | 93% / 100% | 75% / 75% | 67% / 0% | 3.8 | 100% GPU | FAILED: owner right, evidence inside the line |
| qwen3.5:4b | 8/8 | 100% / 89% | 100% / 100% | 100% / 73% | 59% / 25% | 11.4 | 100% GPU | FAILED: owner right, source right |
