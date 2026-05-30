---
title: SimGenerator — Requirements & Implementation Status
type: requirements
date: 2026-05-30
description: Full SimGenerator specification and implementation status table. The source of truth for requirement status.
tags: [simgenerator, requirements, traceability]
related: ["[[AGENTS]]", "[[STATUS]]", "[[known_issues]]", "[[test_strategy]]"]
---

# SimGenerator — Requirements & Implementation Status

This file documents the complete SimGenerator requirements.

## Input Parameters

1. **scenario_duration** [seconds]: Total length of each scenario
2. **max_multiple_events**: Maximum number of events per scenario (1 to N)
3. **min_Events_time_separation** [seconds]: Minimum gap between consecutive events
4. **generate_n_scenarios**: Total number of scenarios to generate
5. **selected_categories**: User selects which scenario categories to include

## CSV Format

### Structure

```
Row 1:  Description: <scenario description>
Row 2:  Initial gaps: <gap1>, <gap2>, ...
Row 3:  Time_s, Truck1_Velocity_kph, Truck1_Event, Truck2_Image_Event, Truck3_Image_Event, Notes
Row 4+: <timestamp>, <velocity>, <event>, <event>, <event>, <notes>
```

### Columns

- **Time_s**: Event timestamp (0 to scenario_duration) — must be monotonically increasing
- **Truck1_Velocity_kph**: Leader velocity (changes throughout scenario)
- **Truck1_Event**: Only FORT (emergency stop) events allowed
- **Truck2_Image_Event**: "Loss" or "Resume" events (identification loss/recovery)
- **Truck3_Image_Event**: "Loss" or "Resume" events (identification loss/recovery)
- **Notes**: Descriptive text (optional)

## Event Types & Rules

### 1. Velocity Events (Leader/Truck #1 only)

- **Nominal**: Velocity stays around target speed
- **Medium Variable**: ±X% variation around nominal
- **High Variable**: Full range variation around nominal
- **Leader Hard Braking**: Sharp velocity decrease event

Constraint: Exactly 1 velocity type per scenario (defines velocity profile for entire scenario)

### 2. Initial Gap Configuration (Set once at scenario start)

- **Small Gap**: Minimum allowed distance
- **Medium Gap**: Mid-range distance
- **Big Gap**: Maximum allowed distance
- **Variant Gaps**: First gap = small + second gap = large (or reversed)

Constraint: Exactly 1 gap type per scenario

### 3. Identification Loss Events (Truck #2 & Truck #3 only)

- **First Follower, Quick Resume**: Truck #2 loses ID, resumes in ~15s
- **First Follower, Slow Resume**: Truck #2 loses ID, resumes in ~60s
- **Second Follower, Quick Resume**: Truck #3 loses ID, resumes in ~15s
- **Second Follower, Slow Resume**: Truck #3 loses ID, resumes in ~60s
- **Frequent Losses, Variant Resumes**: Multiple Loss/Resume cycles with mixed timing (15-60s)

Implementation: Loss event at time T, Resume event at time T + duration (in separate CSV rows)

Constraint: 0 to N identification loss events per scenario

### 4. Emergency Stop (FORT) (Truck #1/Leader only)

- **FORT activated**: Only First Follower can trigger; single FORT event per scenario
- **Placement**: Must be last event in scenario — no other events after FORT

Constraint: 0 or 1 FORT event per scenario; if present, must be the final row with data

## Scenario Composition Rules

1. **Truck Count**: 2 or 3 trucks per scenario (randomly selected)
2. **Events per Scenario**: Random selection of 1 to max_multiple_events events
3. **Event Timing**: Random timestamps, separated by ≥ min_Events_time_separation seconds
4. **Event Categories**:
   - Exactly 1 velocity type per scenario
   - Exactly 1 gap type per scenario
   - 0 to N identification loss events
   - 0 or 1 FORT event (if present, must be last)
5. **FORT Constraint**: If FORT is included, no other events can follow it — it must be the last data row

## Scenario Naming Convention

Format: `<trucks>_<velocity>_<gaps>_<idLoss>_<FORT>.csv`

### Components

