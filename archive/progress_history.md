---
title: SimGenerator — Progress History (Archived)
type: archive
date: 2026-05-30
description: Early phase progress entries archived from progress.md on 2026-05-30. Preserved for historical reference.
tags: [simgenerator, archive, progress]
related: ["[[progress]]"]
---

# SimGenerator — Progress History (Archived)

> Archived from `progress.md` on 2026-05-30. See [[progress]] for current entries.

---

## 2026-05-29 — Phase 2 Enhancements: 4 UI/UX Features + Infrastructure

**What was done:**
- ENH-07: Initial Gaps Configuration (Infrastructure ✅, GUI 🔄) — Added `GapConfiguration` dataclass to models.py; extended `ScenarioConfig`; updated `_generate_initial_gaps()` in generator.py.
- ENH-09: Button Caption Clarity ✅ — Changed "+ Add Row" → "+ Add Row Below".
- ENH-08: Row Dividers in Scenario Viewer ✅ — Treeview style with 22px row height.
- ENH-12: Refresh Scenarios List After Save As ✅ — `_load_scenarios_from_folder()` method.
- ENH-10: Dropdown for Truck1 Event Column ✅ — ttk.Combobox, readonly, valid: blank or "FORT activated".

**Test count**: 130 (all passing)

---

## 2026-05-29 — Phase 2 Critical Bugs: All 4 Fixed & Verified

**What was done:**
- BUG-01: Hard Brake deceleration (0.14 m/s² → 2 m/s²) — two velocity events seconds apart.
- BUG-02: Loss/Resume sequencing — per-truck alternation enforcement in validation + generator.
- BUG-03: FORT not generated — FORT now independent of loss events.
- BUG-04: Timestamp precision — whole seconds (`.0f`).

**Test count**: 130 (all passing)

---

## 2026-05-29 — Phase 2 Requirements: User Feedback & Enhancements

**What was done:**
- Reviewed 12 user feedback items (4 critical bugs + 8 enhancements).
- Documented full specifications in REQUIREMENTS.md.
- Updated STATUS.md to reflect Phase 2 status.

---

## 2026-05-29 — Stop and Pause buttons (REQ G4a, G4b)

**What was done:**
- Implemented Stop button with `threading.Event` (`stop_signal`).
- Implemented Pause button toggling to "Resume" with sleep loop.
- All 130 tests pass.

---

## 2026-05-29 — Stop button implementation (REQ G4a)

**What was done:**
- Stop button added to GUI (disabled when not running).
- `stop_signal` threading.Event; progress callback raises RuntimeError if set.
- Graceful cleanup: re-enables Generate, disables Stop.

---

## 2026-05-29 — Category selection filtering (REQ P5/G1)

**What was done:**
- `_filter_by_category()` and `_is_category_allowed()` in generator.py.
- Category checkboxes in GUI: velocity, gap, loss, FORT.
- Format: `category_type:value` (e.g., `velocity_type:hV`). Unchecked = include all.

---

## 2026-05-29 — Doc system rebuild + requirement tracking

**What was done:**
- Fixed req 2.2 (Scene_Gen folder always created).
- Fixed 7 failing tests from session-2 changes.
- Consolidated from 15 → 8 MD files (removed COMPLETION_STATUS.md, PROJECT_SUMMARY.md, INDEX.md, ARCHITECTURE.md, QUICKSTART.md).
- Rewrote CLAUDE.md with session rituals and immediate tracking rule.

---

## 2026-05-29 — GUI rewrite + bug fixes 10/11/12

**What was done:**
- Merged 4 tabs → 2 tabs (Generate, Scenarios).
- Bug 10: Initial gaps — each gap in own CSV column.
- Bug 11: FORT silent drop — velocity tail cleared before FORT; `_assign_timestamps` returns 4-tuple.
- Bug 12: Loss type mismatch — all pairs share one type per scenario.

**Test count**: 130 (all passing)

---

## 2026-05-28 — Phase 6: GUI implementation

**What was done:**
- Built initial Tkinter GUI (4 tabs: Parameters, Generation, Browser, Viewer).
- Threading for background generation. Progress bar and status log. Scenario browser. CSV viewer.

**Test count**: 89

---

## 2026-05-28 — Phase 5: Full generator integration

**What was done:**
- Wired all modules in ScenarioGenerator. 25 integration tests. ConvoySIM Stage A compat verified.
- Performance: 333 scenarios/sec (33× target). Seed-based reproducibility.

**Test count**: 89

---

## 2026-05-28 — Phase 4: Naming & metadata

**What was done:**
- `naming.py`: ScenarioNameEncoder + ScenarioNameParser. Round-trip verified. ≤30 char constraint.

**Test count**: 64

---

## 2026-05-28 — Phase 3: CSV output

**What was done:**
- `csv_writer.py`. 28 unit tests. Fixed timestamp assignment bugs during CSV testing.

**Test count**: 69

---

## 2026-05-28 — Phase 2: Event generation

**What was done:**
- `events.py` (4 velocity types). `generator.py` `_assign_timestamps()`. `validation.py` (9 constraints). 40+ unit tests.

**Test count**: 41

---

## 2026-05-28 — Phase 1: Architecture & data model

**What was done:**
- `models.py` (all data classes + enums). `PLANNING.md`. `decisions.md` (first 2 decisions). Skeleton modules.

**Test count**: 0

---

## 2026-05-28 — Project initialisation

**What was done:**
- Created SimGenerator folder. Established base project docs. Documented scope and requirements.
