# Results

_Generated from `reports/`. Do not edit by hand._

## heldout seeds [9101, 9102, 9103] (config `cb3c3f3318ea`)

On 3 held-out seeds (117 simulated customers), the desk took customers live in 5.1 weeks against 9.4 today: 4.3 weeks sooner (95% interval 3.8–4.9), 100% on the committed date against 48%, and 0.0 P1 incidents per 10 go-lives against 2.3.

| Design | Weeks to go-live | On time | P1 per 10 go-lives | Exposures per 10 | Wrong answers per 1,000 | Security turnaround (weeks) | Weeks saved vs today |
|---|---|---|---|---|---|---|---|
| Today: least-busy manager takes it, a manual check the week before go-live, security answers every question | 9.4 (8.7–10.0) | 48% | 2.33 | 1.29 | 19.0 | 3.7 | – |
| Checks at kickoff, managers matched on skills and language, the questionnaire agent, the lead stepping in | 5.1 (4.8–5.3) | 100% | 0.00 | 0.00 | 3.6 | 1.0 | 4.3 (3.8–4.9) |
| Desk running the same checks only before go-live | 7.4 (7.2–7.7) | 79% | 0.00 | 0.00 | 3.6 | 1.0 | 1.9 (1.4–2.5) |
| Desk assigning the least-busy manager | 5.3 (5.1–5.5) | 99% | 0.00 | 0.00 | 3.6 | 1.0 | 4.1 (3.5–4.6) |
| Desk without the questionnaire agent | 7.5 (7.0–8.1) | 71% | 0.00 | 0.00 | 19.0 | 3.7 | 1.9 (1.6–2.2) |
| Desk without the lead stepping in on at-risk projects | 5.3 (5.0–5.5) | 96% | 0.00 | 0.00 | 3.6 | 1.0 | 4.1 (3.6–4.7) |

| Design | Revenue live inside the horizon, per seed | Manager-weeks over capacity | Lead hours per week stepping in |
|---|---|---|---|
| Today: least-busy manager takes it, a manual check the week before go-live, security answers every question | $1.81M | 22% | 0.0 |
| Checks at kickoff, managers matched on skills and language, the questionnaire agent, the lead stepping in | $2.21M | 23% | 1.9 |
| Desk running the same checks only before go-live | $1.97M | 19% | 2.3 |
| Desk assigning the least-busy manager | $2.19M | 27% | 2.1 |
| Desk without the questionnaire agent | $2.00M | 20% | 2.3 |
| Desk without the lead stepping in on at-risk projects | $2.20M | 26% | 0.0 |

Planted setup problems: 216; found by the kickoff checks: 216; blocker findings no planted problem explains: 0; questionnaire questions: 11,289.

| Gate | Measured | Pass |
|---|---|---|
| weeks saved, low end of the interval, at least 3.0 | 3.76 | yes |
| on-time share at least 90% | 100% | yes |
| P1 incidents per 10 go-lives at most 0.5 | 0.00 | yes |
| documents exposed per 10 go-lives at most 0 | 0.00 | yes |
| wrong questionnaire answers per 1,000 at most 30% of today's | 3.6 (cap 5.7) | yes |
| blocker findings no planted problem explains at most 0 | 0 | yes |

## dev seeds [1, 2, 3] (config `cb3c3f3318ea`)

On 3 development seeds (141 simulated customers), the desk took customers live in 5.0 weeks against 9.7 today: 4.7 weeks sooner (95% interval 4.3–5.2), 100% on the committed date against 35%, and 0.0 P1 incidents per 10 go-lives against 2.3.

| Design | Weeks to go-live | On time | P1 per 10 go-lives | Exposures per 10 | Wrong answers per 1,000 | Security turnaround (weeks) | Weeks saved vs today |
|---|---|---|---|---|---|---|---|
| Today: least-busy manager takes it, a manual check the week before go-live, security answers every question | 9.7 (9.3–10.2) | 35% | 2.30 | 1.15 | 21.1 | 4.4 | – |
| Checks at kickoff, managers matched on skills and language, the questionnaire agent, the lead stepping in | 5.0 (4.8–5.2) | 100% | 0.00 | 0.00 | 3.0 | 1.0 | 4.7 (4.3–5.2) |
| Desk running the same checks only before go-live | 7.4 (7.2–7.7) | 85% | 0.00 | 0.00 | 3.0 | 1.0 | 2.3 (1.8–2.8) |
| Desk assigning the least-busy manager | 5.3 (5.1–5.5) | 100% | 0.00 | 0.00 | 3.0 | 1.0 | 4.5 (4.1–4.9) |
| Desk without the questionnaire agent | 8.0 (7.6–8.4) | 58% | 0.00 | 0.00 | 21.1 | 4.4 | 1.8 (1.6–2.1) |
| Desk without the lead stepping in on at-risk projects | 5.4 (5.2–5.6) | 99% | 0.00 | 0.00 | 3.0 | 1.0 | 4.4 (4.0–4.8) |

| Design | Revenue live inside the horizon, per seed | Manager-weeks over capacity | Lead hours per week stepping in |
|---|---|---|---|
| Today: least-busy manager takes it, a manual check the week before go-live, security answers every question | $2.41M | 33% | 0.0 |
| Checks at kickoff, managers matched on skills and language, the questionnaire agent, the lead stepping in | $3.08M | 35% | 3.1 |
| Desk running the same checks only before go-live | $2.75M | 30% | 3.5 |
| Desk assigning the least-busy manager | $3.05M | 38% | 3.0 |
| Desk without the questionnaire agent | $2.69M | 31% | 3.2 |
| Desk without the lead stepping in on at-risk projects | $3.02M | 39% | 0.0 |

Planted setup problems: 263; found by the kickoff checks: 263; blocker findings no planted problem explains: 0; questionnaire questions: 13,848.

| Gate | Measured | Pass |
|---|---|---|
| weeks saved, low end of the interval, at least 3.0 | 4.29 | yes |
| on-time share at least 90% | 100% | yes |
| P1 incidents per 10 go-lives at most 0.5 | 0.00 | yes |
| documents exposed per 10 go-lives at most 0 | 0.00 | yes |
| wrong questionnaire answers per 1,000 at most 30% of today's | 3.0 (cap 6.3) | yes |
| blocker findings no planted problem explains at most 0 | 0 | yes |
