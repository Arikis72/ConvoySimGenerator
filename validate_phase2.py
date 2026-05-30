#!/usr/bin/env python
"""
validate_phase2.py — Manual validation of Phase 2 implementation

Runs key functionality tests without pytest dependency.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import ScenarioConfig, VelocityType, LossType
from events import VelocityProfile, create_loss_resume_pair, create_fort_event
from generator import ScenarioGenerator
from csv_writer import CSVWriter
from validation import ScenarioValidator


def test_velocity_profiles():
    """Test velocity profile generation."""
    print("\n=== Testing Velocity Profiles ===")

    # Test NOMINAL
    profile = VelocityProfile(VelocityType.NOMINAL, 120.0)
    profile.generate_nominal(nominal_kph=60.0)
    assert len(profile.points) == 2, f"Nominal should have 2 points, got {len(profile.points)}"
    assert profile.points[0][1] == 60.0, "Nominal velocity should be 60 kph"
    print("[OK] Nominal profile works")

    # Test MEDIUM_VARIABLE
    profile = VelocityProfile(VelocityType.MEDIUM_VARIABLE, 120.0)
    profile.generate_medium_variable(nominal_kph=60.0)
    assert 8 <= len(profile.points) <= 12, f"Medium should have 8-12 points, got {len(profile.points)}"
    for t, v in profile.points:
        assert 48.0 <= v <= 72.0, f"Medium velocity {v} out of range [48, 72]"
    print(f"[OK] Medium variable profile works ({len(profile.points)} points)")

    # Test HIGH_VARIABLE
    profile = VelocityProfile(VelocityType.HIGH_VARIABLE, 120.0)
    profile.generate_high_variable(min_kph=40.0, max_kph=80.0)
    assert 6 <= len(profile.points) <= 10, f"High should have 6-10 points, got {len(profile.points)}"
    for t, v in profile.points:
        assert 40.0 <= v <= 80.0, f"High velocity {v} out of range [40, 80]"
    print(f"[OK] High variable profile works ({len(profile.points)} points)")

    # Test HARD_BRAKE
    profile = VelocityProfile(VelocityType.HARD_BRAKE, 120.0)
    profile.generate_hard_brake(nominal_kph=60.0, brake_time_s=60.0)
    assert len(profile.points) == 4, f"Hard brake should have 4 points, got {len(profile.points)}"
    assert profile.points[0][1] == 60.0, "Hard brake should start at nominal"
    assert profile.points[2][1] == 20.0, "Hard brake should decelerate to 20 kph"
    print("[OK] Hard brake profile works")


def test_loss_resume_pairs():
    """Test loss/resume pair creation."""
    print("\n=== Testing Loss/Resume Pairs ===")

    # Test QUICK_SHORT
    pair = create_loss_resume_pair(truck_id=2, loss_timestamp_s=30.0, loss_type=LossType.QUICK_SHORT)
    assert pair.loss_event.duration_s == 15.0, f"Quick short should be 15s, got {pair.loss_event.duration_s}"
    assert pair.resume_event.timestamp_s == 45.0, f"Resume should be at 45s, got {pair.resume_event.timestamp_s}"
    print("[OK] Quick short loss/resume pair works")

    # Test SLOW
    pair = create_loss_resume_pair(truck_id=3, loss_timestamp_s=20.0, loss_type=LossType.SLOW)
    assert pair.loss_event.duration_s == 60.0, f"Slow should be 60s, got {pair.loss_event.duration_s}"
    assert pair.resume_event.timestamp_s == 80.0, f"Resume should be at 80s, got {pair.resume_event.timestamp_s}"
    print("[OK] Slow loss/resume pair works")

    # Test FORT
    fort = create_fort_event(timestamp_s=100.0)
    assert fort.timestamp_s == 100.0, f"FORT timestamp should be 100, got {fort.timestamp_s}"
    assert fort.truck_id == 1, f"FORT should affect truck 1, got {fort.truck_id}"
    print("[OK] FORT event creation works")


def test_scenario_generation():
    """Test complete scenario generation."""
    print("\n=== Testing Scenario Generation ===")

    config = ScenarioConfig(
        scenario_duration_s=120.0,
        max_events=4,
        min_event_separation_s=5.0,
        num_scenarios=10,
    )

    gen = ScenarioGenerator(config, seed=42)
    scenarios = gen.generate_all()

    assert len(scenarios) == 10, f"Should generate 10 scenarios, got {len(scenarios)}"
    print(f"[OK] Generated {len(scenarios)} scenarios")

    # Validate each scenario
    for i, scenario in enumerate(scenarios):
        # Check basic properties
        assert scenario.truck_count in [2, 3], f"Invalid truck count: {scenario.truck_count}"
        assert 0 < len(scenario.metadata.name) <= 30, f"Invalid name length: {len(scenario.metadata.name)}"

        # Validate timestamps
        try:
            ScenarioValidator.validate_all(scenario, config.min_event_separation_s)
        except ValueError as e:
            print(f"[FAIL] Scenario {i} validation failed: {e}")
            return False

    print(f"[OK] All {len(scenarios)} scenarios passed validation")

    # Test CSV output
    csv_text = CSVWriter.scenario_to_csv_text(scenarios[0])
    lines = csv_text.split("\n")
    assert lines[0].startswith("Description:"), "First line should be description"
    assert lines[1].startswith("Initial gaps:"), "Second line should be gaps"
    assert "Time_s" in lines[2], "Third line should be header"
    print("[OK] CSV output format is correct")

    # Test reproducibility
    gen2 = ScenarioGenerator(config, seed=42)
    scenarios2 = gen2.generate_all()
    for s1, s2 in zip(scenarios, scenarios2):
        assert s1.metadata.name == s2.metadata.name, f"Same seed should produce same names"
    print("[OK] Reproducibility verified (same seed = same scenarios)")

    return True


def test_timestamp_assignment():
    """Test timestamp assignment with constraints."""
    print("\n=== Testing Timestamp Assignment ===")

    config = ScenarioConfig(
        scenario_duration_s=120.0,
        max_events=4,
        min_event_separation_s=5.0,
        num_scenarios=20,
    )

    gen = ScenarioGenerator(config, seed=123)

    # Generate multiple scenarios and check timestamp properties
    for i in range(20):
        scenario = gen._compose_scenario()

        # Get all events
        events = scenario.get_all_events()

        # Check chronological order
        for j in range(1, len(events)):
            if events[j].timestamp_s < events[j - 1].timestamp_s:
                print(f"[FAIL] Events out of order at scenario {i}")
                return False

        # Check all within bounds
        for event in events:
            if not (0 <= event.timestamp_s <= config.scenario_duration_s):
                print(f"[FAIL] Event timestamp {event.timestamp_s} out of bounds at scenario {i}")
                return False

    print(f"[OK] Timestamp assignment works (20 scenarios tested)")

    return True


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("Phase 2: Event Generation - Validation")
    print("=" * 60)

    try:
        test_velocity_profiles()
        test_loss_resume_pairs()
        success = test_scenario_generation()
        if not success:
            return 1
        success = test_timestamp_assignment()
        if not success:
            return 1

        print("\n" + "=" * 60)
        print("[OK] ALL VALIDATION TESTS PASSED")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n[FAIL] Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
