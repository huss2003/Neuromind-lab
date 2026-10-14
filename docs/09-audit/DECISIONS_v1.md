# Decisions taken while implementing Requirements v1.0 (13 Oct 2026)
Taken from the requirements document where it was explicit; defaults are marked and need owner confirmation.

| Topic | Decision | Source / status |
|---|---|---|
| Attempts | Unlimited; abuse limits only (6/min, 2 in flight) | §6.2 — explicit |
| Best score | Highest score among completed graded attempts | §6.2 — explicit |
| Hint formula | -10 points per hint on the current attempt (configurable per exercise) | §25 open item — **default, confirm** |
| Appeals | Not enabled | §21 undecided |
| Teacher scope | Assignment table, revocable; admin sees all | §3, §21 — model implemented, **cohort rules to confirm** |
| Teacher feedback | Separate record; never changes scores; learner sees only published | §9.2 — explicit |
| Evidence | Versions, criteria, hints, correlation id stored with each attempt | §6.3 — explicit |
| Retention | Not decided; nothing is deleted automatically | §21 open |
| Out of scope (needs approval) | AI Tutor, RAG, agents, GPU/hosted AI, authoring/lab-lifecycle UI, multi-file IDE/terminal, proctoring, load certification of 200 learners | §2.2/§2.3/§10 |
