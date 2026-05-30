---
title: SimGenerator — Agent Operating Contract
type: instructions
date: 2026-05-30
description: Canonical agent operating contract for SimGenerator. Loaded by Cursor natively. Claude Code must be pointed here by CLAUDE.md. Single source of truth — no rules are restated elsewhere.
tags: [simgenerator, agent-instructions, closed-loop, cursor, claude-code]
related: ["[[REQUIREMENTS]]", "[[STATUS]]", "[[known_issues]]", "[[TASKS]]", "[[PLANNING]]"]
---

# SimGenerator — Agent Operating Contract

> Single source of truth for how AI agents work in this project. Loaded by Cursor natively.
> Claude Code: see `CLAUDE.md` — it points here as its first action.
> No rules are duplicated in any other file.

---

## 0. Role

You develop SimGenerator in a **closed loop**:

**Requirement → Clarify → Plan → Implement → Test → Debug → Fix → Regress → Validate → Document → Update memory → Verify completion**

Operate autonomously through this loop. The **one human checkpoint** is **UI/UX correctness during testing** — pause and ask the user at that point only.

---

## 1. Session start (do this first, every session)

Read in this order:

1. This file (you are here)
2. `STATUS.md` — current state, test count, last-known issues
3. `REQUIREMENTS.md § Implementation Status` — requirement status table
4. `TASKS.md` — open items
5. `known_issues.md` — open bugs and regression guards

Then post a **4-point session summary**:
- (a) What this project is (1–2 sentences)
- (b) Current status — done items, open requirements, test count
- (c) Open blockers or issues
- (d) What you intend to do this session

Only then proceed with the user's task.

---

## 2. Context-loading tiers

| Tier | Files | When to load |
|------|-------|-------------|
| **Always (Tier 1)** | This file, `STATUS.md`, `REQUIREMENTS.md`, `TASKS.md` | Every session |
| **On demand (Tier 2–3)** | `PLANNING.md`, `test_strategy.md`, `known_issues.md`, `decisions.md` | When relevant to the task |
| **Rarely (Tier 4)** | `progress.md`, `archive/*`, `PHASE5_SUMMARY.md` | Only when specifically needed |

Never bulk-load Tier 4.

---

## 3. In-conversation requirement tracking (IMMEDIATE — not deferred)

Whenever the user states a new requirement, a change, or a bug that implies a missing requirement:

**Before writing any code:**

1. Add (or update) a row in `REQUIREMENTS.md § Implementation Status` with status `⏳ In progress`.
2. If it is an open task, add it to `TASKS.md § Requirements Gaps`.
3. Then implement.
4. When verified (tests pass), update the row to `✅ Complete` and move the TASKS.md entry to `§ Recently Closed`.

This must happen within the **same response** where the work is done — not deferred to the end of the session.

---

## 4. Planning

Before coding:
- Restate the requirement ID(s) and acceptance criteria you are satisfying.
- List the minimal file changes needed.
- Note any risks or behavioral side-effects.

Do not rename public functions, classes, files, or data structures unless the task explicitly requires it.

---

## 5. Implementation

- Python 3.9+, pure stdlib + tkinter — no external dependencies.
- All public methods have docstrings and type hints.
- `random.seed()` is called once in `ScenarioGenerator.__init__` — nowhere else.
- CSV format is fixed at 6 columns; do not change column count or order.
- Scenario names are ≤ 30 characters; `naming.py` enforces this.
- Output always goes to `{scene_gen_root}/{ddmmyyyy_hhmm}/` — never directly to the root folder.
- Keep simulation/generation logic separate from GUI and file I/O.
- Validate inputs before running generation logic.

---

## 6. Testing

Run the full suite before ending any session:

```powershell
# From C:\dev\ConvoySIM\SimGenerator
python -m unittest discover tests -v
```

Rules:
- The **full suite must be green** before you end a session (currently 130 tests).
- Any new behavior needs a **test** mapped to its requirement ID.
- **Never skip or disable tests** to make the bar green.
- If tests cannot run, state exactly what was not run, why, and the risk.

---

## 7. Debugging

On any failure:
1. Find the **root cause** (not a symptom patch).
2. Record it in `known_issues.md` as a `BUG-NNN` entry with: symptom, root cause, fix, regression guard.

---

## 8. Fix validation

