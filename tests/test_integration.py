"""
test_integration.py — Full end-to-end integration tests

Tests complete scenario generation pipeline from configuration through CSV export.
"""

import unittest
import tempfile
import os
import time
from pathlib import Path

from models import (
    ScenarioConfig,
    VelocityType,
    GapType,
    LossType,
)
from generator import ScenarioGenerator
from validation import ScenarioValidator
from csv_writer import CSVWriter
from naming import ScenarioNameParser


class TestEndToEndGeneration(unittest.TestCase):
    """Test complete generation pipeline."""

    def setUp(self):
        """Create test configuration."""
        self.config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=4,
            min_event_separation_s=5.0,
            num_scenarios=5,
        )

    def test_generate_and_validate(self):
        """Test generation followed by validation."""
        gen = ScenarioGenerator(self.config, seed=42)
        scenarios = gen.generate_all()

        self.assertEqual(len(scenarios), 5)

        # Validate all scenarios
        for scenario in scenarios:
            ScenarioValidator.validate_all(scenario, self.config.min_event_separation_s)

    def test_generate_and_export_csv(self):
        """Test generation followed by CSV export."""
        gen = ScenarioGenerator(self.config, seed=42)
        scenarios = gen.generate_all()

        # Export to CSV
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = CSVWriter.write_scenarios_batch(scenarios, tmpdir)

            self.assertEqual(len(paths), 5)

            # Verify files exist and have content
            for path in paths:
                self.assertTrue(os.path.exists(path))
                self.assertGreater(os.path.getsize(path), 0)

                # Check content
                with open(path, "r") as f:
                    content = f.read()
                    self.assertIn("Description:", content)
                    self.assertIn("Initial gaps:", content)
                    self.assertIn("Time_s", content)

    def test_roundtrip_name_parsing(self):
        """Test that generated scenario names can be parsed back."""
        gen = ScenarioGenerator(self.config, seed=42)
        scenarios = gen.generate_all()

        for scenario in scenarios:
            name = scenario.metadata.name

            # Parse the name
            truck_count, velocity_type, gap_type, loss_types, has_fort = (
                ScenarioNameParser.parse_name(name)
            )

            # Verify it matches scenario attributes
            self.assertEqual(truck_count, scenario.truck_count)
            self.assertEqual(velocity_type, scenario.velocity_type)
            self.assertEqual(gap_type, scenario.gap_type)

    def test_reproducibility_with_seed(self):
        """Test that same seed produces identical scenarios."""
        gen1 = ScenarioGenerator(self.config, seed=42)
        scenarios1 = gen1.generate_all()

        gen2 = ScenarioGenerator(self.config, seed=42)
        scenarios2 = gen2.generate_all()

        # Should have same names
        names1 = [s.metadata.name for s in scenarios1]
        names2 = [s.metadata.name for s in scenarios2]

        self.assertEqual(names1, names2)

    def test_different_seeds_different_scenarios(self):
        """Test that different seeds produce different scenarios."""
        gen1 = ScenarioGenerator(self.config, seed=42)
        scenarios1 = gen1.generate_all()

        gen2 = ScenarioGenerator(self.config, seed=43)
        scenarios2 = gen2.generate_all()

        names1 = [s.metadata.name for s in scenarios1]
        names2 = [s.metadata.name for s in scenarios2]

        # Most scenarios should be different
        same_count = sum(1 for n1, n2 in zip(names1, names2) if n1 == n2)
        self.assertLess(same_count, len(names1))  # Not all the same

    def test_progress_callback(self):
        """Test that progress callback is invoked."""
        progress_calls = []

        def progress_callback(current, total):
            progress_calls.append((current, total))

        gen = ScenarioGenerator(self.config, progress_callback=progress_callback)
        scenarios = gen.generate_all()

        # Should have been called 5 times (once per scenario)
        self.assertEqual(len(progress_calls), 5)
        self.assertEqual(progress_calls[-1], (5, 5))  # Last call should be 5/5


