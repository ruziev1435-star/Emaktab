# Task 3 — Hand trace of the metro-fare flowchart

Fare tiers used (example scheme — substitute your instructor's actual numbers if different):

| Rides       | Price / ride |
|-------------|--------------|
| 1–10        | 25 som       |
| 11–30       | 20 som       |
| 31+         | 15 som       |

Tracing the flowchart in `metro-fare-flowchart.drawio` for each input:

| Rides | `r ≤ 10 ?` | `r ≤ 20 ?` (after first tier) | Running total     | Fare (som) |
|-------|------------|--------------------------------|--------------------|------------|
| 20    | No → total = 250, r = 10 | Yes → total += 10×20 | 250 + 200        | **450**    |
| 30    | No → total = 250, r = 20 | Yes → total += 20×20 | 250 + 400        | **650**    |
| 40    | No → total = 250, r = 30 | No → total += 20×20, r = 10; total += 10×15 | 250 + 400 + 150 | **800**    |