A fix is **not done** until:
- The specific failing test(s) pass.
- The full suite is green.
- The requirement row in `REQUIREMENTS.md` is updated to ✅.
- A regression guard exists in `known_issues.md`.

---

## 9. Regression

Before declaring a session complete:
- Full suite green ✅
- All `known_issues.md` regression guards pass ✅
- No previously-✅ requirement has regressed ✅

---

## 10. Documentation & memory (session end)

| File | What to update |
|------|---------------|
| `STATUS.md` | **Replace** the snapshot — current state, test count, open items, last-updated date |
| `progress.md` | Append a dated entry at the top (most-recent-first) |
| `decisions.md` | Record any non-obvious design decision |
| `REQUIREMENTS.md` | Verify all rows touched this session are ✅ or ❌ (not ⏳) |
| `TASKS.md` | Remove completed items; confirm open items are listed |
| `README.md` | Update if project direction, API, or GUI changed |
| `PLANNING.md` | Update if architecture or algorithms changed |

If nothing changed in a file, leave it.

---

## 11. Completion criteria

Do **NOT** say "done" unless:
- Every in-scope requirement is ✅ in `REQUIREMENTS.md § Implementation Status`
- Full suite is green
- No open blocker in `known_issues.md`
- `STATUS.md` snapshot is updated
- `progress.md` entry appended

---

## 12. Ask vs. continue

**ASK the user for:**
- UI/UX correctness during testing (the sanctioned human checkpoint)
- Ambiguous or conflicting requirements
- Destructive actions (deleting files, renaming public APIs)
- Scope changes

**CONTINUE independently for:**
- Work with a clear acceptance criterion
- Refactoring within established patterns
- Fixing a failing test with a known root cause

---

## 13. Hard rules

- **Never guess** at requirement intent — ask or record as open question.
- **Never skip or disable tests** to make the suite pass.
- **Never delete files** without listing them and getting explicit confirmation — archive instead.
- **Never lose a requirement** — every user requirement gets a row in REQUIREMENTS.md.
- **Never duplicate rules** across files — this file is the single source of truth.
- **Never commit secrets** — check `.gitignore` before any commit.
- **Never write "100% complete", "PRODUCTION READY"** unless every row in REQUIREMENTS.md is ✅.

---

## 14. Stack, module map & commands

### Stack
- Language: Python 3.9+, pure stdlib + tkinter (no external dependencies)
- Tests: `unittest` (discover pattern)
- GUI: `tkinter` (stdlib)
- Output: CSV files in `Scene_Gen/ddmmyyyy_hhmm/`

### Module responsibilities
| File | Responsibility |
|------|----------------|
| `models.py` | Data classes and enums only — no logic |
| `events.py` | Velocity profile generation; loss/resume pair creation |
| `generator.py` | Orchestration: selects event types, calls `_assign_timestamps`, validates |
| `validation.py` | Stateless constraint checks — raises `ValueError` on violation |
| `csv_writer.py` | Converts `Scenario` → CSV text/files; no generation logic |
| `naming.py` | Encodes/decodes scenario names; must round-trip perfectly |
| `gui.py` | Tkinter UI only — all logic stays in other modules |
| `__main__.py` | CLI entry point — thin wrapper around generator + csv_writer |

### Test modules
| File | Tests | Coverage |
|------|:-----:|---------|
| `tests/test_csv_output.py` | 28 | CSV format, column layout, row structure |
| `tests/test_naming.py` | 36 | Name encoding/decoding, round-trip, length constraint |
| `tests/test_events.py` | 15 | Velocity profiles, loss duration ranges |
| `tests/test_generator_events.py` | 20 | Timestamp assignment, FORT placement, event budgets |
| `tests/test_scenario_composition.py` | 11 | Constraint validation, truck count, event sequencing |
| `tests/test_integration.py` | 20 | End-to-end: config → generation → validation → CSV export |
| **Total** | **130** | |

### Key commands (run from `C:\dev\ConvoySIM\SimGenerator`)
```powershell
# Run full test suite
python -m unittest discover tests -v

# Launch GUI
python -m simgenerator

# CLI generation
python -m simgenerator --duration 120 --count 10 --output Scene_Gen
```

### Requirements reference
- `REQUIREMENTS.md` — full spec + implementation status table (update this for status changes)
- `known_issues.md` — bugs + regression guards
- `test_strategy.md` — test module → requirement mapping
