"""
test_csv_output.py — CSV output formatting and file writing tests

Tests CSV row formatting, file I/O, and ConvoySIM compatibility.
"""

import unittest
import tempfile
import os
from pathlib import Path

from models import (
    Scenario,
    ScenarioMetadata,
    ScenarioConfig,
    CSVRow,
    VelocityEvent,
    IdentificationLossEvent,
    FORTEvent,
    LossResumePair,
    VelocityType,
    GapType,
    LossType,
)
from csv_writer import CSVWriter
from datetime import datetime


class TestCSVRowFormatting(unittest.TestCase):
    """Test CSVRow formatting to CSV line format."""

    def test_velocity_row_formatting(self):
        """Test formatting of velocity event row."""
        row = CSVRow(
            time_s=10.0,
            truck1_velocity_kph=60.0,
            truck1_event=None,
            truck2_image_event=None,
            truck3_image_event=None,
            notes="Test velocity",
        )

        csv_line = row.to_csv_row()

        # Check format: time,velocity,event,img2,img3,notes
        parts = csv_line.split(",")
        self.assertEqual(len(parts), 6)
        self.assertEqual(parts[0], "10")     # time (whole seconds, no decimals)
        self.assertEqual(parts[1], "60.00")  # velocity (2 decimal places)
        self.assertEqual(parts[2], "")      # truck1_event
        self.assertEqual(parts[3], "")      # truck2_image_event
        self.assertEqual(parts[4], "")      # truck3_image_event
        self.assertEqual(parts[5], "Test velocity")  # notes

    def test_loss_event_row_formatting(self):
        """Test formatting of identification loss event row."""
        row = CSVRow(
            time_s=25.0,
            truck1_velocity_kph=None,
            truck1_event=None,
            truck2_image_event="Loss",
            truck3_image_event=None,
            notes="ID Loss on truck 2",
        )

        csv_line = row.to_csv_row()

        parts = csv_line.split(",")
        self.assertEqual(len(parts), 6)
        self.assertEqual(parts[0], "25")  # time (whole seconds, no decimals)
        self.assertEqual(parts[1], "")      # No velocity
        self.assertEqual(parts[2], "")      # No truck1 event
        self.assertEqual(parts[3], "Loss")  # truck2 event
        self.assertEqual(parts[4], "")      # truck3 event
        self.assertEqual(parts[5], "ID Loss on truck 2")

    def test_resume_event_row_formatting(self):
        """Test formatting of identification resume event row."""
        row = CSVRow(
            time_s=40.0,
            truck1_velocity_kph=None,
            truck1_event=None,
            truck2_image_event=None,
            truck3_image_event="Resume",
            notes="ID Resume on truck 3",
        )

        csv_line = row.to_csv_row()

        parts = csv_line.split(",")
        self.assertEqual(parts[3], "")        # truck2 event
        self.assertEqual(parts[4], "Resume")  # truck3 event

    def test_fort_event_row_formatting(self):
        """Test formatting of FORT (emergency stop) event row."""
        row = CSVRow(
            time_s=110.0,
            truck1_velocity_kph=None,
            truck1_event="FORT activated",
            truck2_image_event=None,
            truck3_image_event=None,
            notes="Emergency stop",
        )

        csv_line = row.to_csv_row()

        parts = csv_line.split(",")
        self.assertEqual(parts[0], "110")  # time (whole seconds, no decimals)
        self.assertEqual(parts[2], "FORT activated")
        self.assertEqual(parts[5], "Emergency stop")

    def test_empty_row_formatting(self):
        """Test formatting of row with no events."""
        row = CSVRow(
            time_s=50.0,
            truck1_velocity_kph=None,
            truck1_event=None,
            truck2_image_event=None,
            truck3_image_event=None,
            notes="",
        )

        csv_line = row.to_csv_row()

        parts = csv_line.split(",")
        self.assertEqual(len(parts), 6)
        self.assertEqual(parts[0], "50")  # time (whole seconds, no decimals)
        # All other fields are empty
        for i in range(1, 6):
            self.assertEqual(parts[i], "")

    def test_velocity_with_fort_same_time(self):
        """Test row with both velocity and FORT at same timestamp (edge case)."""
        # Note: This shouldn't happen in normal scenarios, but test defensive handling
        row = CSVRow(
            time_s=120.0,
            truck1_velocity_kph=45.0,
            truck1_event="FORT activated",
            truck2_image_event=None,
            truck3_image_event=None,
            notes="Simultaneous events",
        )

        csv_line = row.to_csv_row()

        parts = csv_line.split(",")
        self.assertEqual(parts[1], "45.00")  # velocity (2 decimal places)
        self.assertEqual(parts[2], "FORT activated")