- **<trucks>**: `2T` or `3T`
- **<velocity>**: `nV` (nominal), `mV` (medium variable), `hV` (high variable), `hB` (hard brake)
- **<gaps>**: `sG` (small), `mG` (medium), `bG` (big), `vG` (variant)
- **<idLoss>**: `idL<count><types>` where:
  - count = number of identification loss events
  - types = `qs` (quick-short, ~15s), `sl` (slow, ~60s), `fv` (frequent variant, mixed timing)
  - or `none` if no ID loss events
- **<FORT>**: `1ES` (1 emergency stop) or `0ES` (no emergency stop)

### Examples

- `3T_hV_mG_idL2qs_1ES.csv` = 3 trucks, high variable velocity, medium gaps, 2 quick-short ID losses, 1 FORT
- `2T_nV_sG_none_0ES.csv` = 2 trucks, nominal velocity, small gaps, no ID losses, no FORT
- `3T_mV_vG_idL1sl_0ES.csv` = 3 trucks, medium variable velocity, variant gaps, 1 slow ID loss, no FORT

**Constraint:** Max 30 characters total

## Generator Workflow

1. **Generation**: Create scenarios by randomly combining categories within constraints
2. **Output Structure**:
   - Create timestamped folder: `Scene_Gen/ddmmyyyy_hhmm/`
   - Save each scenario as named CSV
3. **Comments**: Row 1 = human-readable description (simulator must ignore)

## GUI Features

1. **Category Selection**: Checkboxes for scenario categories (select all / partial)
2. **Generation Parameters**: Input fields for:
   - scenario_duration (seconds)
   - max_multiple_events
   - min_Events_time_separation (seconds)
   - generate_n_scenarios
3. **Progress Tracking**: Progress bar + event log window
4. **Controls**: Start / Stop / Pause buttons
5. **Output List**: Display generated scenarios (clickable to review)
6. **Scenario Editor**: View/Edit/Save/Save As for generated scenarios

## Simulator Modifications Required (For ConvoySIM Stage A)

### Already Supported

- Event parsing at arbitrary timestamps
- Velocity changes throughout scenario

### Must Add (After generation)

1. **Comment Line Handling**: Ignore Row 1 (Description) when parsing
2. **Loss/Resume Event Logic**: Parse "Loss" and "Resume" events, calculate duration from timestamps
3. **FORT Event Execution**: Implement emergency stop behavior when "FORT activated" is encountered

See: `ConvoyLogic.md` for resume timing implications

## Validation Constraints

- All timestamps must be ≤ scenario_duration
- Timestamps must be monotonically increasing
- Event timing must respect min_Events_time_separation
- FORT must be the last event if present
- Truck count must be 2 or 3
- Each scenario must have exactly 1 velocity type and 1 gap type

---

## Implementation Status

*Last updated: 2026-05-29*

