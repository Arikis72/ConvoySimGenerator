---
title: SimGenerator — Planning & Architecture
type: planning
date: 2026-05-30
description: Architecture, data model, and key algorithms for SimGenerator. Load on demand when making architectural decisions.
tags: [simgenerator, planning, architecture]
related: ["[[AGENTS]]", "[[REQUIREMENTS]]", "[[decisions]]"]
---

# SimGenerator — Planning & Architecture

*Last updated: 2026-05-29*

This document is the technical reference for architecture, data model, and
key algorithms. It is updated when architecture or algorithms change.
For current project status see STATUS.md. For design rationale see decisions.md.

---

## Data model

```
┌─────────────────────────────────────────────────────────────┐
│                      Scenario (complete)                     │
├─────────────────────────────────────────────────────────────┤
│ metadata: ScenarioMetadata                                   │
│   ├─ name: str  (e.g. "3T_hV_mG_idL2qs_1ES")               │
│   ├─ description: str                                        │
│   ├─ generated_at: datetime                                  │
│   └─ seed: int                                               │
│                                                              │
│ truck_count: int  (2 or 3)                                  │
│ scenario_duration_s: float                                   │
│ velocity_type: VelocityType  (exactly 1)                    │
│ gap_type: GapType  (exactly 1)                              │
│ initial_gaps: List[float]  (len == truck_count - 1)         │
│                                                              │
│ velocity_events: List[VelocityEvent]                        │
│ loss_resume_pairs: List[LossResumePair]                     │
│   ├─ loss_event: IdentificationLossEvent  (is_loss=True)    │
│   └─ resume_event: IdentificationLossEvent  (is_loss=False) │
│ fort_event: Optional[FORTEvent]  (must be last if present)  │
└─────────────────────────────────────────────────────────────┘
```

### Enums (implemented in models.py)

| Enum | Values | CSV codes |
|------|--------|-----------|
| VelocityType | NOMINAL, MEDIUM_VARIABLE, HIGH_VARIABLE, HARD_BRAKE | nV, mV, hV, hB |
| GapType | SMALL, MEDIUM, BIG, VARIANT | sG, mG, bG, vG |
| LossType | QUICK_SHORT (~15 s), SLOW (~60 s), FREQUENT_VARIANT (mixed) | qs, sl, fv |

### ScenarioConfig (user input)

```python
ScenarioConfig(
    scenario_duration_s: float,      # seconds
    max_events: int,                 # max loss events (FORT is additional)
    min_event_separation_s: float,   # seconds between any two events
    num_scenarios: int,
    # selected_categories: not yet implemented (REQ P5 / G1)
)
```

---

## Module responsibilities

| Module | Responsibility | Must not |
|--------|----------------|----------|
| `models.py` | Data classes and enums | Contain logic |
| `events.py` | Velocity profile generation; create_loss_resume_pair | Know about CSV |
| `naming.py` | Name encode/decode; round-trip | Know about generation |
| `validation.py` | Stateless constraint checks; raises ValueError | Modify data |
| `csv_writer.py` | Scenario → CSV text/files | Generate or validate scenarios |
| `generator.py` | Orchestration: select, compose, timestamp, validate | Write files directly |
| `gui.py` | Tkinter UI | Contain generation or CSV logic |
| `__main__.py` | CLI argument parsing; call generator + csv_writer | Contain business logic |

---

## Generation pipeline

```
Phase 1: Random Selection
  ├─ truck_count ← random.choice([2, 3])
  ├─ velocity_type ← random.choice(VelocityType)
  ├─ gap_type ← random.choice(GapType)
  ├─ num_loss_events ← random.randint(0, max_events)
  ├─ shared_loss_type ← random.choice(LossType)  [one type per scenario]
  └─ has_fort ← random.choice([True, False]) if num_loss_events > 0

Phase 2: Event Composition
  ├─ VelocityProfile → velocity_events
  ├─ initial_gaps from gap_type
  └─ loss_resume_pairs (placeholder timestamp 0.0, assigned in Phase 3)

Phase 3: Timestamp Assignment  [_assign_timestamps()]
  ├─ Filter velocity events for min_event_separation
  ├─ If FORT planned: clear tail velocity events until room exists
  ├─ Greedily assign loss/resume timestamps (10 retries per pair)
  ├─ Assign FORT timestamp (must follow all others + min_sep)
  └─ Return 4-tuple: (velocity_events, pairs, fort_event, actual_loss_types)
     (pairs or FORT silently dropped if no valid slot)

Phase 4: Naming  [from actual placed events, not planned]
  └─ ScenarioNameEncoder.generate_name(truck_count, velocity_type, gap_type,
                                        actual_loss_types, actual_has_fort)
     → "3T_hV_mG_idL2qs_1ES"

Phase 5: Validation
  └─ ScenarioValidator.validate_all()  — raises ValueError on violation

Phase 6: CSV Output
  └─ CSVWriter.write_scenario_file()
     → Scene_Gen/{ddmmyyyy_hhmm}/{name}.csv
```

---

## Key algorithms

### Greedy timestamp assignment (`_assign_timestamps` in generator.py)