class TestParameterVariations(unittest.TestCase):
    """Test generation with various parameter combinations."""

    def test_short_duration(self):
        """Test generation with short scenario duration."""
        config = ScenarioConfig(
            scenario_duration_s=30.0,
            max_events=3,   # minimum is 3 (NOMINAL startup ramp = 3 events)
            min_event_separation_s=5.0,
            num_scenarios=3,
        )

        gen = ScenarioGenerator(config, seed=42)
        scenarios = gen.generate_all()

        for scenario in scenarios:
            self.assertEqual(scenario.scenario_duration_s, 30.0)
            ScenarioValidator.validate_all(scenario, 5.0)

    def test_long_duration(self):
        """Test generation with long scenario duration."""
        config = ScenarioConfig(
            scenario_duration_s=300.0,
            max_events=10,
            min_event_separation_s=5.0,
            num_scenarios=3,
        )

        gen = ScenarioGenerator(config, seed=42)
        scenarios = gen.generate_all()

        for scenario in scenarios:
            self.assertEqual(scenario.scenario_duration_s, 300.0)
            ScenarioValidator.validate_all(scenario, 5.0)

    def test_no_event_separation_requirement(self):
        """Test generation with no minimum separation."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=5,
            min_event_separation_s=0.0,  # No separation required
            num_scenarios=3,
        )

        gen = ScenarioGenerator(config, seed=42)
        scenarios = gen.generate_all()

        for scenario in scenarios:
            ScenarioValidator.validate_all(scenario, 0.0)

    def test_strict_separation_requirement(self):
        """Test generation with strict separation requirement."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=3,
            min_event_separation_s=15.0,  # Strict separation
            num_scenarios=3,
        )

        gen = ScenarioGenerator(config, seed=42)
        scenarios = gen.generate_all()

        for scenario in scenarios:
            ScenarioValidator.validate_all(scenario, 15.0)

    def test_many_events(self):
        """Test generation allowing many events."""
        config = ScenarioConfig(
            scenario_duration_s=300.0,
            max_events=20,  # Many events possible
            min_event_separation_s=5.0,
            num_scenarios=2,
        )

        gen = ScenarioGenerator(config, seed=42)
        scenarios = gen.generate_all()

        self.assertEqual(len(scenarios), 2)

        for scenario in scenarios:
            event_count = len(scenario.get_all_events())
            # Should have some events
            self.assertGreater(event_count, 0)
            ScenarioValidator.validate_all(scenario, 5.0)

    def test_two_truck_scenario(self):
        """Test that 2-truck scenarios are generated."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=3,
            min_event_separation_s=5.0,
            num_scenarios=10,
        )

        gen = ScenarioGenerator(config, seed=42)
        scenarios = gen.generate_all()

        has_two_truck = any(s.truck_count == 2 for s in scenarios)
        self.assertTrue(has_two_truck, "No 2-truck scenarios generated")

    def test_three_truck_scenario(self):
        """Test that 3-truck scenarios are generated."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=3,
            min_event_separation_s=5.0,
            num_scenarios=10,
        )

        gen = ScenarioGenerator(config, seed=42)
        scenarios = gen.generate_all()

        has_three_truck = any(s.truck_count == 3 for s in scenarios)
        self.assertTrue(has_three_truck, "No 3-truck scenarios generated")


