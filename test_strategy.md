---
title: SimGenerator — Test Strategy
type: test-strategy
date: 2026-05-30
description: How the SimGenerator test suite is structured, what it covers, how to run it, and how tests map to requirements.
tags: [simgenerator, testing, test-strategy]
related: ["[[AGENTS]]", "[[REQUIREMENTS]]", "[[known_issues]]"]
---

# SimGenerator — Test Strategy

> See [[AGENTS]] §6 for the testing rules (suite must be green before ending a session).
> See [[REQUIREMENTS]] for requirement ID → implementation status mapping.

---

## How to run

```powershell
# Full suite with verbose output (run from C:\dev\ConvoySIM\SimGenerator)
python -m unittest discover tests -v

# Single test module
python -m unittest tests.test_events -v

# Specific test
python -m unittest tests.test_events.VelocityProfileTest.test_all_profiles_start_at_zero_velocity -v
```

**Last confirmed full run:** 2026-05-29 — 130 tests, all passing.

---

## Test modules and requirement coverage

| Test module | Tests | Requirements covered |
|-------------|:-----:|---------------------|
| `tests/test_csv_output.py` | 28 | CSV1–CSV4, GW3, BUG-04/04b/10 regressions |
| `tests/test_naming.py` | 36 | N1, N2, N3, BUG-12 regression |
| `tests/test_events.py` | 15 | E1–E8, BUG-01/05/07/09/11 regressions |
| `tests/test_generator_events.py` | 20 | E9, GW1, G4a, BUG-03/06/08 regressions |
| `tests/test_scenario_composition.py` | 11 | V1–V7, BUG-02 regression |
| `tests/test_integration.py` | 20 | P1–P5, GW1/GW2, G1–G6, full pipeline |
| **Total** | **130** | |

---

## Coverage gaps

| Area | Gap | Priority |
|------|-----|:--------:|
| GUI end-to-end (Generate tab layout, Scenarios tab, tooltip hover, Stop/Pause threading) | No automated test — requires manual UI/UX review | 🔴 human checkpoint |
| Settings persistence across restarts | Tested manually; INI round-trip not unit-tested | 🟡 |
| Gap configuration semantics (weighted vs random within range) | Deferred — decision pending (see TASKS.md) | ⏳ |

---

## Rules for adding new tests

1. Every new behavior must have a test mapped to its requirement ID.
2. Test name: `test_<what>_<condition>_<expected>`.
3. Add the requirement → test mapping to `REQUIREMENTS.md § Implementation Status` in the same session.
4. If a bug is fixed, add a regression guard test and record it in `known_issues.md`.
5. Tests must not rely on `.simgen_settings.ini` state — use fresh `ScenarioConfig` instances.
6. Reproducibility tests must pass a fixed `seed` to `ScenarioGenerator` — never rely on `random.random()` directly.