class TestCSVHeaderFormatting(unittest.TestCase):
    """Test header row formatting."""

    def test_header_row_format(self):
        """Test CSV header row matches expected format."""
        header = CSVWriter.format_header_row()

        expected = "Time_s,Truck1_Velocity_kph,Truck1_Event,Truck2_Image_Event,Truck3_Image_Event,Notes"
        self.assertEqual(header, expected)

    def test_header_columns_count(self):
        """Test header has exactly 6 columns."""
        header = CSVWriter.format_header_row()
        columns = header.split(",")
        self.assertEqual(len(columns), 6)
        self.assertEqual(columns[0], "Time_s")
        self.assertEqual(columns[1], "Truck1_Velocity_kph")
        self.assertEqual(columns[2], "Truck1_Event")
        self.assertEqual(columns[3], "Truck2_Image_Event")
        self.assertEqual(columns[4], "Truck3_Image_Event")
        self.assertEqual(columns[5], "Notes")


class TestCSVMetadataRows(unittest.TestCase):
    """Test metadata row formatting (description and initial gaps)."""

    def setUp(self):
        """Create a test scenario."""
        self.metadata = ScenarioMetadata(
            name="test_scenario",
            description="2 trucks, nominal velocity, small gaps",
            generated_at=datetime.now(),
            seed=42,
        )

        self.scenario = Scenario(
            metadata=self.metadata,
            truck_count=2,
            scenario_duration_s=120.0,
            velocity_type=VelocityType.NOMINAL,
            gap_type=GapType.SMALL,
            initial_gaps=[5.0],
            velocity_events=[],
            loss_resume_pairs=[],
            fort_event=None,
        )

    def test_description_row_format(self):
        """Test description row formatting."""
        desc_row = CSVWriter.format_description_row(self.scenario)

        self.assertTrue(desc_row.startswith("Description: "))
        self.assertIn("2 trucks", desc_row)
        self.assertIn("nominal velocity", desc_row)

    def test_initial_gaps_row_single_gap(self):
        """Test initial gaps row with 2 trucks (1 gap).

        Expected format: Initial gaps:,5,,,,
        Label in column 0, gap value in column 1, remaining columns empty.
        """
        gaps_row = CSVWriter.format_initial_gaps_row(self.scenario)

        # Label (no trailing space)
        self.assertTrue(gaps_row.startswith("Initial gaps:"))
        # Exactly 6 comma-separated fields
        parts = gaps_row.split(",")
        self.assertEqual(len(parts), 6)
        # First field is the label
        self.assertEqual(parts[0], "Initial gaps:")
        # Second field contains the gap value
        self.assertEqual(float(parts[1]), 5.0)
        # Remaining fields are empty
        for p in parts[2:]:
            self.assertEqual(p, "")

    def test_initial_gaps_row_multiple_gaps(self):
        """Test initial gaps row with 3 trucks (2 gaps).

        Expected format: Initial gaps:,5,20,,,
        """
        scenario = Scenario(
            metadata=self.metadata,
            truck_count=3,
            scenario_duration_s=120.0,
            velocity_type=VelocityType.NOMINAL,
            gap_type=GapType.VARIANT,
            initial_gaps=[5.0, 20.0],
            velocity_events=[],
            loss_resume_pairs=[],
            fort_event=None,
        )

        gaps_row = CSVWriter.format_initial_gaps_row(scenario)

        parts = gaps_row.split(",")
        self.assertEqual(len(parts), 6)
        self.assertEqual(parts[0], "Initial gaps:")
        self.assertEqual(float(parts[1]), 5.0)
        self.assertEqual(float(parts[2]), 20.0)
        # Remaining fields empty
        for p in parts[3:]:
            self.assertEqual(p, "")