Track every requirement here. A requirement is **complete** only when code is merged
AND there is a test or manual verification note.

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| P1 | scenario_duration input parameter | ✅ Complete | GUI + CLI |
| P2 | max_multiple_events input parameter | ✅ Complete | GUI + CLI |
| P3 | min_Events_time_separation input parameter | ✅ Complete | GUI + CLI |
| P4 | generate_n_scenarios input parameter | ✅ Complete | GUI + CLI |
| P5 | selected_categories (filter by scenario category) | ✅ Complete | Category filtering working; GUI checkboxes added |
| CSV1 | 6-column CSV format with correct headers | ✅ Complete | test_csv_output.py |
| CSV2 | Row 1 = Description | ✅ Complete | test_csv_output.py |
| CSV3 | Row 2 = Initial gaps (one value per column) | ✅ Complete | Fixed; test_csv_output.py |
| CSV4 | Timestamps monotonically increasing | ✅ Complete | validation.py + tests |
| E1 | Nominal velocity profile | ✅ Complete | events.py |
| E2 | Medium Variable velocity profile | ✅ Complete | events.py |
| E3 | High Variable velocity profile | ✅ Complete | events.py |
| E4 | Hard Brake velocity profile | ✅ Complete | events.py |
| E5 | Small / Medium / Big / Variant gap types | ✅ Complete | generator.py |
| E6 | Identification Loss events (Truck 2 & 3) | ✅ Complete | events.py |
| E7 | Quick-Short (~15 s) loss duration | ✅ Complete | events.py |
| E8 | Slow (~60 s) loss duration | ✅ Complete | events.py |
| E9 | FORT event — last row only | ✅ Complete | validation.py; Bug 11 fixed |
| N1 | Scenario naming convention (≤30 chars) | ✅ Complete | naming.py |
| N2 | Name encodes truck count, velocity, gap, losses, FORT | ✅ Complete | naming.py |
| N3 | Name matches actual CSV content (no silent drops) | ✅ Complete | Bug 11/12 fixed |
| GW1 | Generate scenarios combining categories | ✅ Complete | generator.py |
| GW2 | Save in Scene_Gen/ddmmyyyy_hhmm/ per run | ✅ Complete | Fixed 2026-05-29; gui.py + __main__.py |
| GW3 | Row 1 is a human-readable comment | ✅ Complete | csv_writer.py |
| G1 | Category selection checkboxes | ✅ Complete | Velocity, gap, loss, and FORT filters implemented |
| G2 | Generation parameters input fields | ✅ Complete | GUI Generate tab |
| G3 | Progress bar + event log | ✅ Complete | GUI Generate tab |
| G4 | Start button | ✅ Complete | "Generate Scenarios" button |
| G4a | Stop button | ✅ Complete | Stop button added to GUI; gracefully aborts generation |
| G4b | Pause button | ✅ Complete | Pause/Resume button implemented; sleeps when paused |
| G5 | Output list (clickable scenarios) | ✅ Complete | GUI Scenarios tab |
| G6 | Scenario Editor (View/Edit/Save/Save As) | ✅ Complete | GUI Scenarios tab — editable CSV table |
| V1 | All timestamps ≤ scenario_duration | ✅ Complete | validation.py |
| V2 | Timestamps monotonically increasing | ✅ Complete | validation.py |
| V3 | Event timing respects min_Events_time_separation | ✅ Complete | validation.py |
| V4 | FORT is last event if present | ✅ Complete | validation.py |
| V5 | Truck count is 2 or 3 | ✅ Complete | validation.py |
| V6 | Exactly 1 velocity type per scenario | ✅ Complete | generator.py |
| V7 | Exactly 1 gap type per scenario | ✅ Complete | generator.py |

---

## Phase 2: User Feedback & Enhancements (2026-05-29)

Based on testing and feedback, the following items require fixes and enhancements:

### Bug Fixes (Critical)

| ID | Issue | Current Behavior | Fix Required |
|---|---|---|---|
| **BUG-01** | Hard Brake deceleration too gentle | Takes 77s to decelerate from 60→20 kph (0.14 m/s²) | ✅ FIXED: Generate two velocity events seconds apart for ~2 m/s² deceleration |
| **BUG-02** | Loss/Resume sequencing invalid | Can have consecutive Loss or Resume events | ✅ FIXED: Per-truck Loss→Resume alternation enforced in validation + generator |
| **BUG-03** | FORT not generated when selected | User selects "Include FORT" but scenarios show "0ES" and no FORT event | ✅ FIXED: FORT generation now independent of loss events; respects user selection |
| **BUG-04** | Timestamp precision excessive | CSV has 3 decimals (77.007s) | ✅ FIXED: Timestamps now whole seconds (77s, no decimals) |

### Enhancements (Phase 2)

| ID | Category | Feature | Priority |
|---|---|---|---|
| **ENH-06** | Event Timing | Variable loss durations | Medium | ✅ DONE |
| **ENH-07** | Parameters | Configurable initial gaps with ranges | High | ✅ DONE |
| **ENH-08** | UI/UX | Row dividers in scenario viewer (zebra striping) | Low | ✅ Complete |
| **ENH-09** | UI/UX | Button caption clarity | Low | ✅ DONE |
| **ENH-10** | UI/UX | Dropdown for Truck1 event column | Medium | ✅ DONE |
| **ENH-11** | UI/UX | Output folder preview panel | Medium | ✅ DONE |
| **ENH-12** | UI/UX | Refresh scenarios list after Save As | Medium | ✅ DONE |

### Detailed Specifications

