"""
test_scenario_composition.py — Integration tests for scenario generation

Tests end-to-end scenario generation, CSV output, and reproducibility.
"""

import unittest
import os
import tempfile
from models import ScenarioConfig, VelocityEvent
from generator import ScenarioGenerator
from csv_writer import CSVWriter
from validation import ScenarioValidator


class TestEndToEndGeneration(unittest.TestCase):
    """Integration tests for complete scenario generation."""

    def test_generate_scenarios_end_to_end(self):
        """Generate scenarios and verify they are valid."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=5,
            min_event_separation_s=5.0,
            num_scenarios=20,
        )
        gen = ScenarioGenerator(config, seed=555)

        scenarios = gen.generate_all()

        self.assertEqual(len(scenarios), 20)

        # Verify each scenario is valid
        for scenario in scenarios:
            self.assertIsNotNone(scenario.metadata.name)
            self.assertIsNotNone(scenario.metadata.description)

            # Should pass all validations
            ScenarioValidator.validate_all(scenario, config.min_event_separation_s)

    def test_scenario_names_are_valid(self):
        """Generated scenario names should be valid and unique."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=4,
            min_event_separation_s=5.0,
            num_scenarios=15,
        )
        gen = ScenarioGenerator(config, seed=666)

        scenarios = gen.generate_all()

        names = set()
        for scenario in scenarios:
            name = scenario.metadata.name

            # Name should be valid format (includes uppercase letters in velocity/gap codes)
            self.assertRegex(
                name,
                r"^[23]T_[a-zA-Z]{2}_[a-zA-Z]{2}_(idL\d+[a-z]+|none)_[01]ES$",
                f"Invalid name format: {name}",
            )

            # Name should be <= 30 chars
            self.assertLessEqual(len(name), 30)

            # Track names
            names.add(name)

        # Should have mostly different names
        # (very unlikely to get all duplicates)
        # With max_events=4 and tight budget, expect at least 8 unique names
        # (velocity profile + gap variations create diversity even without loss events)
        self.assertGreaterEqual(len(names), 8)

    def test_scenario_csv_output(self):
        """Generated scenarios should produce valid CSV output."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=3,
            min_event_separation_s=5.0,
            num_scenarios=5,
        )
        gen = ScenarioGenerator(config, seed=777)

        scenarios = gen.generate_all()

        for scenario in scenarios:
            csv_text = CSVWriter.scenario_to_csv_text(scenario)

            # Should have header line
            lines = csv_text.split("\n")
            self.assertGreater(len(lines), 3)

            # First line should be description
            self.assertTrue(lines[0].startswith("Description:"))

            # Second line should be gaps
            self.assertTrue(lines[1].startswith("Initial gaps:"))

            # Third line should be header
            self.assertIn("Time_s,Truck1_Velocity_kph", lines[2])

    def test_scenario_csv_timestamps_ordered(self):
        """CSV output should have timestamps in chronological order."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=4,
            min_event_separation_s=5.0,
            num_scenarios=10,
        )
        gen = ScenarioGenerator(config, seed=888)

        scenarios = gen.generate_all()

        for scenario in scenarios:
            rows = CSVWriter.scenario_to_csv_rows(scenario)

            # Extract timestamps
            timestamps = [row.time_s for row in rows]

            # Should be in order
            self.assertEqual(timestamps, sorted(timestamps))

            # All should be within scenario
            for t in timestamps:
                self.assertGreaterEqual(t, 0.0)
                self.assertLessEqual(t, config.scenario_duration_s)

    def test_fort_event_is_last(self):
        """FORT event (if present) should be last in CSV."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=5,
            min_event_separation_s=5.0,
            num_scenarios=20,
        )
        gen = ScenarioGenerator(config, seed=999)

        scenarios = gen.generate_all()

        for scenario in scenarios:
            if scenario.fort_event:
                rows = CSVWriter.scenario_to_csv_rows(scenario)

                # Last row should have FORT event
                last_row = rows[-1]
                self.assertEqual(last_row.truck1_event, "FORT activated")

    def test_scenario_file_write(self):
        """Scenarios should write to files correctly."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=3,
            min_event_separation_s=5.0,
            num_scenarios=3,
        )
        gen = ScenarioGenerator(config, seed=1111)

        scenarios = gen.generate_all()

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = CSVWriter.write_scenarios_batch(scenarios, tmpdir)

            self.assertEqual(len(paths), 3)

            # Verify files exist and have content
            for path in paths:
                self.assertTrue(os.path.exists(path))
                with open(path, "r") as f:
                    content = f.read()
                    self.assertGreater(len(content), 50)  # Should have content


