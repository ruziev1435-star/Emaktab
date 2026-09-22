# Task 3 — tracing the fare by hand

Fare rule I used (swap in the real numbers if the instructor gave different ones):

| Rides   | Price / ride |
|---------|--------------|
| 1–10    | 25 som       |
| 11–30   | 20 som       |
| 31+     | 15 som       |

Basically: first 10 rides are full price, next 20 are a bit cheaper, and anything past 30 rides is the cheap tier.

| Rides | First check (r ≤ 10?) | Second check (r ≤ 20?) | Total       | Fare |
|-------|------------------------|--------------------------|-------------|------|
| 20    | No → pay 10×25, 10 left | Yes → pay 10×20         | 250 + 200   | **450** |
| 30    | No → pay 10×25, 20 left | Yes → pay 20×20         | 250 + 400   | **650** |
| 40    | No → pay 10×25, 30 left | No → pay 20×20, 10 left, then 10×15 | 250 + 400 + 150 | **800** |