#### BUG-01: Hard Brake Deceleration Rate
**Current:** Hard brake velocity profile ends at 20 kph after 77+ seconds (0.14 m/s² deceleration)
**Required:** Two velocity events separated by seconds, creating ~2 m/s² deceleration (realistic emergency braking)
**Example:** Event at 10s: 60 kph → Event at 11s: 20 kph (approximately 18 m/s² deceleration, or ~2m/s² for actual vehicle with safety margin)

#### BUG-02: Loss/Resume Sequencing
**Current:** Can generate Loss, Loss, Resume, Resume (invalid logic)
**Required:** Loss and Resume events must alternate: Loss → Resume → Loss → Resume...
**Validation:** After event generation, verify no two consecutive events have same type (both Loss or both Resume)

#### BUG-03: FORT Selection Bug
**Current:** "Include FORT" checkbox selected → scenarios generated with "0ES" (no FORT)
**Root Cause:** Likely FORT filtering logic not working correctly with category selection
**Required:** Ensure FORT generation respects both `fort:yes`/`fort:no` filter AND general FORT probability logic

#### BUG-04: Timestamp Decimals
**Current:** Timestamps like `14.3`, `31.8`, `69.3` (3 decimals)
**Required:** Round to whole seconds: `14`, `32`, `69`
**Rationale:** Cleaner CSV; simulation timescale doesn't require sub-second precision

#### ENH-06: Variable Loss Durations
**Current:** Fixed durations (~15s quick, ~60s slow)
**Proposed:**
- **Quick-Short (qs):** 0–15 seconds (randomized)
- **Medium (new):** 15–40 seconds (randomized)
- **Slow (sl):** 40–60 seconds (randomized)
**Implementation:** Modify `events.py` loss creation functions to use `random.uniform(min, max)` instead of fixed value

#### ENH-07: Initial Gaps Configuration
**Current:** Single Gap Type selected (e.g., "Small" = 5m for all gaps)
**Proposed GUI:**
```
Gap 1: ◉ Fixed at [5.0] m  ◉ Range [5.0] to [10.0] m
Gap 2: ◉ Fixed at [10.0] m  ◉ Range [10.0] to [20.0] m
       ☐ Load from ConvoySIM parameters file
```
**Implementation:** Add `gap_config` to ScenarioConfig with per-gap settings; update `_generate_initial_gaps()` logic
**Known Issue:** Mark in documentation that ConvoySIM should be refactored to allow scenario-defined gaps to override default parameters (currently a conflict point)

#### ENH-08: Row Dividers in Scenario Viewer
**Current:** CSV table rows have no visual separation
**Proposed:** Add horizontal lines between rows for readability
**Implementation:** Modify `ttk.Treeview` styling or add separators to improve visual hierarchy

#### ENH-09: Button Caption
**Current:** "+ Add Row"
**Proposed:** "+ Add Row Below"
**Rationale:** Clarifies insertion point (new row added below selected row)

#### ENH-10: Truck1 Event Column Dropdown
**Current:** Free text input in Truck1_Event column (allows invalid values)
**Proposed:** Dropdown list with only valid values: `[blank, "FORT activated"]`
**Implementation:** Custom cell editor with combobox for Truck1_Event column

#### ENH-11: Output Folder Preview
**Current:** User browses to folder; no feedback on folder contents
**Proposed:** After folder selection, display list of .csv files in that folder on right side of Parameters panel
**Implementation:** Update `_browse_output_folder()` to populate a new listbox with folder contents

#### ENH-12: Refresh After Save As
**Current:** After "Save As" in Scenarios tab, new file not visible in Scenarios list until generation
**Proposed:** Auto-refresh `scenario_listbox` and reload scenario list from disk after save
**Implementation:** Call `_populate_scenario_list()` or reload from output folder after `_save_table_as()`

### Open Items (Phase 2 — In Progress)

**Critical Bugs (must fix):**
- BUG-01: Hard Brake deceleration rate (0.14 m/s² → 2 m/s²)
- BUG-02: Loss/Resume sequencing validation
- BUG-03: FORT selection not working
- BUG-04: Timestamp precision (3 decimals → 0 decimals)