class TestScenarioToCSVRows(unittest.TestCase):
    """Test conversion of scenarios to CSV rows."""

    def setUp(self):
        """Create a test scenario with various events."""
        self.metadata = ScenarioMetadata(
            name="test_scenario",
            description="Test scenario",
            generated_at=datetime.now(),
            seed=42,
        )

    def test_velocity_event_to_row(self):
        """Test conversion of velocity event to CSV row."""
        velocity_event = VelocityEvent(
            timestamp_s=10.0,
            truck_id=1,
            velocity_type=VelocityType.NOMINAL,
            velocity_kph=60.0,
            notes="Velocity change",
        )

        scenario = Scenario(
            metadata=self.metadata,
            truck_count=2,
            scenario_duration_s=120.0,
            velocity_type=VelocityType.NOMINAL,
            gap_type=GapType.SMALL,
            initial_gaps=[5.0],
            velocity_events=[velocity_event],
            loss_resume_pairs=[],
            fort_event=None,
        )

        rows = CSVWriter.scenario_to_csv_rows(scenario)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].time_s, 10.0)
        self.assertEqual(rows[0].truck1_velocity_kph, 60.0)
        self.assertIsNone(rows[0].truck1_event)

    def test_loss_resume_pair_to_rows(self):
        """Test conversion of loss/resume pair to CSV rows."""
        loss_event = IdentificationLossEvent(
            timestamp_s=30.0,
            truck_id=2,
            is_loss=True,
            loss_type=LossType.QUICK_SHORT,
            duration_s=15.0,
            notes="ID loss",
        )

        resume_event = IdentificationLossEvent(
            timestamp_s=45.0,
            truck_id=2,
            is_loss=False,
            notes="Resume",
        )

        pair = LossResumePair(loss_event, resume_event)

        scenario = Scenario(
            metadata=self.metadata,
            truck_count=2,
            scenario_duration_s=120.0,
            velocity_type=VelocityType.NOMINAL,
            gap_type=GapType.SMALL,
            initial_gaps=[5.0],
            velocity_events=[],
            loss_resume_pairs=[pair],
            fort_event=None,
        )

        rows = CSVWriter.scenario_to_csv_rows(scenario)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].time_s, 30.0)
        self.assertEqual(rows[0].truck2_image_event, "Loss")
        self.assertEqual(rows[1].time_s, 45.0)
        self.assertEqual(rows[1].truck2_image_event, "Resume")

    def test_fort_event_to_row(self):
        """Test conversion of FORT event to CSV row."""
        fort_event = FORTEvent(
            timestamp_s=110.0,
            truck_id=1,
            notes="Emergency stop",
        )

        scenario = Scenario(
            metadata=self.metadata,
            truck_count=2,
            scenario_duration_s=120.0,
            velocity_type=VelocityType.NOMINAL,
            gap_type=GapType.SMALL,
            initial_gaps=[5.0],
            velocity_events=[],
            loss_resume_pairs=[],
            fort_event=fort_event,
        )

        rows = CSVWriter.scenario_to_csv_rows(scenario)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].time_s, 110.0)
        self.assertEqual(rows[0].truck1_event, "FORT activated")

    def test_mixed_events_chronological_order(self):
        """Test that mixed event types are sorted chronologically."""
        # Create events in non-chronological order
        fort_event = FORTEvent(
            timestamp_s=110.0,
            truck_id=1,
            notes="FORT",
        )

        loss_event = IdentificationLossEvent(
            timestamp_s=30.0,
            truck_id=2,
            is_loss=True,
            loss_type=LossType.QUICK_SHORT,
            duration_s=15.0,
            notes="Loss",
        )

        resume_event = IdentificationLossEvent(
            timestamp_s=45.0,
            truck_id=2,
            is_loss=False,
            notes="Resume",
        )

        velocity_event = VelocityEvent(
            timestamp_s=10.0,
            truck_id=1,
            velocity_type=VelocityType.NOMINAL,
            velocity_kph=60.0,
            notes="Velocity",
        )

        scenario = Scenario(
            metadata=self.metadata,
            truck_count=2,
            scenario_duration_s=120.0,
            velocity_type=VelocityType.NOMINAL,
            gap_type=GapType.SMALL,
            initial_gaps=[5.0],
            velocity_events=[velocity_event],
            loss_resume_pairs=[LossResumePair(loss_event, resume_event)],
            fort_event=fort_event,
        )

        rows = CSVWriter.scenario_to_csv_rows(scenario)

        # Should be sorted: velocity (10) < loss (30) < resume (45) < fort (110)
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0].time_s, 10.0)
        self.assertEqual(rows[1].time_s, 30.0)
        self.assertEqual(rows[2].time_s, 45.0)
        self.assertEqual(rows[3].time_s, 110.0)


