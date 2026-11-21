# M2: Whisper threads on M01.wav

- Date: 2026-11-21 18:31 UTC
- Machine: Intel(R) Core(TM) i7-9750H CPU at 2.60GHz, 12 logical CPUs
- stt-small, batched, int8, beam 5, 2 run(s) per setting

| Threads | Fastest s | Slowest s | Audio s | RTF (fastest) | WER |
|---|---|---|---|---|---|
| 2 | 18.4 | 20.8 | 84.2 | 0.22 | 4.5% |
| 4 | 12.9 | 13.8 | 84.2 | 0.15 | 4.5% |
| 8 | 28.7 | 29.4 | 84.2 | 0.34 | 4.5% |

- Fastest: 4 threads.
