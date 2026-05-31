---
title: SimGenerator — Convoy Scenario Generation System
type: readme
date: 2026-05-30
description: SimGenerator generates randomised, constraint-satisfying convoy scenarios for ConvoySIM Stage A testing. Pure Python 3.9+ stdlib.
tags: [simgenerator, readme]
related: ["[[AGENTS]]", "[[REQUIREMENTS]]", "[[STATUS]]"]
---

# SimGenerator — Convoy Scenario Generation System

**Repository:** https://github.com/Arikis72/ConvoySimGenerator

A Python tool that generates randomised convoy scenarios for ConvoySIM testing.
Produces realistic, constraint-satisfying scenarios and exports them to
ConvoySIM Stage A CSV format.

**No external dependencies — pure Python 3.9+ standard library.**

---

## Quick start (5 minutes)

### Requirements
- Python 3.9+
- Tkinter (verify with `python -m tkinter` — a window should appear)

### GUI (recommended)

```bash
python gui.py
```

The GUI has two tabs:

**Generate tab**
1. Set parameters (duration, max events, separation, count, seed).
2. Set the **Output Root Folder** (or leave blank to use `Scene_Gen/` in the
   current directory). Each run automatically creates a `ddmmyyyy_hhmm`
   subfolder inside it.
3. Click **Generate Scenarios**.
4. Watch the progress bar and log.

**Scenarios tab**
- Left panel: list of generated scenarios.
- Right panel: scenario details (name, truck count, velocity type, events).
- Bottom panel: editable CSV table — double-click any cell to edit, then
  Save or Save As.

### Command line

```bash
python -m simgenerator --count 10 --duration 120 --max-events 5 --min-sep 5
```

Scenarios are written to `Scene_Gen/{ddmmyyyy_hhmm}/` by default.
Use `--output /path/to/root` to change the root; the timestamp subfolder
is always appended automatically.

### Programmatic API

```python
from models import ScenarioConfig
from generator import ScenarioGenerator
from csv_writer import CSVWriter

config = ScenarioConfig(
    scenario_duration_s=120.0,
    max_events=5,
    min_event_separation_s=5.0,
    num_scenarios=10,
)

gen = ScenarioGenerator(config, seed=42)   # seed optional; omit for random
scenarios = gen.generate_all()

CSVWriter.write_scenarios_batch(scenarios, "Scene_Gen/my_run")
```

---

## Scenario types

### Velocity profiles (exactly 1 per scenario)

| Code | Name | Behaviour |
|------|------|-----------|
| `nV` | Nominal | Constant speed |
| `mV` | Medium Variable | ±10% random walk; 8–12 sample points |
| `hV` | High Variable | Random jumps across full range; 6–10 sample points |
| `hB` | Hard Brake | Nominal → sharp deceleration at random time |

### Gap types (exactly 1 per scenario)

| Code | Name | Gap value |
|------|------|-----------|
| `sG` | Small | 5 m |
| `mG` | Medium | 10 m |
| `bG` | Big | 20 m |
| `vG` | Variant | 5 m + 20 m (or reversed) |

### Identification loss events (0 to max_events per scenario)

- Truck 2 or Truck 3 loses and later recovers identification.
- **Quick-Short (`qs`)**: ~15 s duration.
- **Slow (`sl`)**: ~60 s duration.
- **Frequent Variant (`fv`)**: mixed 15–60 s duration.
- All loss/resume pairs in one scenario share the same type.

### FORT event (0 or 1, always last)

Emergency stop by the leader (Truck 1). Must be the final event in the
scenario. Present only when at least one loss event was also generated.

---

## Scenario naming

```
{N}T_{vel}_{gap}_{idLoss}_{fort}ES
```

| Component | Examples |
|-----------|---------|
| Truck count | `2T`, `3T` |
| Velocity | `nV`, `mV`, `hV`, `hB` |
| Gap | `sG`, `mG`, `bG`, `vG` |
| ID losses | `none` or `idL{count}{type}` e.g. `idL2qs` |
| FORT | `0ES` (no), `1ES` (yes) |

**Max 30 characters.** Round-trip: name → attributes via `ScenarioNameParser`.

Examples:
- `2T_nV_sG_none_0ES` — 2 trucks, nominal, small gaps, no losses, no FORT
- `3T_hV_mG_idL2qs_1ES` — 3 trucks, high variable, medium gaps, 2 quick-short losses, FORT

---

## CSV output format

```csv
Description: 3 trucks, high variable velocity, medium gaps, 2 QUICK_SHORT ID losses, 1 FORT event
Initial gaps:,10,10,,,
Time_s,Truck1_Velocity_kph,Truck1_Event,Truck2_Image_Event,Truck3_Image_Event,Notes
0.0,60.0,,,,Velocity profile start
14.3,72.1,,,,
31.8,,,"Loss",,Quick-short loss begins
46.8,,,"Resume",,
...
118.4,,"FORT activated",,,Emergency stop
```