class TestScenarioToCSVText(unittest.TestCase):
    """Test complete CSV text generation."""

    def setUp(self):
        """Create a test scenario."""
        self.metadata = ScenarioMetadata(
            name="test_scenario",
            description="Test scenario with events",
            generated_at=datetime.now(),
            seed=42,
        )

        velocity_event = VelocityEvent(
            timestamp_s=10.0,
            truck_id=1,
            velocity_type=VelocityType.NOMINAL,
            velocity_kph=60.0,
            notes="Start",
        )

        self.scenario = Scenario(
            metadata=self.metadata,
            truck_count=2,
            scenario_duration_s=120.0,
            velocity_type=VelocityType.NOMINAL,
            gap_type=GapType.SMALL,
            initial_gaps=[5.0],
            velocity_events=[velocity_event],
            loss_resume_pairs=[],
            fort_event=None,
        )

    def test_csv_text_has_header_rows(self):
        """Test CSV text includes description, gaps, and header rows."""
        csv_text = CSVWriter.scenario_to_csv_text(self.scenario)

        lines = csv_text.split("\n")

        # At least 3 header lines + 1 data line
        self.assertGreaterEqual(len(lines), 4)

        self.assertTrue(lines[0].startswith("Description: "))
        self.assertTrue(lines[1].startswith("Initial gaps:"))
        self.assertIn("Time_s", lines[2])

    def test_csv_text_structure(self):
        """Test CSV text has correct structure."""
        csv_text = CSVWriter.scenario_to_csv_text(self.scenario)

        lines = csv_text.split("\n")

        # Line 0: Description
        self.assertTrue(lines[0].startswith("Description: "))

        # Line 1: Initial gaps — label in col 0, values in subsequent columns
        self.assertTrue(lines[1].startswith("Initial gaps:"))

        # Line 2: Header
        header = lines[2]
        columns = header.split(",")
        self.assertEqual(len(columns), 6)

        # Lines 3+: Data rows
        if len(lines) > 3:
            data_line = lines[3]
            data_columns = data_line.split(",")
            self.assertEqual(len(data_columns), 6)

    def test_csv_text_data_rows_count(self):
        """Test CSV text has correct number of data rows."""
        # Scenario with no events should still have headers, just no data rows
        scenario = Scenario(
            metadata=self.metadata,
            truck_count=2,
            scenario_duration_s=120.0,
            velocity_type=VelocityType.NOMINAL,
            gap_type=GapType.SMALL,
            initial_gaps=[5.0],
            velocity_events=[],
            loss_resume_pairs=[],
            fort_event=None,
        )

        csv_text = CSVWriter.scenario_to_csv_text(scenario)
        lines = csv_text.split("\n")

        # 3 header lines, 0 data lines
        self.assertEqual(len(lines), 3)

    def test_csv_text_with_multiple_events(self):
        """Test CSV text with multiple events."""
        velocity_event1 = VelocityEvent(
            timestamp_s=10.0,
            truck_id=1,
            velocity_type=VelocityType.NOMINAL,
            velocity_kph=60.0,
            notes="Start",
        )

        velocity_event2 = VelocityEvent(
            timestamp_s=100.0,
            truck_id=1,
            velocity_type=VelocityType.NOMINAL,
            velocity_kph=50.0,
            notes="Slow down",
        )

        scenario = Scenario(
            metadata=self.metadata,
            truck_count=2,
            scenario_duration_s=120.0,
            velocity_type=VelocityType.NOMINAL,
            gap_type=GapType.SMALL,
            initial_gaps=[5.0],
            velocity_events=[velocity_event1, velocity_event2],
            loss_resume_pairs=[],
            fort_event=None,
        )

        csv_text = CSVWriter.scenario_to_csv_text(scenario)
        lines = csv_text.split("\n")

        # 3 header lines + 2 data lines
        self.assertEqual(len(lines), 5)