class TestConvoySIMCompatibility(unittest.TestCase):
    """Test compatibility with ConvoySIM Stage A format."""

    def test_csv_format_columns(self):
        """Test that CSV has correct columns for ConvoySIM."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=3,
            min_event_separation_s=5.0,
            num_scenarios=1,
        )

        gen = ScenarioGenerator(config, seed=42)
        scenarios = gen.generate_all()

        csv_text = CSVWriter.scenario_to_csv_text(scenarios[0])
        lines = csv_text.split("\n")

        # Check header row
        header = lines[2]
        expected_columns = [
            "Time_s",
            "Truck1_Velocity_kph",
            "Truck1_Event",
            "Truck2_Image_Event",
            "Truck3_Image_Event",
            "Notes",
        ]

        columns = header.split(",")
        self.assertEqual(columns, expected_columns)

    def test_csv_data_types(self):
        """Test that CSV data can be parsed as expected types."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=3,   # minimum is 3 (NOMINAL startup ramp = 3 events)
            min_event_separation_s=5.0,
            num_scenarios=1,
        )

        gen = ScenarioGenerator(config, seed=42)
        scenarios = gen.generate_all()

        csv_text = CSVWriter.scenario_to_csv_text(scenarios[0])
        lines = csv_text.split("\n")

        # Skip metadata rows (0, 1) and header (2)
        data_lines = lines[3:]

        for line in data_lines:
            if not line.strip():
                continue

            parts = line.split(",")
            self.assertEqual(len(parts), 6)

            # Time should be numeric
            try:
                float(parts[0])
            except ValueError:
                self.fail(f"Time value not numeric: {parts[0]}")

            # Velocity (if present) should be numeric
            if parts[1]:
                try:
                    float(parts[1])
                except ValueError:
                    self.fail(f"Velocity not numeric: {parts[1]}")

    def test_csv_initial_gaps_format(self):
        """Test that initial gaps are formatted correctly.

        Expected row format: Initial gaps:,{gap1},{gap2},,,
        Label in column 0; each gap in its own column; row has 6 fields total.
        """
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=3,   # minimum is 3 (NOMINAL startup ramp = 3 events)
            min_event_separation_s=5.0,
            num_scenarios=1,
        )

        gen = ScenarioGenerator(config, seed=42)
        scenarios = gen.generate_all()

        csv_text = CSVWriter.scenario_to_csv_text(scenarios[0])
        lines = csv_text.split("\n")

        gaps_line = lines[1]
        self.assertTrue(gaps_line.startswith("Initial gaps:"))

        # New format: comma-separated, label in col 0, gap values in col 1+
        parts = gaps_line.split(",")
        self.assertEqual(len(parts), 6, "Gaps row must have 6 comma-separated fields")
        self.assertEqual(parts[0], "Initial gaps:")

        # Extract non-empty gap fields (columns 1 onwards)
        gap_values = [p for p in parts[1:] if p.strip()]
        self.assertGreater(len(gap_values), 0, "At least one gap value expected")

        for gap in gap_values:
            try:
                float(gap)
            except ValueError:
                self.fail(f"Gap value not numeric: {gap!r}")

    def test_scenario_names_valid_for_filenames(self):
        """Test that scenario names are valid filenames."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=3,
            min_event_separation_s=5.0,
            num_scenarios=10,
        )

        gen = ScenarioGenerator(config, seed=42)
        scenarios = gen.generate_all()

        for scenario in scenarios:
            name = scenario.metadata.name

            # Should not contain invalid filename characters
            invalid_chars = r'<>:"|?*'
            for char in invalid_chars:
                self.assertNotIn(
                    char,
                    name,
                    f"Invalid filename character '{char}' in: {name}",
                )

            # Should be reasonable length for filename
            self.assertLessEqual(len(name), 30)


class TestBulkGeneration(unittest.TestCase):
    """Test performance with bulk scenario generation."""

    def test_bulk_generation_speed(self):
        """Test that bulk generation completes in reasonable time."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=4,
            min_event_separation_s=5.0,
            num_scenarios=50,  # Bulk generation
        )

        start_time = time.time()
        gen = ScenarioGenerator(config, seed=42)
        scenarios = gen.generate_all()
        elapsed = time.time() - start_time

        self.assertEqual(len(scenarios), 50)

        # Should generate 50 scenarios in reasonable time (< 5 seconds)
        self.assertLess(elapsed, 5.0, f"Generation too slow: {elapsed:.2f}s for 50 scenarios")

    def test_bulk_export_speed(self):
        """Test that bulk CSV export completes in reasonable time."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=3,
            min_event_separation_s=5.0,
            num_scenarios=50,
        )

        gen = ScenarioGenerator(config, seed=42)
        scenarios = gen.generate_all()

        with tempfile.TemporaryDirectory() as tmpdir:
            start_time = time.time()
            paths = CSVWriter.write_scenarios_batch(scenarios, tmpdir)
            elapsed = time.time() - start_time

            self.assertEqual(len(paths), 50)

            # Should export 50 files in reasonable time (< 2 seconds)
            self.assertLess(
                elapsed, 2.0, f"Export too slow: {elapsed:.2f}s for 50 files"
            )

    def test_bulk_validation_speed(self):
        """Test that bulk validation completes quickly."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=3,
            min_event_separation_s=5.0,
            num_scenarios=50,
        )

        gen = ScenarioGenerator(config, seed=42)
        scenarios = gen.generate_all()

        start_time = time.time()
        for scenario in scenarios:
            ScenarioValidator.validate_all(scenario, 5.0)
        elapsed = time.time() - start_time

        # Should validate 50 scenarios in < 1 second
        self.assertLess(elapsed, 1.0, f"Validation too slow: {elapsed:.2f}s")


