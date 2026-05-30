"""
generator.py — Core scenario generation logic

Main ScenarioGenerator class that orchestrates random scenario creation.
"""

import random
from datetime import datetime
from typing import List, Optional, Callable, Tuple
from models import (
    ScenarioConfig,
    Scenario,
    ScenarioMetadata,
    ScenarioEvent,
    VelocityEvent,
    IdentificationLossEvent,
    LossResumePair,
    VelocityType,
    GapType,
    LossType,
    FORTEvent,
)
from events import VelocityProfile, create_loss_resume_pair, create_fort_event
from naming import ScenarioNameEncoder
from validation import ScenarioValidator
from csv_writer import CSVWriter


class ScenarioGenerator:
    """
    Main scenario generation orchestrator.

    Generates randomized convoy scenarios matching ConvoySIM requirements.
    """

    def __init__(
        self,
        config: ScenarioConfig,
        seed: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ):
        """
        Initialize generator.

        Args:
            config: Generation configuration (duration, max_events, constraints, etc.)
            seed: Random seed for reproducibility (None = random seed)
            progress_callback: Optional callback(current, total) for progress tracking
        """
        self.config = config
        self.seed = seed or random.randint(0, 2**31 - 1)
        self.progress_callback = progress_callback

        random.seed(self.seed)

    def generate_all(self) -> List[Scenario]:
        """
        Generate all configured scenarios.

        Returns:
            List of generated Scenario objects

        Raises:
            ValueError: If configuration is invalid
        """
        self.config.validate()

        scenarios = []
        for i in range(self.config.num_scenarios):
            scenario = self._generate_one_scenario()
            scenarios.append(scenario)

            # Emit progress
            if self.progress_callback:
                self.progress_callback(i + 1, self.config.num_scenarios)

        return scenarios

    def _generate_one_scenario(self) -> Scenario:
        """
        Generate a single scenario.

        Returns:
            A valid Scenario object

        Raises:
            RuntimeError: If cannot generate valid scenario after retries
        """
        max_retries = 5
        for attempt in range(max_retries):
            try:
                scenario = self._compose_scenario()
                ScenarioValidator.validate_all(
                    scenario, self.config.min_event_separation_s
                )
                return scenario
            except (ValueError, RuntimeError) as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(
                        f"Failed to generate valid scenario after {max_retries} attempts: {e}"
                    )
                # Retry with new random values
                continue

        raise RuntimeError("Failed to generate scenario")

    def _compose_scenario(self) -> Scenario:
        """
        Compose a scenario by selecting and combining event types.

        Returns:
            Scenario (may not be fully validated yet)
        """
        # Phase 1: Random Selection with category filtering
        truck_count = random.choice([2, 3])

        # Velocity type: filter by selected_categories if specified, and by max_events budget
        # Account for velocity event counts when selecting profile type:
        # - NOMINAL: 1-2 events (safe for max_events >= 2)
        # - HARD_BRAKE: 3-4 events (needs max_events >= 4)
        # - HIGH_VARIABLE: 6-10 events (needs max_events >= 10)
        # - MEDIUM_VARIABLE: 8-12 events (needs max_events >= 12)
        velocity_types = self._filter_by_category(list(VelocityType), 'velocity_type')

        # Restrict velocity types based on available budget.
        # With startup ramp, event counts are:
        #   NOMINAL:         3 events  (0→ramp→end)
        #   HARD_BRAKE:    4-5 events  (0→ramp→brake_start→brake→end)
        #   HIGH_VARIABLE: 7-11 events (0→ramp + 6-10 random samples)
        #   MEDIUM_VARIABLE:9-13 events (0→ramp + 8-12 random samples)
        if self.config.max_events <= 4:
            # Only allow NOMINAL (3 events with ramp, leaving 1 slot for FORT)
            velocity_types = [vt for vt in velocity_types if vt == VelocityType.NOMINAL]
        elif self.config.max_events <= 6:
            # Allow NOMINAL and HARD_BRAKE (max 5 events with ramp, leaving 1 for FORT)
            velocity_types = [vt for vt in velocity_types if vt in [VelocityType.NOMINAL, VelocityType.HARD_BRAKE]]
        elif self.config.max_events <= 10:
            # Allow NOMINAL, HARD_BRAKE, HIGH_VARIABLE (7-11 events with ramp)
            velocity_types = [vt for vt in velocity_types if vt in [VelocityType.NOMINAL, VelocityType.HARD_BRAKE, VelocityType.HIGH_VARIABLE]]
        # else: all types allowed for max_events >= 11

        if not velocity_types:
            # Fallback: if user restricted categories too much, use NOMINAL
            velocity_types = [VelocityType.NOMINAL]

        velocity_type = random.choice(velocity_types)

        # Gap type: filter by selected_categories if specified
        gap_types = self._filter_by_category(list(GapType), 'gap_type')
        gap_type = random.choice(gap_types)

        # Loss types: filter by selected_categories if specified
        loss_types_available = self._filter_by_category(list(LossType), 'loss_type')

        # FORT: check if it's in selected_categories
        # FORT is independent of loss events, but must fit within the max_events budget.
        # We'll decide whether to include FORT after we know the velocity event count.
        fort_allowed = self._is_category_allowed('fort', 'yes')

        # Phase 2: Event Composition
        # Generate velocity profile.
        # max_velocity_kph is the hard ceiling (constant speed for NOMINAL; cruise speed for HARD_BRAKE).
        # For variable profiles (mV, hV) the *center* of the random walk is set 15 % below the ceiling
        # so the profile can vary naturally both above and below the center — without the ceiling
        # clipping every upward step and turning the walk into a one-sided downward drift.
        nominal_kph        = self.config.max_velocity_kph        # speed for NOMINAL / HARD_BRAKE
        variable_center_kph = self.config.max_velocity_kph * 0.85  # walk center for variable profiles

        velocity_profile = VelocityProfile(
            velocity_type,
            self.config.scenario_duration_s,
            max_velocity_kph=self.config.max_velocity_kph,
            max_acceleration_mps2=self.config.max_acceleration_mps2,
        )

        if velocity_type == VelocityType.NOMINAL:
            velocity_profile.generate_nominal(nominal_kph=nominal_kph)
        elif velocity_type == VelocityType.MEDIUM_VARIABLE:
            velocity_profile.generate_medium_variable(
                nominal_kph=variable_center_kph,
                variation_percent=20.0,   # ±20 % gives ≈5 kph spread at 17 kph nominal
            )
        elif velocity_type == VelocityType.HIGH_VARIABLE:
            velocity_profile.generate_high_variable(
                min_kph=max(5.0, variable_center_kph * 0.50),
                max_kph=nominal_kph,      # ceiling is the upper bound for hV jumps
            )
        elif velocity_type == VelocityType.HARD_BRAKE:
            velocity_profile.generate_hard_brake(
                nominal_kph=nominal_kph,
                brake_target_kph=max(5.0, nominal_kph * 0.33),
            )

        velocity_events = velocity_profile.to_velocity_events()

        # Enforce max_events constraint. max_events is the TOTAL event cap, which includes:
        # - velocity waypoints (already generated)
        # - loss/resume pairs (each pair = 2 events)
        # - FORT event (1 event)
        # If velocity events exceed max_events, force this scenario to be invalid
        # so it gets regenerated (via the retry logic in _generate_one_scenario).
        velocity_event_count = len(velocity_events)
        if velocity_event_count > self.config.max_events:
            # Velocity events alone exceed budget - regenerate
            raise ValueError(f"Velocity profile has {velocity_event_count} events, exceeds max_events={self.config.max_events}")

        remaining_budget = self.config.max_events - velocity_event_count

        # FORT takes 1 event slot; decide if there's room for it
        fort_budget_used = 0
        has_fort = False
        if fort_allowed and remaining_budget > 0:
            has_fort = random.choice([True, False])
            if has_fort:
                fort_budget_used = 1

        # Each loss/resume pair counts as 2 events, limit by remaining budget
        loss_budget_available = remaining_budget - fort_budget_used
        max_loss_events_allowed = loss_budget_available // 2
        num_loss_events = random.randint(0, min(max_loss_events_allowed, len(loss_types_available)) if loss_types_available else 0)

        # Generate initial gaps based on gap_type
        initial_gaps = self._generate_initial_gaps(gap_type, truck_count)

        # Generate loss/resume pairs (timestamps will be assigned later).
        # All losses in a scenario share a single type so the filename accurately
        # reflects the behaviour (e.g. idL2qs means every pair is QUICK_SHORT).
        if num_loss_events > 0 and loss_types_available:
            shared_loss_type = random.choice(loss_types_available)
            loss_types = [shared_loss_type] * num_loss_events
        else:
            loss_types = []
        loss_resume_pairs = []

        for loss_type in loss_types:
            # Sample from follower trucks only — BUG-06 fix: respect truck_count
            # 2T → only T2 available; 3T → T2 or T3
            affected_truck = random.choice(list(range(2, truck_count + 1)))

            # Create pair with placeholder timestamp (will be assigned in _assign_timestamps)
            pair = create_loss_resume_pair(
                truck_id=affected_truck,
                loss_timestamp_s=0.0,  # Placeholder
                loss_type=loss_type,
            )
            loss_resume_pairs.append(pair)

        # Create FORT event (if selected, timestamp will be assigned later)
        fort_event = None
        if has_fort:
            fort_event = FORTEvent(timestamp_s=0.0, truck_id=1, notes="Emergency stop")

        # Phase 3: Assign timestamps respecting constraints.
        # Returns actual placed events — some pairs or FORT may be dropped when
        # there is no valid slot.  Use the returned values for naming so the
        # filename always matches the CSV contents.
        velocity_events, loss_resume_pairs, fort_event, actual_loss_types = (
            self._assign_timestamps(velocity_events, loss_resume_pairs, fort_event)
        )
        actual_has_fort = fort_event is not None

        # Phase 4: Generate name and description from *actual* (placed) events
        scenario_name = ScenarioNameEncoder.generate_name(
            truck_count=truck_count,
            velocity_type=velocity_type,
            gap_type=gap_type,
            loss_types=actual_loss_types,
            has_fort=actual_has_fort,
        )

        metadata = ScenarioMetadata(
            name=scenario_name,
            description=self._generate_description(
                truck_count, velocity_type, gap_type, actual_loss_types, actual_has_fort
            ),
            generated_at=datetime.now(),
            seed=self.seed,
        )

        scenario = Scenario(
            metadata=metadata,
            truck_count=truck_count,
            scenario_duration_s=self.config.scenario_duration_s,
            velocity_type=velocity_type,
            gap_type=gap_type,
            initial_gaps=initial_gaps,
            velocity_events=velocity_events,
            loss_resume_pairs=loss_resume_pairs,
            fort_event=fort_event,
        )

        return scenario

    def _assign_timestamps(
        self,
        velocity_events: List[VelocityEvent],
        loss_resume_pairs: List[LossResumePair],
        fort_event: Optional[FORTEvent],
    ) -> Tuple[List[VelocityEvent], List[LossResumePair], Optional[FORTEvent], List[LossType]]:
        """
        Assign timestamps to all events respecting min_event_separation constraint.

        This method ensures:
        - All event timestamps respect min_event_separation_s
        - Loss/resume pairs have correct duration
        - Resume timestamps fit within scenario_duration_s
        - FORT event (if present) is the last event
        - All timestamps are in chronological order

        Args:
            velocity_events: List of velocity events (already have timestamps)
            loss_resume_pairs: List of loss/resume pairs (need timestamp assignment)
            fort_event: Optional FORT event (needs timestamp assignment)

        Returns:
            Tuple of (velocity_events, loss_resume_pairs, fort_event, actual_loss_types)
            reflecting what was *actually* placed (some pairs may be dropped when no
            valid slot exists; FORT may be dropped if the scenario is too tight).
        """
        min_sep = self.config.min_event_separation_s
        duration = self.config.scenario_duration_s

        # ── Step 1: Pass all velocity profile waypoints through unchanged ──
        # Velocity events form a continuous interpolated curve; applying
        # min_event_separation to them would silently drop intentionally close
        # waypoints.  The hard-brake profile in particular relies on two points
        # that are only ~1–2 s apart to represent the sharp deceleration — the
        # old filter was destroying that pair and leaving a flat constant-speed
        # profile.  min_sep is enforced between *discrete* event types (loss,
        # resume, FORT) in steps 3–5 below.
        filtered_velocity_events: List[VelocityEvent] = list(velocity_events)

        # ── Step 2: If FORT is planned, ensure there is room for it at the end ──
        # Velocity profiles typically end exactly at scenario_duration_s, which
        # leaves no room for a FORT event (FORT must come *after* all other events
        # with at least min_sep clearance).  Remove tail velocity events until
        # there is a gap of at least min_sep before the scenario end.
        if fort_event is not None:
            while len(filtered_velocity_events) > 1:
                last_v_time = filtered_velocity_events[-1].timestamp_s
                if last_v_time + min_sep > duration:
                    filtered_velocity_events.pop()
                else:
                    break
            # Edge case: only one velocity event left and it still blocks FORT
            if (filtered_velocity_events and
                    filtered_velocity_events[-1].timestamp_s + min_sep > duration):
                # Shift the single event back slightly so FORT can fit at the end
                filtered_velocity_events[-1].timestamp_s = max(
                    0.0, duration - 2 * min_sep
                )

        # ── Step 3: Collect anchor times (velocity events are already placed) ──
        # Track (time, event_type, truck_id) for all assigned events
        all_assigned_events: List[Tuple[float, str, int]] = []
        for e in filtered_velocity_events:
            all_assigned_events.append((e.timestamp_s, "velocity", 1))

        # ── Step 4: Assign timestamps to loss/resume pairs ───────────────────
        updated_pairs: List[LossResumePair] = []

        for pair in loss_resume_pairs:
            assigned = False
            for _ in range(10):
                # Sample loss time: loss + duration must fit before scenario end
                min_loss_time = min_sep
                max_loss_time = (
                    duration - pair.loss_event.duration_s - min_sep
                )

                if max_loss_time <= min_loss_time:
                    break  # No valid window — skip this pair

                loss_time = random.uniform(min_loss_time, max_loss_time)
                resume_time = loss_time + pair.loss_event.duration_s
                truck_id = pair.loss_event.truck_id

                # Check for collisions with already-assigned times
                collision = any(
                    abs(loss_time - t) < min_sep or abs(resume_time - t) < min_sep
                    for t, _, _ in all_assigned_events
                )

                if collision:
                    continue

                # For same-truck events, ensure Loss → Resume → Loss → Resume pattern
                # Verify that adding this Loss/Resume pair maintains alternation for this truck
                truck_events = [(t, et) for t, et, tid in all_assigned_events if tid == truck_id]
                truck_events.append((loss_time, "loss"))
                truck_events.append((resume_time, "resume"))
                truck_events.sort(key=lambda x: x[0])

                # Check that events alternate: Loss, Resume, Loss, Resume, ...
                invalid_sequence = False
                for i in range(1, len(truck_events)):
                    prev_type = truck_events[i - 1][1]
                    curr_type = truck_events[i][1]

                    if prev_type == "loss" and curr_type != "resume":
                        invalid_sequence = True
                        break
                    if prev_type == "resume" and curr_type != "loss" and i < len(truck_events) - 1:
                        invalid_sequence = True
                        break

                if invalid_sequence:
                    continue

                pair.loss_event.timestamp_s = loss_time
                pair.resume_event.timestamp_s = resume_time
                updated_pairs.append(pair)
                all_assigned_events.extend([
                    (loss_time, "loss", truck_id),
                    (resume_time, "resume", truck_id)
                ])
                assigned = True
                break

            # If not assigned, this pair is silently dropped (can happen when the
            # scenario is very dense).  The name/description will reflect the actual
            # placed count, not the originally planned count.

        # ── Step 5: Assign FORT timestamp (must be last) ─────────────────────
        updated_fort: Optional[FORTEvent] = None
        if fort_event is not None:
            all_times = [t for t, _, _ in all_assigned_events]
            if all_times:
                min_fort_time = max(all_times) + min_sep
            else:
                min_fort_time = duration * 0.8
            max_fort_time = duration

            if min_fort_time <= max_fort_time:
                fort_time = random.uniform(min_fort_time, max_fort_time)
                updated_fort = FORTEvent(
                    timestamp_s=fort_time,
                    truck_id=1,
                    notes=fort_event.notes,
                )
            # else: still no room — FORT is dropped; caller will update the name

        # ── Step 6: Collect actual loss types from placed pairs ───────────────
        actual_loss_types = [p.loss_event.loss_type for p in updated_pairs]

        return filtered_velocity_events, updated_pairs, updated_fort, actual_loss_types

    def _generate_initial_gaps(self, gap_type: GapType, truck_count: int) -> List[float]:
        """
        Generate initial gaps based on gap type or per-gap configurations.

        If gap_configurations are provided in config, use them (ENH-07).
        Otherwise, fall back to gap_type-based generation (legacy).

        Args:
            gap_type: Type of gap configuration (ignored if gap_configurations provided)
            truck_count: Number of trucks (2 or 3)

        Returns:
            List of gap values (count = truck_count - 1)
        """
        expected_gap_count = truck_count - 1

        # ENH-07: Check if per-gap configurations are provided
        if self.config.gap_configurations and len(self.config.gap_configurations) > 0:
            gaps = []
            for i in range(expected_gap_count):
                # Find configuration for this gap index
                gap_config = None
                for gc in self.config.gap_configurations:
                    if gc.gap_index == i:
                        gap_config = gc
                        break

                if gap_config is None:
                    # No configuration for this gap, use default fallback
                    gaps.append(10.0)
                elif gap_config.is_fixed:
                    # Use fixed value
                    gaps.append(gap_config.fixed_value)
                else:
                    # Use range (random value between min and max)
                    gaps.append(random.uniform(gap_config.min_value, gap_config.max_value))

            return gaps

        # Legacy: Generate based on gap_type
        # TODO: Use more realistic gap values based on ConvoySIM parameters
        if gap_type == GapType.SMALL:
            gap_value = 5.0
        elif gap_type == GapType.MEDIUM:
            gap_value = 10.0
        elif gap_type == GapType.BIG:
            gap_value = 20.0
        elif gap_type == GapType.VARIANT:
            # Mix small and large
            return [5.0, 20.0] if truck_count == 3 else [5.0]
        else:
            gap_value = 10.0

        # Return gap count matching truck count - 1
        return [gap_value] * (truck_count - 1)

    def _generate_description(
        self,
        truck_count: int,
        velocity_type: VelocityType,
        gap_type: GapType,
        loss_types: List[LossType],
        has_fort: bool,
    ) -> str:
        """
        Generate human-readable scenario description.

        Args:
            truck_count: Number of trucks
            velocity_type: Velocity type
            gap_type: Gap type
            loss_types: List of loss types
            has_fort: Whether FORT is included

        Returns:
            Description string
        """
        parts = [
            f"{truck_count} trucks",
            f"{velocity_type.name.lower()} velocity",
            f"{gap_type.name.lower()} gaps",
        ]

        if loss_types:
            loss_count = len(loss_types)
            loss_names = ", ".join(lt.name for lt in set(loss_types))
            parts.append(f"{loss_count} {loss_names} ID losses")

        if has_fort:
            parts.append("1 FORT event")

        return ", ".join(parts)

    def _filter_by_category(self, all_items, category_type: str):
        """
        Filter a list of enum items by selected_categories.

        Args:
            all_items: List of enum values (e.g., list(VelocityType))
            category_type: Category name (e.g., 'velocity_type', 'gap_type', 'loss_type')

        Returns:
            Filtered list of enum values. If no filters for this category are set,
            returns the full list (include all).
        """
        if not self.config.selected_categories:
            return all_items

        # Collect matching enum values for this category
        filtered = []
        for item in all_items:
            category_filter = f"{category_type}:{item.value}"
            if category_filter in self.config.selected_categories:
                filtered.append(item)

        # If no matches found, return all (default to non-restrictive)
        return filtered if filtered else all_items

    def _is_category_allowed(self, category_type: str, value: str) -> bool:
        """
        Check if a specific category value is allowed.

        Args:
            category_type: Category name (e.g., 'fort')
            value: Value to check (e.g., 'yes', 'no')

        Returns:
            True if allowed (either explicitly selected or no filters set), False otherwise.
        """
        if not self.config.selected_categories:
            return True

        category_filter = f"{category_type}:{value}"
        if category_filter in self.config.selected_categories:
            return True

        # Check if ANY fort filters are set. If yes, and this one is not selected, deny it.
        fort_filters = [c for c in self.config.selected_categories if c.startswith('fort:')]
        if fort_filters and category_filter not in self.config.selected_categories:
            return False

        # No fort filters set — allow
        return True