**Enhancements (priority order):**
- ENH-07: Initial gaps configuration with ranges
- ENH-10: Truck1 event dropdown
- ENH-11: Output folder preview panel
- ENH-12: Refresh after Save As
- ENH-06: Variable loss durations
- ENH-08: Row dividers in viewer
- ENH-09: Button caption clarity

### Recently Fixed (Phase 3)

- **BUG-05** (2026-05-29): Velocity appeared constant for medium_variable and high_variable profiles. Root cause: `to_velocity_events()` in `events.py` filtered out velocity points where speed changed ≤5% from the previous point. The medium_variable random walk uses ±5% steps, so the filter threshold exactly matched the step size — every intermediate waypoint was dropped. Fix: removed the significance filter entirely. All profile points are now emitted. ConvoySIM needs every waypoint to interpolate correctly.
- **BUG-06** (2026-05-29): 2T scenarios assigned loss events to T3 (non-existent truck). Root cause: `generator.py` used `random.choice([2, 3])` regardless of `truck_count`. Fix: changed to `random.choice(list(range(2, truck_count + 1)))`. For 2T → only T2 available. For 3T → T2 or T3. Multiple losses on a 2T scenario now correctly cycle on T2 (Loss→Resume→Loss→Resume).
- **BUG-08 — max_events constraint violation** (2026-05-29 continued): Scenarios generated with far more total events than the `max_events` parameter allowed. Example: `max_events=3` produced 12 events (8 velocity waypoints + 2 Loss + 2 Resume). Root cause: `_compose_scenario()` calculated `num_loss_events = random.randint(0, max_events)` before generating velocity profile, treating max_events as a cap on loss events only. Velocity waypoints were never counted against the budget. Fix: moved velocity profile generation before loss event calculation. Now: (1) generate velocity profile, (2) count velocity events, (3) calculate remaining budget: `remaining = max_events - velocity_count`, (4) limit loss pairs to `remaining // 2`. Each scenario now correctly respects total event cap. Verified with max_events=3,5,10 — all scenarios pass constraint. All 130 tests passing.
- **ENH-14 — Scenario counters for sorting** (2026-05-29 continued): Scenario filenames now include numeric prefix for sorting. Example: `1_3T_hV_sG_idL2sl_0ES.csv`, `2_2T_nV_mG_none_0ES.csv`. Implementation: `csv_writer.py` `write_scenarios_batch()` uses `enumerate()` to prepend counter (1, 2, 3, ...). GUI `_populate_scenario_list()` automatically displays scenarios in counter order because they're stored in `self.scenarios` list in generation order. On-disk filenames now sort correctly alphabetically, matching generation order. Verified with 5-scenario batch — all filenames have correct counter prefix. Test updated: `test_write_scenarios_batch_filenames` expects `"1_scenario_A.csv"` and `"2_scenario_B.csv"`.

### Recently Fixed

**Phase 2 Critical Bugs (2026-05-29):**
- **BUG-01** (2026-05-29): Hard Brake deceleration rate fixed. Modified `events.py` `generate_hard_brake()` to calculate deceleration time based on target acceleration (~2 m/s²) instead of linear interpolation (was 0.14 m/s² over 77s). Added safety guards for edge cases (minimum 0.5s deceleration, brake_start_time clamped to [0, brake_time]).
- **BUG-02** (2026-05-29): Loss/Resume sequencing validation fixed. Changed `validation.py` to validate per-truck instead of globally, allowing independent Loss/Resume cycles for each truck. Generator `_assign_timestamps()` enhanced to prevent invalid sequences when placing multiple pairs for same truck by tracking truck_id and enforcing alternation pattern.
- **BUG-03** (2026-05-29): FORT generation fixed. FORT now independent of loss events. Modified `generator.py` line 132: was `has_fort = random.choice([True, False]) if (num_loss_events > 0 and fort_allowed)` → now `has_fort = fort_allowed and random.choice([True, False])`.
- **BUG-04** (2026-05-29): Timestamp precision fixed. Changed `models.py` CSVRow.to_csv_row() timestamp format from `.1f` (1 decimal) to `.0f` (0 decimals). Timestamps now whole seconds for cleaner output. Updated 4 test cases.