class TestErrorHandling(unittest.TestCase):
    """Test error handling in generation pipeline."""

    def test_invalid_config_duration(self):
        """Test that invalid duration is caught."""
        with self.assertRaises(ValueError):
            config = ScenarioConfig(
                scenario_duration_s=-10.0,  # Invalid
                max_events=3,
                min_event_separation_s=5.0,
                num_scenarios=1,
            )
            config.validate()

    def test_invalid_config_max_events(self):
        """Test that invalid max_events is caught."""
        with self.assertRaises(ValueError):
            config = ScenarioConfig(
                scenario_duration_s=120.0,
                max_events=0,  # Invalid
                min_event_separation_s=5.0,
                num_scenarios=1,
            )
            config.validate()

    def test_impossible_separation_constraint(self):
        """Test handling when min_event_separation exceeds scenario duration.

        With min_sep=100 s and duration=30 s no loss/resume pair can ever fit
        (min_loss_time=100 > max_loss_time<0). The generator deals with this
        gracefully: it drops every loss/FORT event that cannot be placed so the
        resulting scenario is velocity-only and still passes validation.

        If all retry attempts happen to land on configurations where two velocity
        events end up too close (separation 30 < 100), a RuntimeError may still
        be raised — both outcomes are acceptable.
        """
        config = ScenarioConfig(
            scenario_duration_s=30.0,
            max_events=5,
            min_event_separation_s=100.0,
            num_scenarios=1,
        )

        gen = ScenarioGenerator(config, seed=42)

        try:
            scenarios = gen.generate_all()
            # If generation succeeded, all loss/FORT events must have been dropped
            # (they can never fit within the tiny duration with a 100 s separation).
            self.assertEqual(len(scenarios), 1)
            scenario = scenarios[0]
            self.assertEqual(
                len(scenario.loss_resume_pairs),
                0,
                "No loss pairs should fit with min_sep > duration",
            )
            self.assertIsNone(
                scenario.fort_event,
                "FORT should not fit with min_sep > duration",
            )
        except RuntimeError:
            # Also acceptable: all retries failed because velocity events at
            # t=0 and t=30 violated the 100 s separation requirement.
            pass


class TestAPIConsistency(unittest.TestCase):
    """Test API consistency across different usage patterns."""

    def test_generator_instance_independence(self):
        """Test that different generator instances produce valid scenarios."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=3,
            min_event_separation_s=5.0,
            num_scenarios=3,
        )

        gen1 = ScenarioGenerator(config, seed=42)
        gen2 = ScenarioGenerator(config, seed=42)

        scenarios1 = gen1.generate_all()
        scenarios2 = gen2.generate_all()

        # Both should produce valid scenarios
        self.assertEqual(len(scenarios1), 3)
        self.assertEqual(len(scenarios2), 3)

        for scenario in scenarios1 + scenarios2:
            ScenarioValidator.validate_all(scenario, 5.0)

    def test_scenario_immutability(self):
        """Test that generated scenarios maintain their attributes."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=3,   # minimum is 3 (NOMINAL startup ramp = 3 events)
            min_event_separation_s=5.0,
            num_scenarios=2,
        )

        gen = ScenarioGenerator(config, seed=42)
        scenarios = gen.generate_all()

        # Record initial state
        names = [s.metadata.name for s in scenarios]
        truck_counts = [s.truck_count for s in scenarios]

        # Create CSV and validate
        CSVWriter.scenario_to_csv_text(scenarios[0])
        ScenarioValidator.validate_all(scenarios[0], 5.0)

        # Attributes should be unchanged
        self.assertEqual(names, [s.metadata.name for s in scenarios])
        self.assertEqual(truck_counts, [s.truck_count for s in scenarios])


if __name__ == "__main__":
    unittest.main()
