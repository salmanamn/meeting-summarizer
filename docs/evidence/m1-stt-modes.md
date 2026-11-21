# M1: Whisper sequential vs batched on M01 (23 lines)

- Date: 2026-11-21 15:18 UTC
- stt-small, int8, beam 5, 8 threads, batch size 4, voice-activity filter on, attendees as hotwords
- Same script, Piper seeds 0 to N-1: the audio differs slightly per seed, the words do not.

| Seed | Audio s | sequential WER | sequential segments | sequential s | batched WER | batched segments | batched s |
|---|---|---|---|---|---|---|---|
| 0 | 84.2 | 4.1% | 23 | 119.1 | 4.5% | 30 | 36.8 |
| 1 | 84.3 | 4.1% | 24 | 60.7 | 4.1% | 32 | 27.6 |
| 2 | 83.9 | 24.9% | 17 | 47.7 | 4.5% | 30 | 27.7 |
| 3 | 83.9 | 3.3% | 23 | 60.6 | 3.3% | 30 | 26.8 |
| 4 | 84.0 | 4.8% | 23 | 61.3 | 4.1% | 39 | 27.2 |

- sequential: 1 of 5 runs above 15% WER
- batched: 0 of 5 runs above 15% WER