class TestCSVFileWriting(unittest.TestCase):
    """Test file I/O operations."""

    def setUp(self):
        """Create test scenario and temporary directory."""
        self.metadata = ScenarioMetadata(
            name="test_scenario",
            description="Test scenario",
            generated_at=datetime.now(),
            seed=42,
        )

        self.scenario = Scenario(
            metadata=self.metadata,
            truck_count=2,
            scenario_duration_s=120.0,
            velocity_type=VelocityType.NOMINAL,
            gap_type=GapType.SMALL,
            initial_gaps=[5.0],
            velocity_events=[],
            loss_resume_pairs=[],
            fort_event=None,
        )

        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_write_single_scenario_file(self):
        """Test writing a single scenario file."""
        output_path = os.path.join(self.temp_dir, "test.csv")

        result_path = CSVWriter.write_scenario_file(self.scenario, output_path)

        # File should exist
        self.assertTrue(os.path.exists(result_path))

        # Path should be absolute
        self.assertTrue(os.path.isabs(result_path))

    def test_write_scenario_file_content(self):
        """Test that written file contains expected content."""
        output_path = os.path.join(self.temp_dir, "test.csv")

        CSVWriter.write_scenario_file(self.scenario, output_path)

        # Read file back
        with open(output_path, "r") as f:
            content = f.read()

        # Check content
        self.assertIn("Description: ", content)
        self.assertIn("Initial gaps:", content)   # label (no trailing space)
        self.assertIn("Time_s", content)

    def test_write_scenario_creates_directory(self):
        """Test that write_scenario_file creates missing directories."""
        nested_path = os.path.join(self.temp_dir, "nested", "deep", "test.csv")

        # Directory shouldn't exist yet
        self.assertFalse(os.path.exists(os.path.dirname(nested_path)))

        CSVWriter.write_scenario_file(self.scenario, nested_path)

        # File should be created
        self.assertTrue(os.path.exists(nested_path))

    def test_write_scenario_with_invalid_path(self):
        """Test error handling for invalid paths."""
        # Create a file, then try to write to a path where the parent is a file
        file_as_dir = os.path.join(self.temp_dir, "file.txt")
        with open(file_as_dir, "w") as f:
            f.write("test")

        # Try to write to a path where the parent is a file, not a directory
        invalid_path = os.path.join(file_as_dir, "subdir", "test.csv")

        # Should raise IOError or OSError
        with self.assertRaises((IOError, OSError)):
            CSVWriter.write_scenario_file(self.scenario, invalid_path)

    def test_write_scenarios_batch(self):
        """Test writing multiple scenarios to a folder."""
        scenarios = [
            self.scenario,
            Scenario(
                metadata=ScenarioMetadata(
                    name="scenario2",
                    description="Second scenario",
                    generated_at=datetime.now(),
                    seed=43,
                ),
                truck_count=3,
                scenario_duration_s=120.0,
                velocity_type=VelocityType.HIGH_VARIABLE,
                gap_type=GapType.MEDIUM,
                initial_gaps=[10.0, 10.0],
                velocity_events=[],
                loss_resume_pairs=[],
                fort_event=None,
            ),
        ]

        result_paths = CSVWriter.write_scenarios_batch(scenarios, self.temp_dir)

        # Should return 2 paths
        self.assertEqual(len(result_paths), 2)

        # Both files should exist
        for path in result_paths:
            self.assertTrue(os.path.exists(path))

    def test_write_scenarios_batch_filenames(self):
        """Test that batch-written files use scenario names as filenames."""
        scenarios = [
            Scenario(
                metadata=ScenarioMetadata(
                    name="scenario_A",
                    description="Scenario A",
                    generated_at=datetime.now(),
                    seed=42,
                ),
                truck_count=2,
                scenario_duration_s=120.0,
                velocity_type=VelocityType.NOMINAL,
                gap_type=GapType.SMALL,
                initial_gaps=[5.0],
                velocity_events=[],
                loss_resume_pairs=[],
                fort_event=None,
            ),
            Scenario(
                metadata=ScenarioMetadata(
                    name="scenario_B",
                    description="Scenario B",
                    generated_at=datetime.now(),
                    seed=43,
                ),
                truck_count=3,
                scenario_duration_s=120.0,
                velocity_type=VelocityType.MEDIUM_VARIABLE,
                gap_type=GapType.BIG,
                initial_gaps=[20.0, 20.0],
                velocity_events=[],
                loss_resume_pairs=[],
                fort_event=None,
            ),
        ]

        CSVWriter.write_scenarios_batch(scenarios, self.temp_dir)

        # Check files exist with correct names (counter prefix added for sorting)
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "1_scenario_A.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "2_scenario_B.csv")))