**Phase 2 Enhancements (2026-05-29):**
- **ENH-06** (2026-05-29): Variable loss durations implemented. Modified `events.py` `create_loss_resume_pair()` to use `random.uniform()` instead of fixed durations: QUICK_SHORT now 0–15s (was 15s), SLOW now 40–60s (was 60s), FREQUENT_VARIANT now 15–40s (was 30s). Updated test cases to validate ranges instead of exact values. Adjusted test parameters in `test_generator_events.py` to account for tighter spacing from randomized durations.
- **ENH-07** (2026-05-29): Custom gap configuration UI completed. Implemented Fixed/Range mode selector for each gap in GUI with conditional display of value spinbox vs min/max spinboxes. **IMPROVED LAYOUT**: Refactored to two-column design (Parameters left, Output Folder Contents right). Range fields now appear on same row as radio buttons, not below. Added `_update_gap_ui()` method to toggle spinbox/range frame visibility. Integrated gap configuration collection in `_start_generation()` to create `GapConfiguration` objects and pass to `ScenarioConfig`. Fixed grid layout issues (rows 11–15 correctly positioned). Added imports for `GapConfiguration` in gui.py. End-to-end testing confirms: Fixed mode produces exact values, Range mode produces values within specified bounds.
- **BONUS - Settings Persistence** (2026-05-29): Implemented automatic user preference persistence using INI file (`.simgen_settings.ini`). Settings automatically saved on window close and loaded on startup. Persists: scenario parameters (duration, max_events, min_sep, count), random seed, output folder, and gap configuration settings (modes + values). Tested: Save/load cycle works correctly across app restarts. All 130 tests passing.

**Phase 3 New Features (2026-05-29 continued):**
- **BUG-07 — Hard brake deceleration invisible** (2026-05-29): Hard brake scenarios showed only constant speed (e.g. `17.00, 17.00`) with no velocity drop. Root cause: `_assign_timestamps()` Step 1 applied `min_event_separation` filtering to velocity profile waypoints. The hard-brake profile has two waypoints only ~1.6 s apart (brake_start → brake_time) to represent the sharp deceleration; the filter dropped the deceleration target point as "too close". Additionally, Step 2 (FORT clearance) was then removing the post-brake constant-speed point. Fix: removed Step 1 entirely. Velocity profile waypoints form a continuous interpolated curve and must all be preserved; `min_event_separation` only applies to discrete events (loss, resume, FORT) which are handled in subsequent steps. Hard brake CSV now correctly shows: `t=0: 17.00 → t=73: 17.00 → t=74: 5.61` with FORT placed after the brake.
- **BUG-04b — Velocity decimals** (2026-05-29): Velocity values in CSV output were still formatted with 1 decimal place (e.g. `60.0`) after the timestamp fix. Root cause: `models.py` `CSVRow.to_csv_row()` used `:.1f` for velocity. Fixed to `:.0f` (whole kph). Also updated `events.py` velocity event notes from `:.1f` to `:.0f`. Updated 3 test assertions in `test_csv_output.py` and 1 test in `test_events.py` (nominal profile at 75 kph now correctly constructs profile with `max_velocity_kph=75.0`).
- **ENH-13 — Parameters file browser + velocity constraints** (2026-05-29): Added Parameters File browse button above Output Root Folder. GUI parses a ConvoySIM `parameters_3.csv`-format file (columns: Parameter, Value, Unit, Description) and extracts "Max velocity" and "Max acceleration" rows. Extracted values populate editable Max Velocity (kph) and Max Acceleration (m/s²) spinboxes. These values flow through `ScenarioConfig.max_velocity_kph` and `ScenarioConfig.max_acceleration_mps2` → `VelocityProfile._apply_constraints()` which (1) caps all waypoint velocities at `max_velocity_kph`, (2) enforces acceleration limiting (upward velocity changes throttled to `max_accel_mps2 × dt × 3.6 kph`). Deceleration is not limited (hard-brake profiles need free decel). Settings persist across sessions. All 130 tests pass.