```
1. Filter velocity events:
   - Always keep first and last
   - Keep middle events only if time_since_last >= min_sep

2. FORT tail-clearing (if FORT planned):
   - Remove velocity events from tail until last_vel_time + min_sep <= duration
   - Edge case: if single event remains and blocks FORT, shift it back

3. Loss/resume pairs (per pair, up to 10 retries):
   - min_loss_time = min_sep
   - max_loss_time = duration - pair.duration - min_sep
   - Sample loss_t uniformly in [min_loss_time, max_loss_time]
   - resume_t = loss_t + pair.duration
   - Reject if any |loss_t - assigned_t| < min_sep or |resume_t - assigned_t| < min_sep
   - Drop pair silently if no slot found in 10 retries

4. FORT:
   - min_fort_time = max(all_assigned_times) + min_sep
   - Sample fort_t uniformly in [min_fort_time, duration]
   - Drop FORT silently if min_fort_time > duration

5. Return (filtered_velocity_events, placed_pairs, fort_or_None, actual_loss_types)
   — name is generated from actual_loss_types, not the planned list
```

### Velocity profile generation (`events.py`)

| Type | Algorithm |
|------|-----------|
| NOMINAL | Two points: (0, nominal_kph) and (duration, nominal_kph) |
| MEDIUM_VARIABLE | 8–12 sample points; random walk ±5% per step; clamped to [0.8×nominal, 1.2×nominal] |
| HIGH_VARIABLE | 6–10 sample points; each sampled uniformly from [min_kph, max_kph] |
| HARD_BRAKE | Nominal → brake at random time → recover; sharp deceleration shape |

### Scenario naming

```
Format:  {N}T_{vel}_{gap}_{idLoss}_{fort}ES
Example: 3T_hV_mG_idL2qs_1ES

Components:
  {N}T    truck count:       2T or 3T
  {vel}   velocity type:     nV mV hV hB
  {gap}   gap type:          sG mG bG vG
  {idLoss} loss events:      none  OR  idL{count}{type}
            count = number of pairs placed
            type  = qs sl fv  (one shared type per scenario)
  {fort}ES  FORT flag:       0ES or 1ES

Max length: 30 characters (enforced by ScenarioNameEncoder)
Round-trip: ScenarioNameParser.parse_name() → original attributes
```

---

## CSV output format

```
Row 0:  Description: {human-readable description}
Row 1:  Initial gaps:,{gap1},{gap2},,,       ← one value per column
Row 2:  Time_s,Truck1_Velocity_kph,Truck1_Event,Truck2_Image_Event,Truck3_Image_Event,Notes
Row 3+: {timestamp},{velocity or blank},{T1 event or blank},{T2 event or blank},{T3 event or blank},{notes}
```

Event encoding in CSV:
- Velocity event → Truck1_Velocity_kph filled; other event columns blank
- Loss event (truck 2) → Truck2_Image_Event = "Loss"
- Resume event (truck 2) → Truck2_Image_Event = "Resume"
- Loss/Resume (truck 3) → Truck3_Image_Event column
- FORT → Truck1_Event = "FORT activated"

All rows sorted by Time_s ascending.

---

## Constraints enforced (validation.py)

| # | Constraint | Check |
|---|-----------|-------|
| 1 | Truck count is 2 or 3 | validate_truck_count |
| 2 | initial_gaps length == truck_count − 1 | validate_initial_gaps |
| 3 | All timestamps ∈ [0, scenario_duration_s] | validate_timestamps_in_range |
| 4 | Events in chronological order | validate_timestamps_ordered |
| 5 | Consecutive events ≥ min_event_separation_s apart | validate_event_separation |
| 6 | loss_time < resume_time for all pairs | validate_loss_resume_pairing |
| 7 | Loss/resume events only on trucks 2 and 3 | validate_loss_resume_trucks |
| 8 | At most 1 FORT event | validate_fort_count |
| 9 | FORT (if present) is the last event | validate_fort_placement |

---

## Extensibility

### Add a new loss type
1. Add to `LossType` enum in `models.py`
2. Add duration mapping in `create_loss_resume_pair()` in `events.py`
3. Add entry to `LOSS_CODES` dict in `naming.py`
4. The new type appears automatically in random selection

### Add a new velocity type
1. Add to `VelocityType` enum in `models.py`
2. Add `generate_*()` method to `VelocityProfile` in `events.py`
3. Add case to `_compose_scenario()` in `generator.py`

### Add a custom validation rule
1. Add method to `ScenarioValidator` in `validation.py`
2. Register in `validate_all()` checks list
3. Raise `ValueError` with descriptive message on violation

---

## Test file map

| Test file | What it tests | Count |
|-----------|---------------|-------|
| `test_csv_output.py` | CSV formatting, file I/O, round-trip | 28 |
| `test_naming.py` | Name encoding/decoding for all combinations | 36 |
| `test_events.py` | VelocityProfile methods, create_loss_resume_pair | 15 |
| `test_generator_events.py` | _assign_timestamps, scenario composition | 20 |
| `test_scenario_composition.py` | Constraint satisfaction, reproducibility | 11 |
| `test_integration.py` | End-to-end pipeline, performance, error handling | 20 |
| **Total** | | **130** |

Run all: `python -m unittest discover tests -v`