class TestCSVRoundTrip(unittest.TestCase):
    """Test reading back and verifying CSV content."""

    def setUp(self):
        """Create test scenario with various events."""
        velocity_event = VelocityEvent(
            timestamp_s=10.0,
            truck_id=1,
            velocity_type=VelocityType.NOMINAL,
            velocity_kph=60.0,
            notes="Start",
        )

        loss_event = IdentificationLossEvent(
            timestamp_s=30.0,
            truck_id=2,
            is_loss=True,
            loss_type=LossType.QUICK_SHORT,
            duration_s=15.0,
            notes="Loss",
        )

        resume_event = IdentificationLossEvent(
            timestamp_s=45.0,
            truck_id=2,
            is_loss=False,
            notes="Resume",
        )

        fort_event = FORTEvent(
            timestamp_s=110.0,
            truck_id=1,
            notes="FORT",
        )

        self.metadata = ScenarioMetadata(
            name="roundtrip_test",
            description="Test scenario for round-trip",
            generated_at=datetime.now(),
            seed=42,
        )

        self.scenario = Scenario(
            metadata=self.metadata,
            truck_count=2,
            scenario_duration_s=120.0,
            velocity_type=VelocityType.NOMINAL,
            gap_type=GapType.SMALL,
            initial_gaps=[5.0],
            velocity_events=[velocity_event],
            loss_resume_pairs=[LossResumePair(loss_event, resume_event)],
            fort_event=fort_event,
        )

        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_csv_text_read_back(self):
        """Test that CSV text can be read back and parsed."""
        csv_text = CSVWriter.scenario_to_csv_text(self.scenario)

        lines = csv_text.split("\n")

        # Verify structure
        self.assertEqual(len(lines), 7)  # 3 headers + 4 data rows

        # Parse lines
        desc_line = lines[0]
        gaps_line = lines[1]
        header_line = lines[2]
        data_lines = lines[3:]

        # Verify description
        self.assertIn("Description: Test scenario for round-trip", desc_line)

        # Verify gaps — new format: Initial gaps:,5,,,,  (g-format strips .0)
        parts = gaps_line.split(",")
        self.assertEqual(parts[0], "Initial gaps:")
        self.assertEqual(float(parts[1]), 5.0)

        # Verify header
        header_parts = header_line.split(",")
        self.assertEqual(header_parts[0], "Time_s")
        self.assertEqual(header_parts[1], "Truck1_Velocity_kph")

    def test_csv_file_read_back(self):
        """Test that CSV file can be written and read back."""
        output_path = os.path.join(self.temp_dir, "roundtrip.csv")

        CSVWriter.write_scenario_file(self.scenario, output_path)

        # Read file back
        with open(output_path, "r") as f:
            lines = f.readlines()

        # Should have content
        self.assertGreater(len(lines), 0)

        # Strip newlines
        lines = [line.rstrip("\n") for line in lines]

        # Verify structure
        self.assertTrue(lines[0].startswith("Description: "))
        self.assertTrue(lines[1].startswith("Initial gaps:"))
        self.assertIn("Time_s", lines[2])

    def test_csv_data_integrity(self):
        """Test that all events are present in CSV output."""
        output_path = os.path.join(self.temp_dir, "roundtrip.csv")

        CSVWriter.write_scenario_file(self.scenario, output_path)

        # Read file back
        with open(output_path, "r") as f:
            content = f.read()

        # Should contain all event markers
        self.assertIn("60.00", content)  # Velocity (2 decimal places)
        self.assertIn("Loss", content)
        self.assertIn("Resume", content)
        self.assertIn("FORT activated", content)


if __name__ == "__main__":
    unittest.main()