**BUG-09 — Convoy startup instant velocity jump (2026-05-29 late evening):**
- **BUG-09 — Startup acceleration ramp**: All velocity profiles previously started at full target velocity at t=0 (e.g. 17 kph immediately). This caused following trucks to lose identification immediately because the convoy was already at speed when they started tracking. Fix: every velocity profile now starts at (t=0, 0 kph) and ramps up to the target velocity using `max_acceleration_mps2` as the rate. Added `_calc_ramp_time()` helper in `VelocityProfile`. All four profile types updated: NOMINAL gets 3 events (0→ramp→end), HARD_BRAKE gets 4-5 (0→ramp→brake_start→brake→end), MEDIUM_VARIABLE and HIGH_VARIABLE each get +1 point (startup rest). Updated generator budget thresholds: `max_events <= 4` → NOMINAL only; `<= 6` → + HARD_BRAKE; `<= 10` → + HIGH_VARIABLE; `>= 11` → all types. Updated `validate_event_separation()` and `test_min_event_separation` to skip consecutive velocity-to-velocity pairs (curve waypoints exempt from min_sep; only discrete events — loss, resume, FORT — are checked). Updated all affected tests (point counts, first-point assertions, range checks). Minimum valid `max_events` is now 3. All 130 tests passing.

**UI/UX Improvements (Session 2026-05-29 evening):**
- **ENH-15 — Tooltip helper system** (2026-05-29 evening): Added Tooltip class and "?" hover buttons for four form fields in Generate tab to reduce UI clutter while preserving information accessibility. Modified Parameters File section: added blue "?" button with tooltip explaining CSV format (parameters_3.csv), auto-fill behavior for Max Velocity/Acceleration, and constraint interpretation. Modified Random Seed section: added blue "?" button with tooltip explaining seed behavior and persistence across runs. Modified Output Root Folder section: added blue "?" button with tooltip explaining ddmmyyyy_hhmm subfolder creation. Modified Custom Gap Configuration section: added blue "?" button with tooltip explaining interaction between custom gap settings and gap type filter. Removed four inline hint text labels (originally at rows 5, 7, 10, 15) that cluttered the form. Updated all row numbers after removal (Output Root Folder: 7, separator: 8, gap controls: 12-13, separator: 14, categories: 15-16, buttons: 20). Tooltip uses yellow background (#ffffcc), black text, wraps at 300px, positioned right of target widget. All 130 tests passing. Visual separators organize form into logical sections (below Output Root Folder and Custom Gap Configuration).

**BUG-11 — Startup acceleration exceeds max_acceleration_mps2 (2026-05-29 late evening):**
- **BUG-11 — Ramp timestamp ceiling**: The startup ramp waypoint timestamp was computed as a raw float (e.g. 3.07 s) but formatted with `:.0f` in the CSV, which rounds DOWN via Python's banker rounding (3.07 → 3). This made the effective acceleration in the CSV `v / 3.6 / floor(ramp_time)` which could exceed `max_acceleration_mps2`. Example: 13.27 kph at 1.2 m/s² → raw=3.07 s → floored to 3 s → actual 1.23 m/s² > 1.2 limit. Fix: changed `_calc_ramp_time()` in `events.py` to return `float(math.ceil(raw_time))` so the integer-valued timestamp always represents ≥ the theoretical minimum time, keeping effective acceleration ≤ max. Added `import math` at top of `events.py`. No test changes needed. All 130 tests passing.

**Previous Fixes:**
- **G4a / G4b** (2026-05-29): Stop and Pause buttons implemented in GUI. Stop button aborts generation via threading.Event; pause button uses another event and sleeps 100ms while paused, checking for stop or resumed state. Both buttons update UI state appropriately.
- **P5 / G1** (2026-05-29): Category selection checkboxes now allow users to filter scenario generation by velocity type, gap type, loss type, and FORT events. Categories are passed via `selected_categories` list in `ScenarioConfig`; filtering logic applied in `_compose_scenario()`. GUI has four checkbox groups.
- **GW2** (2026-05-29): The `Scene_Gen/ddmmyyyy_hhmm` timestamped subfolder was only created when the output field was blank. Fixed to always append a timestamp regardless of what the user types in the output root field.
- **CSV3** (prev session): Initial gaps row was emitting all values in one cell. Fixed to one value per CSV column.
- **N3 / E9** (prev session): FORT event was silently dropped but name still claimed `1ES`. Fixed; name now reflects actual placed events.
