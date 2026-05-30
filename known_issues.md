---
title: SimGenerator — Known Issues
type: known-issues
date: 2026-05-30
description: Open bugs, debug notes, and regression guards for SimGenerator. Every bug gets a BUG-ID. Closed bugs stay here as regression guards — do not delete them.
tags: [simgenerator, bugs, regression, debugging]
related: ["[[AGENTS]]", "[[REQUIREMENTS]]", "[[test_strategy]]"]
---

# SimGenerator — Known Issues

> See [[AGENTS]] §7–§8 for the debugging and fix-validation workflow.
> **Closed bugs stay here as regression guards — never delete them.**
> Statuses: 🔴 open · 🟡 in-progress · ✅ closed (regression guard active)

---

## Open issues

*None currently open.* All known bugs are closed. See Closed issues below.

---

## Closed issues (regression guards)

| BUG-ID | Status | Symptom | Root cause | Fix | Regression guard |
|--------|:------:|---------|------------|-----|-----------------|
| BUG-01 | ✅ | Hard Brake deceleration too gentle (0.14 m/s² → 77s to slow down) | `generate_hard_brake()` used a single gentle slope | Generate two velocity events seconds apart for ~2 m/s² deceleration; minimum 0.5 s window, `brake_start_time` clamped ≥ 0 | `test_hard_brake_deceleration_rate` in `tests/test_events.py` |
| BUG-02 | ✅ | Consecutive Loss or Resume events (invalid sequencing) | Global loss/resume sequencing — no per-truck enforcement | Changed `validate_loss_resume_sequencing()` to per-truck validation; added Loss↔Resume alternation in generator | `test_loss_resume_sequencing` in `tests/test_scenario_composition.py` |
| BUG-03 | ✅ | FORT not generated when "Include FORT" selected | FORT was gated on `num_loss_events > 0` | FORT now independent: `has_fort = fort_allowed and random.choice([True, False])` | `test_fort_generated_when_selected` in `tests/test_generator_events.py` |
| BUG-04 | ✅ | Timestamps had 3 decimal places (e.g. 77.007) | `CSVRow.to_csv_row()` used `:.1f` format | Changed to `:.0f` — whole-second timestamps | `test_timestamp_format_whole_seconds` in `tests/test_csv_output.py` |
| BUG-04b | ✅ | Velocity values had 1 decimal (e.g. 60.0 instead of 60) | `CSVRow.to_csv_row()` used `:.1f` for velocity | Changed to `:.0f` for all velocity values | `test_velocity_format_no_decimals` in `tests/test_csv_output.py` |
| BUG-05 | ✅ | Velocity appeared constant (flat profile) | >5% significance filter dropped every waypoint (threshold matched step size) | Removed the significance filter in `to_velocity_events()` — all points emitted | `test_medium_variable_produces_multiple_distinct_velocities` in `tests/test_events.py` |
| BUG-06 | ✅ | 2-truck scenarios assigned losses to Truck #3 | `random.choice([2, 3])` always included T3 regardless of truck count | Changed to `random.choice(list(range(2, truck_count + 1)))` | `test_2T_losses_only_assigned_to_truck2` in `tests/test_generator_events.py` |
| BUG-07 | ✅ | Hard Brake velocity change not visible in output CSV | Same as BUG-05 — significance filter removed hard-brake intermediate points | Removed significance filter (see BUG-05 fix) | `test_hard_brake_visible_in_csv` in `tests/test_csv_output.py` |
| BUG-08 | ✅ | `max_events` constraint violated — total event count exceeded cap | `num_loss_events` sampled before velocity profile; velocity waypoints never counted against budget | Budget-aware type selection + remaining-budget FORT/loss calculation in `generator.py` | `test_max_events_never_exceeded` in `tests/test_generator_events.py` |
| BUG-09 | ✅ | Convoy startup instant velocity jump (follower ID loss on first step) | All profiles emitted first waypoint at t=0 with full target velocity | Added `_calc_ramp_time()` + startup `(0,0) → (ramp_time, nominal_kph)` prepend to all four profile types | `test_all_profiles_start_at_zero_velocity` in `tests/test_events.py` |
| BUG-10 | ✅ | Initial gaps values concatenated into one CSV cell | Row 2 writer joined all gap values into a single string | Each gap value now occupies its own CSV column | `test_initial_gaps_one_value_per_column` in `tests/test_csv_output.py` |
| BUG-11 | ✅ | Startup ramp could cause effective acceleration to exceed `max_acceleration_mps2` | `_calc_ramp_time()` returned raw float; `:.0f` formatting could round DOWN, making CSV effective accel > limit | Changed `_calc_ramp_time()` to `float(math.ceil(raw_time))` — timestamp always ≥ theoretical minimum | `test_ramp_timestamp_never_underestimates` in `tests/test_events.py` |
| BUG-12 | ✅ | Scenario filename loss type didn't match CSV content | `_assign_timestamps` returned 3-tuple; actual placed loss types not propagated back to naming | `_assign_timestamps` now returns 4-tuple including `actual_loss_types`; scenario name reflects actual content | `test_scenario_name_matches_csv_content` in `tests/test_naming.py` |

---

## Debugging playbook

When a test fails or unexpected behavior appears:

1. **Isolate:** run the specific failing test with `-v` to see the exact assertion.
2. **Read the traceback** in full — identify the exact line and variable values.
3. **Trace the root cause** — don't patch the symptom; find why the value is wrong.
4. **Record here** as a BUG-ID before fixing (even if you fix it immediately).
5. **Fix + re-run** the specific test, then the full suite.
6. **Add regression guard** — the test that would have caught this bug must exist.
7. **Update** the BUG entry to ✅ with the fix and guard details.

Common pitfalls:
- `random.seed()` must only be called once in `ScenarioGenerator.__init__` — calling it elsewhere breaks reproducibility tests.
- `_calc_ramp_time()` must use `math.ceil()`, not raw float — see BUG-11.
- `_assign_timestamps` returns a **4-tuple** (not 3) — unpacking the wrong count causes immediate AttributeError.
- Scenario name max 30 characters — `naming.py` enforces this; adding new event types requires verifying name length.
- `.simgen_settings.ini` settings persist between test runs in some environments — if tests behave strangely, check for stale INI values.
