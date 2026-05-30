---
title: SimGenerator — Current Status
type: status
date: 2026-05-30
description: Snapshot of current SimGenerator state, test count, and open items. Replace this snapshot each session — do not append history here.
tags: [simgenerator, status]
related: ["[[AGENTS]]", "[[REQUIREMENTS]]", "[[known_issues]]", "[[TASKS]]"]
---

# SimGenerator — Current Status

*This is the single source of truth for project status. Updated every session.*

**Last updated**: 2026-05-29 (late evening)
**Test count**: 130 (all passing)
**Version**: 2.2 (Phase 1+2 complete, Phase 3 complete)
**Status**: All features complete — BUG-11 fixed (startup ramp timestamp ceiling)

---

## Current state

| Area | Status | Notes |
|------|--------|-------|
| Core generation engine | ✅ Complete | models, events, generator, validation |
| CSV output | ✅ Complete | ConvoySIM Stage A compatible |
| Scenario naming | ✅ Complete | ≤30 chars, round-trip verified |
| Constraint validation | ✅ Complete | 9 rules enforced |
| GUI | ✅ Complete | 2-tab Tkinter UI with category checkboxes |
| Scene_Gen/ddmmyyyy_hhmm folder per run | ✅ Complete | Fixed 2026-05-29 |
| Test suite | ✅ 130 passing | unittest, 0 failures |
| Category selection checkboxes | ✅ Complete | Velocity, gap, loss, FORT filters |
| Stop button | ✅ Complete | Abort generation via thread signal |
| Pause button | ✅ Complete | Pause/Resume generation with sleep loop |
| Custom gap configuration | ✅ Complete | Fixed/Range modes, per-gap settings; same-row layout |
| Variable loss durations | ✅ Complete | Random ranges per loss type (ENH-06) |
| Velocity decimal format | ✅ Complete | All velocities 0 decimals in CSV (BUG-04b) |
| Parameters file browser | ✅ Complete | Browse CSV → auto-fills Max Velocity + Max Acceleration (ENH-13) |
| Velocity constraints | ✅ Complete | VelocityProfile caps vel + limits accel rate (ENH-13) |
| Output folder preview | ✅ Complete | Right-column panel showing CSV files (ENH-11) |
| FORT event dropdown | ✅ Complete | Truck1_Event column validation (ENH-10) |
| Settings persistence | ✅ Complete | Auto-save/load user preferences via INI file |
| Two-column layout | ✅ Complete | Parameters (left) + Output preview (right) |
| max_events constraint enforcement | ✅ Complete | Total event count (velocity + loss/resume + FORT) respects max_events (BUG-08) |
| Scenario filename counters | ✅ Complete | Filenames prefixed with counter for sorting (ENH-14) |
| Generate tab visual dividers | ✅ Complete | Separator lines organize sections (user request) |
| Scenario data zebra striping | ✅ Complete | Alternating row colors for readability (ENH-08) |
| Tooltip helper system | ✅ Complete | "?" hover buttons for four form fields reduce clutter (ENH-15) |
| Startup acceleration ramp | ✅ Complete | All profiles start at 0 kph and ramp up at max_acceleration rate (BUG-09) |
| Startup ramp accel ceiling | ✅ Complete | Ramp timestamp uses math.ceil so CSV never exceeds max_acceleration (BUG-11) |

**Phase 1 Status**: ✅ All core requirements complete (130 tests).
**Phase 2 Status**: ✅ Complete — 4 critical bugs fixed + 8 enhancements implemented.
**Phase 3 Status**: ✅ Complete — BUG-05 (velocity flat) + BUG-06 (2T assigns T3) + BUG-04b (velocity decimals) + ENH-13 (parameters file + velocity constraints) + BUG-07 (hard brake invisible).
**Overall**: 130 tests passing. Ready for use.

---

## Open requirements

All requirements are complete. See `REQUIREMENTS.md § Recently Fixed` for latest features.

---

## Deliverables

### Code modules
| File | Purpose | Status |
|------|---------|--------|
| `models.py` | Data structures and enums | ✅ |
| `events.py` | Velocity profile generation | ✅ |
| `generator.py` | Scenario generation engine | ✅ |
| `validation.py` | Constraint validation | ✅ |
| `csv_writer.py` | CSV file output | ✅ |
| `naming.py` | Scenario naming encode/decode | ✅ |
| `gui.py` | Tkinter GUI application | ✅ |
| `__main__.py` | CLI entry point | ✅ |

### Test modules
| File | Tests | Status |
|------|-------|--------|
| `tests/test_csv_output.py` | 28 | ✅ All pass |
| `tests/test_naming.py` | 36 | ✅ All pass |
| `tests/test_events.py` | 15 | ✅ All pass |
| `tests/test_generator_events.py` | 20 | ✅ All pass |
| `tests/test_scenario_composition.py` | 11 | ✅ All pass |
| `tests/test_integration.py` | 20 | ✅ All pass |
| **Total** | **130** | ✅ |

### Documentation
| File | Purpose | Status |
|------|---------|--------|
| `CLAUDE.md` | Claude working instructions | ✅ Current |
| `README.md` | User-facing overview and API | ✅ Current |
| `STATUS.md` | This file | ✅ Current |
| `progress.md` | Session log | ✅ Current |
| `decisions.md` | Design decision log | ✅ Current |
| `REQUIREMENTS.md` | Spec + implementation status | ✅ Current |
| `TASKS.md` | Open tasks | ✅ Current |
| `PLANNING.md` | Architecture reference | ✅ Current |

---

## Performance benchmarks (measured)

| Operation | 50 scenarios | Time | Rate |
|-----------|-------------|------|------|
| Generation | 50 | 0.15 s | 333/sec |
| CSV export | 50 files | 0.08 s | 625 files/sec |
| Validation | 50 | 0.03 s | 1 667/sec |

All targets exceeded by 25–33×.

---

## Known working configurations

```
Standard:  duration=120s  max_events=5  min_sep=5s   count=10–50   → fast, reliable
Stress:    duration=300s  max_events=10 min_sep=2s   count=100+    → still fast
Quick:     duration=60s   max_events=3  min_sep=5s   count=5       → instant
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `RuntimeError: Failed to generate after retries` | Impossible constraint combination | Increase duration, decrease max_events or min_sep |
| `ValueError: Scenario validation failed` | Generator bug (should not happen) | Check logs; file a bug report with seed value |
| GUI won't start | Tkinter missing or display unavailable | `python -m tkinter` to verify; use CLI instead |
| No timestamped subfolder created | Using old code (pre 2026-05-29 fix) | Pull latest — every run now always creates `ddmmyyyy_hhmm/` |

---

## Session history summary

| Date | Key work |
|------|----------|
| 2026-05-28 | Phases 1–6 built (architecture, generation, CSV, naming, integration, GUI) |
| 2026-05-29 | GUI rewrite (2-tab); bugs 10/11/12 fixed; req 2.2 fixed; doc system rebuilt |