- **Row 0**: Human-readable description (ConvoySIM ignores this row).
- **Row 1**: Initial gaps — label in column 0, each gap value in its own column.
- **Row 2**: Column headers.
- **Row 3+**: Events sorted by `Time_s` ascending.

---

## API reference

### ScenarioConfig

```python
ScenarioConfig(
    scenario_duration_s=120.0,     # Total duration in seconds
    max_events=5,                   # Maximum loss events per scenario
    min_event_separation_s=5.0,     # Minimum seconds between any two events
    num_scenarios=10,               # How many scenarios to generate
)
```

### ScenarioGenerator

```python
gen = ScenarioGenerator(
    config=config,
    seed=42,                                              # Optional; None = random
    progress_callback=lambda current, total: ...,         # Optional
)
scenarios = gen.generate_all()   # Returns List[Scenario]
```

### CSVWriter

```python
# Single scenario to string
csv_text = CSVWriter.scenario_to_csv_text(scenario)

# Write single file
CSVWriter.write_scenario_file(scenario, "path/to/file.csv")

# Write all scenarios
paths = CSVWriter.write_scenarios_batch(scenarios, "output_folder")
```

### ScenarioValidator

```python
from validation import ScenarioValidator

try:
    ScenarioValidator.validate_all(scenario, min_event_separation_s=5.0)
except ValueError as e:
    print(f"Invalid: {e}")
```

### ScenarioNameParser

```python
from naming import ScenarioNameParser

truck_count, velocity_type, gap_type, loss_types, has_fort = (
    ScenarioNameParser.parse_name("3T_hV_mG_idL2qs_1ES")
)
```

---

## Running tests

```bash
python -m unittest discover tests -v
```

**130 tests, all passing.**

| Test file | Count | Covers |
|-----------|-------|--------|
| `test_csv_output.py` | 28 | CSV formatting, file I/O, round-trip |
| `test_naming.py` | 36 | Name encoding/decoding, all combinations |
| `test_events.py` | 15 | Velocity profiles, loss/resume creation |
| `test_generator_events.py` | 20 | Timestamp assignment, composition |
| `test_scenario_composition.py` | 11 | Constraints, reproducibility |
| `test_integration.py` | 20 | End-to-end pipeline, performance |

---

## Performance

| Operation | 50 scenarios | Rate |
|-----------|-------------|------|
| Generation | 0.15 s | 333/sec |
| CSV export | 0.08 s | 625 files/sec |
| Validation | 0.03 s | 1 667/sec |

All targets exceeded by 25–33×.

---

## Configuration guide

| Parameter | Default | Practical range | Effect |
|-----------|---------|----------------|--------|
| `scenario_duration_s` | 120 | 30–300 | Window for event placement |
| `max_events` | 5 | 1–20 | Max loss pairs (actual may be fewer) |
| `min_event_separation_s` | 5.0 | 0–30 | Tighter = fewer events placed |
| `num_scenarios` | 10 | 1–1000+ | Linear time scaling |
| `seed` | None | Any integer | Same seed → identical scenarios |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `RuntimeError: Failed to generate after retries` | Impossible constraints | Increase duration; decrease max_events or min_sep |
| `ValueError: Validation failed` | Generator bug | Check seed and parameters; report with seed value |
| GUI won't open | Tkinter missing or headless | `python -m tkinter`; use CLI instead |
| Scenarios land in wrong folder | Old code before 2026-05-29 fix | Update — timestamp subfolder now always appended |

---

## Project structure

```
SimGenerator/
├── gui.py              # Tkinter GUI (2-tab: Generate + Scenarios)
├── models.py           # Data classes and enums
├── events.py           # Event generation and velocity profiles
├── generator.py        # Main scenario generation engine
├── validation.py       # Constraint validation (9 rules)
├── csv_writer.py       # CSV formatting and file I/O
├── naming.py           # Scenario name encode/decode
├── __main__.py         # CLI entry point
├── tests/
│   ├── test_csv_output.py
│   ├── test_naming.py
│   ├── test_events.py
│   ├── test_generator_events.py
│   ├── test_scenario_composition.py
│   └── test_integration.py
├── CLAUDE.md           # Claude working instructions
├── README.md           # This file
├── STATUS.md           # Current project state
├── progress.md         # Session log
├── decisions.md        # Design decisions
├── REQUIREMENTS.md     # Requirements spec + status table
├── TASKS.md            # Open tasks
└── PLANNING.md         # Architecture reference
```

---

## Documentation reading order

| Goal | Start here |
|------|-----------|
| Use the tool | This file (README.md) |
| Know what's done / open | STATUS.md |
| See session history | progress.md |
| Understand design choices | decisions.md |
| Check a specific requirement | REQUIREMENTS.md |
| See open tasks | TASKS.md |
| Understand algorithms | PLANNING.md |
| (Claude) Working instructions | CLAUDE.md |

---

## Version history

| Version | Date | Notes |
|---------|------|-------|
| 1.0 | 2026-05-28 | Initial 6-phase implementation (89 tests) |
| 1.1 | 2026-05-29 | GUI rewrite (2 tabs); bugs 10/11/12 fixed; req 2.2 fixed; 130 tests |
