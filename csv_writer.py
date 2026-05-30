"""
csv_writer.py — CSV output formatting and file writing

Handles conversion of Scenario objects to ConvoySIM-compatible CSV format.
"""

import os
from pathlib import Path
from typing import List
from models import (
    Scenario,
    CSVRow,
    VelocityEvent,
    IdentificationLossEvent,
    FORTEvent,
)


class CSVWriter:
    """Writes scenarios to CSV files."""

    @staticmethod
    def format_description_row(scenario: Scenario) -> str:
        """
        Format the description row (Row 1).

        Args:
            scenario: Scenario to describe

        Returns:
            CSV row text
        """
        return f"Description: {scenario.metadata.description}"

    @staticmethod
    def format_initial_gaps_row(scenario: Scenario) -> str:
        """
        Format the initial gaps row (Row 2).

        Each gap value occupies its own CSV column so the row aligns with the
        data rows when opened in a spreadsheet.  The label is in column 0 and
        gap values start at column 1, with the remaining columns left empty.

        Example (3 trucks, gaps 10 m and 10 m):
            Initial gaps:,10,10,,,

        Args:
            scenario: Scenario with initial gaps

        Returns:
            CSV row text with 6 comma-separated fields
        """
        # Build fields: label then one field per gap, rest empty
        fields = ["Initial gaps:"]
        for g in scenario.initial_gaps:
            # Strip unnecessary trailing zeros (5.0 → "5", 12.5 → "12.5")
            fields.append(f"{g:g}")
        # Pad to 6 columns total (matches header + data rows)
        while len(fields) < 6:
            fields.append("")
        return ",".join(fields)

    @staticmethod
    def format_header_row() -> str:
        """
        Format the CSV header row (Row 3).

        Returns:
            CSV header line
        """
        return "Time_s,Truck1_Velocity_kph,Truck1_Event,Truck2_Image_Event,Truck3_Image_Event,Notes"

    @staticmethod
    def scenario_to_csv_rows(scenario: Scenario) -> List[CSVRow]:
        """
        Convert a scenario to CSVRow objects.

        Args:
            scenario: Scenario to convert

        Returns:
            List of CSVRow objects (data rows only, excluding headers)
        """
        rows: List[CSVRow] = []

        # Collect all events
        events = scenario.get_all_events()

        # Process events in chronological order
        for event in events:
            if isinstance(event, VelocityEvent):
                rows.append(
                    CSVRow(
                        time_s=event.timestamp_s,
                        truck1_velocity_kph=event.velocity_kph,
                        truck1_event=None,
                        truck2_image_event=None,
                        truck3_image_event=None,
                        notes=event.notes,
                    )
                )

            elif isinstance(event, IdentificationLossEvent):
                event_str = "Loss" if event.is_loss else "Resume"

                if event.truck_id == 2:
                    rows.append(
                        CSVRow(
                            time_s=event.timestamp_s,
                            truck1_velocity_kph=None,
                            truck1_event=None,
                            truck2_image_event=event_str,
                            truck3_image_event=None,
                            notes=event.notes,
                        )
                    )
                elif event.truck_id == 3:
                    rows.append(
                        CSVRow(
                            time_s=event.timestamp_s,
                            truck1_velocity_kph=None,
                            truck1_event=None,
                            truck2_image_event=None,
                            truck3_image_event=event_str,
                            notes=event.notes,
                        )
                    )

            elif isinstance(event, FORTEvent):
                rows.append(
                    CSVRow(
                        time_s=event.timestamp_s,
                        truck1_velocity_kph=None,
                        truck1_event="FORT activated",
                        truck2_image_event=None,
                        truck3_image_event=None,
                        notes=event.notes,
                    )
                )

        # Sort by timestamp to ensure correct order
        rows.sort(key=lambda r: r.time_s)

        return rows

    @staticmethod
    def scenario_to_csv_text(scenario: Scenario) -> str:
        """
        Convert scenario to complete CSV text.

        Args:
            scenario: Scenario to convert

        Returns:
            Multi-line CSV text (lines separated by newline)
        """
        lines = [
            CSVWriter.format_description_row(scenario),
            CSVWriter.format_initial_gaps_row(scenario),
            CSVWriter.format_header_row(),
        ]

        # Add data rows
        csv_rows = CSVWriter.scenario_to_csv_rows(scenario)
        for row in csv_rows:
            lines.append(row.to_csv_row())

        return "\n".join(lines)

    @staticmethod
    def write_scenario_file(scenario: Scenario, output_path: str) -> str:
        """
        Write scenario to a CSV file.

        Args:
            scenario: Scenario to write
            output_path: Path to write to (should end in .csv)

        Returns:
            Absolute path to written file

        Raises:
            IOError: If file cannot be written
            ValueError: If output_path is invalid
        """
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Convert scenario to CSV text
        csv_text = CSVWriter.scenario_to_csv_text(scenario)

        # Write file
        try:
            with open(output_path, "w", newline="") as f:
                f.write(csv_text)
        except IOError as e:
            raise IOError(f"Failed to write scenario file '{output_path}': {e}")

        return os.path.abspath(output_path)

    @staticmethod
    def write_scenarios_batch(
        scenarios: List[Scenario], output_folder: str
    ) -> List[str]:
        """
        Write multiple scenarios to a folder.

        Args:
            scenarios: List of scenarios to write
            output_folder: Folder to write to

        Returns:
            List of absolute paths to written files

        Raises:
            IOError: If any file cannot be written
        """
        # Ensure folder exists
        os.makedirs(output_folder, exist_ok=True)

        written_paths = []
        for counter, scenario in enumerate(scenarios, start=1):
            # Prepend counter to filename for sorting (e.g., "1_3T_hV_sG_idL2sl_0ES.csv")
            filename = f"{counter}_{scenario.metadata.name}.csv"
            output_path = os.path.join(output_folder, filename)
            path = CSVWriter.write_scenario_file(scenario, output_path)
            written_paths.append(path)

        return written_paths
