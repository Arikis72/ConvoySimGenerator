"""
validation.py — Scenario constraint validation

Provides validators for timestamps, event separation, FORT placement, and other rules.
"""

from typing import List
from models import Scenario, ScenarioEvent, FORTEvent, VelocityEvent


class ScenarioValidator:
    """Validates scenario constraints."""

    @staticmethod
    def validate_timestamps_ordered(scenario: Scenario) -> bool:
        """
        Validate that events are in chronological order.

        Args:
            scenario: Scenario to validate

        Returns:
            True if valid

        Raises:
            ValueError: If events are out of order
        """
        events = scenario.get_all_events()
        for i in range(1, len(events)):
            if events[i].timestamp_s < events[i - 1].timestamp_s:
                raise ValueError(
                    f"Event {i} timestamp {events[i].timestamp_s} < "
                    f"previous {events[i-1].timestamp_s}"
                )
        return True

    @staticmethod
    def validate_timestamps_in_range(scenario: Scenario) -> bool:
        """
        Validate that all event timestamps are within scenario duration.

        Args:
            scenario: Scenario to validate

        Returns:
            True if valid

        Raises:
            ValueError: If any timestamp is out of range
        """
        events = scenario.get_all_events()
        for event in events:
            if event.timestamp_s < 0 or event.timestamp_s > scenario.scenario_duration_s:
                raise ValueError(
                    f"Event timestamp {event.timestamp_s} out of range "
                    f"[0, {scenario.scenario_duration_s}]"
                )
        return True

    @staticmethod
    def validate_event_separation(
        scenario: Scenario, min_separation_s: float
    ) -> bool:
        """
        Validate that consecutive events are separated by at least min_separation_s.

        Args:
            scenario: Scenario to validate
            min_separation_s: Minimum required separation in seconds

        Returns:
            True if valid

        Raises:
            ValueError: If separation is violated
        """
        events = scenario.get_all_events()
        for i in range(1, len(events)):
            # Velocity waypoints form a continuous interpolated curve and may be
            # intentionally close (startup ramp, hard-brake deceleration pair).
            # min_event_separation applies only to discrete events (loss, resume,
            # FORT).  Skip the check whenever both neighbours are velocity events.
            if isinstance(events[i - 1], VelocityEvent) and isinstance(events[i], VelocityEvent):
                continue
            separation = events[i].timestamp_s - events[i - 1].timestamp_s
            if separation < min_separation_s:
                raise ValueError(
                    f"Event {i} too close to event {i-1}: "
                    f"separation {separation}s < {min_separation_s}s"
                )
        return True

    @staticmethod
    def validate_fort_placement(scenario: Scenario) -> bool:
        """
        Validate that FORT event (if present) is the last event.

        Args:
            scenario: Scenario to validate

        Returns:
            True if valid

        Raises:
            ValueError: If FORT is not the last event
        """
        if scenario.fort_event is None:
            return True  # No FORT, pass

        events = scenario.get_all_events()
        if events[-1] != scenario.fort_event:
            raise ValueError(
                f"FORT event at {scenario.fort_event.timestamp_s} is not the last event"
            )
        return True

    @staticmethod
    def validate_fort_count(scenario: Scenario) -> bool:
        """
        Validate that there is at most 1 FORT event.

        Args:
            scenario: Scenario to validate

        Returns:
            True if valid

        Raises:
            ValueError: If more than 1 FORT event
        """
        fort_count = 1 if scenario.fort_event else 0
        if fort_count > 1:
            raise ValueError(f"Too many FORT events: {fort_count} (max 1)")
        return True

    @staticmethod
    def validate_loss_resume_pairing(scenario: Scenario) -> bool:
        """
        Validate that loss events have corresponding resume events.

        Args:
            scenario: Scenario to validate

        Returns:
            True if valid

        Raises:
            ValueError: If loss/resume pairing is violated
        """
        for pair in scenario.loss_resume_pairs:
            if pair.loss_event.timestamp_s >= pair.resume_event.timestamp_s:
                raise ValueError(
                    f"Loss at {pair.loss_event.timestamp_s} >= "
                    f"resume at {pair.resume_event.timestamp_s}"
                )
        return True

    @staticmethod
    def validate_truck_count(scenario: Scenario) -> bool:
        """
        Validate truck count is 2 or 3.

        Args:
            scenario: Scenario to validate

        Returns:
            True if valid

        Raises:
            ValueError: If truck count is invalid
        """
        if scenario.truck_count not in [2, 3]:
            raise ValueError(f"truck_count must be 2 or 3, got {scenario.truck_count}")
        return True

    @staticmethod
    def validate_initial_gaps(scenario: Scenario) -> bool:
        """
        Validate initial gaps list matches truck count.

        Args:
            scenario: Scenario to validate

        Returns:
            True if valid

        Raises:
            ValueError: If gaps don't match truck count
        """
        expected_gap_count = scenario.truck_count - 1
        if len(scenario.initial_gaps) != expected_gap_count:
            raise ValueError(
                f"initial_gaps has {len(scenario.initial_gaps)} values, "
                f"expected {expected_gap_count} for {scenario.truck_count} trucks"
            )
        return True

    @staticmethod
    def validate_loss_resume_trucks(scenario: Scenario) -> bool:
        """
        Validate that loss/resume events only affect Trucks #2 and #3.

        Args:
            scenario: Scenario to validate

        Returns:
            True if valid

        Raises:
            ValueError: If loss event affects wrong truck
        """
        for pair in scenario.loss_resume_pairs:
            if pair.loss_event.truck_id not in [2, 3]:
                raise ValueError(
                    f"Loss event affects truck {pair.loss_event.truck_id}, "
                    f"expected 2 or 3"
                )
        return True

    @staticmethod
    def validate_loss_resume_sequencing(scenario: Scenario) -> bool:
        """
        Validate that Loss and Resume events alternate correctly per truck.

        For each truck (2 and 3), loss and resume events must alternate:
        Loss → Resume → Loss → Resume...
        Cannot have consecutive Loss or Resume events for the same truck.

        Args:
            scenario: Scenario to validate

        Returns:
            True if valid

        Raises:
            ValueError: If sequencing is invalid for any truck
        """
        # Group loss/resume events by truck
        events_by_truck = {2: [], 3: []}

        for pair in scenario.loss_resume_pairs:
            truck_id = pair.loss_event.truck_id
            if truck_id in events_by_truck:
                events_by_truck[truck_id].append((pair.loss_event.timestamp_s, "Loss"))
                events_by_truck[truck_id].append((pair.resume_event.timestamp_s, "Resume"))

        # Check alternation for each truck independently
        for truck_id, events in events_by_truck.items():
            if not events:
                continue

            # Sort by timestamp
            events.sort(key=lambda x: x[0])

            # Validate alternation pattern: Loss → Resume → Loss → Resume...
            for i in range(1, len(events)):
                prev_type = events[i - 1][1]
                curr_type = events[i][1]

                if prev_type == "Loss" and curr_type != "Resume":
                    raise ValueError(
                        f"Truck {truck_id}: Loss at {events[i-1][0]}s not followed by Resume "
                        f"(next event is {curr_type} at {events[i][0]}s)"
                    )
                if prev_type == "Resume" and curr_type != "Loss" and i < len(events) - 1:
                    raise ValueError(
                        f"Truck {truck_id}: Resume at {events[i-1][0]}s not followed by Loss "
                        f"(next event is {curr_type} at {events[i][0]}s)"
                    )

        return True

    @staticmethod
    def validate_all(
        scenario: Scenario, min_event_separation_s: float = 0.0
    ) -> bool:
        """
        Run all validation checks.

        Args:
            scenario: Scenario to validate
            min_event_separation_s: Minimum event separation constraint

        Returns:
            True if all checks pass

        Raises:
            ValueError: With detailed message if any check fails
        """
        checks = [
            ("truck_count", lambda: ScenarioValidator.validate_truck_count(scenario)),
            (
                "initial_gaps",
                lambda: ScenarioValidator.validate_initial_gaps(scenario),
            ),
            (
                "timestamps_in_range",
                lambda: ScenarioValidator.validate_timestamps_in_range(scenario),
            ),
            (
                "timestamps_ordered",
                lambda: ScenarioValidator.validate_timestamps_ordered(scenario),
            ),
            (
                "event_separation",
                lambda: ScenarioValidator.validate_event_separation(
                    scenario, min_event_separation_s
                ),
            ),
            (
                "loss_resume_pairing",
                lambda: ScenarioValidator.validate_loss_resume_pairing(scenario),
            ),
            (
                "loss_resume_sequencing",
                lambda: ScenarioValidator.validate_loss_resume_sequencing(scenario),
            ),
            (
                "loss_resume_trucks",
                lambda: ScenarioValidator.validate_loss_resume_trucks(scenario),
            ),
            ("fort_count", lambda: ScenarioValidator.validate_fort_count(scenario)),
            ("fort_placement", lambda: ScenarioValidator.validate_fort_placement(scenario)),
        ]

        for check_name, check_func in checks:
            try:
                check_func()
            except ValueError as e:
                raise ValueError(f"Validation failed ({check_name}): {e}")

        return True
