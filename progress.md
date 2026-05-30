---
title: SimGenerator — Progress Log
type: progress
date: 2026-05-30
description: Chronological session log for SimGenerator. Most-recent entry first. Early phase entries archived in archive/progress_history.md.
tags: [simgenerator, progress]
related: ["[[AGENTS]]", "[[STATUS]]", "[[decisions]]"]
---

# SimGenerator — Progress Log

> See [[AGENTS]] §10 for session-end update rules. See [[STATUS]] for the current snapshot.
> Most-recent entry first. One entry per working session.
> **Archive rule:** entries older than ~3 months move to `archive/progress_history.md`. Keep only the last ~10 entries here.
> Early phase entries (2026-05-28 to early 2026-05-29) archived in `archive/progress_history.md`.

---

## 2026-05-30 — Agentic-dev remediation

**What was done:**
- Created canonical `AGENTS.md` (migrated CLAUDE.md content, fixed §6 requirement drift, updated file-discipline rule to new set).
- Converted `CLAUDE.md` to imperative pointer stub.
- Created `.cursor/rules/always.mdc` pointer (SimGenerator had no `.cursor/rules` before).
- Fixed `TASKS.md` Requirements Gaps — P5/G1, G4a, G4b moved to Recently Closed (they were ✅ complete but still listed as open).
- Created `known_issues.md` (12 closed BUGs with regression guards; BUG-01 through BUG-12).
- Created `test_strategy.md` (module → REQ coverage table).
- Pruned `progress.md` — early phase entries archived to `archive/progress_history.md`.
- Created `archive/` directory.
- Added vault YAML frontmatter to all docs missing it.
- `git init` + initial commit.

**Test count**: 130 (unchanged — docs-only session).

---

## 2026-05-29 (late evening, session 4) — BUG-11: Ramp Acceleration Ceiling

**What was done:**

BUG-11 — Startup ramp timestamp could cause acceleration to exceed `max_acceleration_mps2` (`events.py`).

Root cause: `_calc_ramp_time()` returned a raw float (e.g. 3.07 s). `:.0f` formatting uses Python's standard rounding and can round DOWN (3.07 → 3). The effective acceleration in the CSV then becomes `v / 3.6 / floored_time` which can exceed `max_acceleration_mps2`. Example: 13.27 kph at 1.2 m/s² → raw 3.07 s → CSV shows t=3 → actual accel = 1.23 m/s² > 1.2 limit.

Fix: Changed `_calc_ramp_time()` to return `float(math.ceil(raw_time))`.

**Test results**: 130 tests, all passing.

---

## 2026-05-29 (late evening, session 3) — BUG-09: Startup Acceleration Ramp

**What was done:**

BUG-09 — All velocity profiles emitted first waypoint at t=0 with full target velocity, causing instant speed jump and follower ID loss on startup.

Fix: Added `_calc_ramp_time(target_kph)` to `VelocityProfile`; all four `generate_*` methods now prepend `(0.0, 0.0) → (ramp_time_s, nominal_kph)`. Updated budget thresholds in `generator.py`. Minimum valid `max_events` is now 3.

**Test results**: 130 tests, all passing.

---

## 2026-05-29 (late evening, session 2) — ENH-15: Tooltip Helper System + Form Reorganization

**What was done:**
- New `Tooltip` class (hover-activated, yellow background, wraps at 300px).
- "?" buttons for four form fields (Parameters File, Random Seed, Output Root Folder, Custom Gap Configuration).
- Removed four inline hint text labels that cluttered the form.
- Updated row grid references throughout.

**Test results**: 130 tests, all passing. GUI manually tested.

---

## 2026-05-29 (late evening) — UI Improvements: Zebra Striping + Section Dividers

**What was done:**
- ENH-08: Alternating background colors in scenario data table (white / light gray).
- Added `ttk.Separator` visual dividers in Generate tab after Output Root Folder and Custom Gap Configuration sections.

**Test results**: 130 tests, all passing.

---

## 2026-05-29 (evening) — Phase 3 Continued: BUG-08 + ENH-14

**What was done:**
- BUG-08: max_events constraint — budget-aware type selection + budget-conscious FORT/loss in generator.py. Verified with max_events=3,5,7,10,15.
- ENH-14: Scenario counters — filenames prefixed with counter for natural sorting (e.g. `1_3T_hV_sG_idL2sl_0ES.csv`).

**Test results**: 130 tests, all passing.
