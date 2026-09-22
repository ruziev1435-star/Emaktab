# Task 3 — tracing the budget check by hand

The actual algorithm from class (flat rate, one condition):

```
READ rides
SET fare = 2100
SET total = rides x fare
PRINT total
IF total > 60000 THEN
    PRINT "over budget"
ELSE
    PRINT "within budget"
```

| Rides | total = rides × 2100 | total > 60000 ? | Result        |
|-------|------------------------|------------------|---------------|
| 20    | 42,000                 | No               | within budget |
| 30    | 63,000                 | Yes              | over budget   |
| 40    | 84,000                 | Yes              | over budget   |