class TestReproducibility(unittest.TestCase):
    """Test scenario reproducibility with seeds."""

    def test_same_seed_same_scenario(self):
        """Same seed should produce identical scenarios."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=3,
            min_event_separation_s=5.0,
            num_scenarios=5,
        )

        gen1 = ScenarioGenerator(config, seed=2222)
        scenarios1 = gen1.generate_all()

        gen2 = ScenarioGenerator(config, seed=2222)
        scenarios2 = gen2.generate_all()

        # Should have same names and structure
        for s1, s2 in zip(scenarios1, scenarios2):
            self.assertEqual(s1.metadata.name, s2.metadata.name)
            self.assertEqual(len(s1.velocity_events), len(s2.velocity_events))
            self.assertEqual(len(s1.loss_resume_pairs), len(s2.loss_resume_pairs))

            # CSV should be identical
            csv1 = CSVWriter.scenario_to_csv_text(s1)
            csv2 = CSVWriter.scenario_to_csv_text(s2)
            self.assertEqual(csv1, csv2)

    def test_different_seed_different_scenarios(self):
        """Different seeds should (usually) produce different scenarios."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=3,
            min_event_separation_s=5.0,
            num_scenarios=5,
        )

        gen1 = ScenarioGenerator(config, seed=3333)
        scenarios1 = gen1.generate_all()

        gen2 = ScenarioGenerator(config, seed=4444)
        scenarios2 = gen2.generate_all()

        # Collect all names
        names1 = [s.metadata.name for s in scenarios1]
        names2 = [s.metadata.name for s in scenarios2]

        # Should not be identical (very unlikely with different seeds)
        self.assertNotEqual(names1, names2)


class TestConstraintSatisfaction(unittest.TestCase):
    """Test that generated scenarios satisfy all constraints."""

    def test_min_event_separation(self):
        """Generated scenarios should respect min_event_separation."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=5,
            min_event_separation_s=10.0,  # 10 second minimum
            num_scenarios=10,
        )
        gen = ScenarioGenerator(config, seed=5555)

        scenarios = gen.generate_all()

        for scenario in scenarios:
            events = scenario.get_all_events()

            # Check separation between consecutive events.
            # Velocity waypoints are curve control points and may be intentionally
            # close (startup ramp, hard-brake pair) — skip consecutive velocity pairs.
            for i in range(1, len(events)):
                if isinstance(events[i - 1], VelocityEvent) and isinstance(events[i], VelocityEvent):
                    continue  # velocity waypoints exempt from min_sep
                sep = events[i].timestamp_s - events[i - 1].timestamp_s
                # Allow small tolerance for floating point
                self.assertGreaterEqual(
                    sep, config.min_event_separation_s - 0.1,
                    f"Event separation {sep} < {config.min_event_separation_s}"
                )

    def test_truck_count_valid(self):
        """All scenarios should have valid truck count (2 or 3)."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=3,
            min_event_separation_s=5.0,
            num_scenarios=10,
        )
        gen = ScenarioGenerator(config, seed=6666)

        scenarios = gen.generate_all()

        for scenario in scenarios:
            self.assertIn(scenario.truck_count, [2, 3])

    def test_event_count_within_limits(self):
        """Scenarios should have <= max_events events."""
        config = ScenarioConfig(
            scenario_duration_s=120.0,
            max_events=4,
            min_event_separation_s=5.0,
            num_scenarios=10,
        )
        gen = ScenarioGenerator(config, seed=7777)

        scenarios = gen.generate_all()

        for scenario in scenarios:
            # Count loss events (each pair is 2 events, but 1 logical event)
            loss_count = len(scenario.loss_resume_pairs)

            # Loss count must not exceed max_events.
            # FORT is an additional optional event beyond the loss budget and is
            # not counted against max_events (generator samples num_loss_events
            # from randint(0, max_events) then independently chooses has_fort).
            self.assertLessEqual(loss_count, config.max_events)


if __name__ == "__main__":
    unittest.main()
