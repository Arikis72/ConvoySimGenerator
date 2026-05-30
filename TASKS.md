---
title: SimGenerator — Tasks
type: tasks
date: 2026-05-30
description: Open tasks for SimGenerator. Requirements Gaps are items stated in the spec but not yet built. Deferred items are non-blocking nice-to-haves.
tags: [simgenerator, tasks]
related: ["[[AGENTS]]", "[[REQUIREMENTS]]", "[[known_issues]]"]
---

# SimGenerator — Tasks

> See [[AGENTS]] §3 for the requirement-tracking workflow.
> See [[REQUIREMENTS]] for full implementation status.
> Open items only — completed items move to `§ Recently Closed`.

---

## Requirements Gaps

Open stated requirements — not deferred nice-to-haves.

*None currently open.* All stated requirements are ✅ Complete. See `REQUIREMENTS.md § Implementation Status`.

---

## Deferred / Future Work

Nice-to-haves not stated in the spec. Non-blocking.

- **Gap configuration semantics** (2026-05-29): Custom gap ranges [min, max] currently use pure random sampling. When a scenario has a gap type in its name (e.g., "bG"), users may expect the value to prefer the high end of the range for big gaps and the low end for small gaps. Options: (1) Weighted sampling; (2) Always use max for big, min for small; (3) Document that custom ranges override type semantics. Flagged for future refinement.
- Mixed loss types per scenario (e.g., `idL1qs1sl`) — currently all pairs share one type per scenario.
- Timestamp sampling optimisation with constraint solvers for very dense scenarios.
- Scenario persistence / caching between sessions.
- Scenario templates for common test patterns.
- REST API for programmatic batch generation.
- Multi-parameter optimisation integration with ConvoySIM Stage B.

---

## Recently Closed

| REQ | Description | Closed |
|-----|-------------|--------|
| P5 / G1 | Category selection checkboxes (velocity, gap, loss, FORT filters) + `selected_categories` in `ScenarioConfig` | 2026-05-29 |
| G4a | Stop button — abort in-progress generation via `threading.Event` | 2026-05-29 |
| G4b | Pause/Resume button — pause generation with sleep loop | 2026-05-29 |
| GW2 | Scene_Gen/ddmmyyyy_hhmm folder always created, even when output root is specified | 2026-05-29 |
| CSV3 | Initial gaps row: one value per CSV column (not concatenated) | 2026-05-29 |
| N3 | Scenario name always matches CSV content (no silent event drops) | 2026-05-29 |
| E9 | FORT event reliably placed via tail-clearing algorithm | 2026-05-29 |
