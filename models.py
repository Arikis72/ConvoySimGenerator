"""
models.py — Core data structures for SimGenerator

Defines scenario, event, and configuration models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


# ============================================================================
# Enumerations
# ============================================================================

class VelocityType(Enum):
    """Velocity profile types for Truck #1 leader."""
    NOMINAL = "nV"
    MEDIUM_VARIABLE = "mV"
    HIGH_VARIABLE = "hV"
    HARD_BRAKE = "hB"


class GapType(Enum):
    """Initial gap configuration types."""
    SMALL = "sG"
    MEDIUM = "mG"
    BIG = "bG"
    VARIANT = "vG"


class LossType(Enum):
    """Identification loss resume-time types."""
    QUICK_SHORT = "qs"       # ~15 seconds
    SLOW = "sl"              # ~60 seconds
    FREQUENT_VARIANT = "fv"  # Multiple cycles, mixed timing
    # Potential future subtypes:
    # FIRST_FOLLOWER_QUICK = "fsq"
    # SECOND_FOLLOWER_SLOW = "ssl"


# ============================================================================
# Gap Configuration (for ENH-07)
# ============================================================================

@dataclass
class GapConfiguration:
    """Configuration for a single gap (per-gap fine-grained control)."""

    gap_index: int
    """Gap index: 0 for Gap 1 (between Truck 1 and 2), 1 for Gap 2 (between Truck 2 and 3)."""

    is_fixed: bool
    """If True, use fixed_value; if False, use range (min_value to max_value)."""

    fixed_value: float = 0.0
    """Fixed gap value (in meters) when is_fixed=True."""

    min_value: float = 0.0
    """Minimum gap value (in meters) when is_fixed=False."""

    max_value: float = 0.0
    """Maximum gap value (in meters) when is_fixed=False."""


# ============================================================================
# Generation Configuration
# ============================================================================

@dataclass
class ScenarioConfig:
    """User input parameters for scenario generation."""

    scenario_duration_s: float
    """Total length of each scenario in seconds."""

    max_events: int
    """Maximum number of events per scenario (1 to N)."""

    min_event_separation_s: float
    """Minimum gap between consecutive events in seconds."""

    num_scenarios: int
    """Total number of scenarios to generate."""

    selected_categories: List[str] = field(default_factory=list)
    """User-selected category filters (e.g., ['velocity_type:hV', 'gap_type:sG'])."""

    gap_configurations: List[GapConfiguration] = field(default_factory=list)
    """Per-gap configurations (ENH-07). If provided and non-empty, overrides GapType-based generation."""

    max_velocity_kph: float = 60.0
    """Hard ceiling for all Truck #1 velocity waypoints (kph). Loaded from parameters file."""

    max_acceleration_mps2: float = 10.0
    """Maximum allowed acceleration rate for velocity increases (m/s²). Loaded from parameters file.
    Default 10.0 m/s² = effectively unconstrained for most profiles."""

    def validate(self) -> bool:
        """Validate configuration constraints."""
        if self.scenario_duration_s <= 0:
            raise ValueError("scenario_duration_s must be positive")
        if self.max_events < 1:
            raise ValueError("max_events must be >= 1")
        if self.min_event_separation_s < 0:
            raise ValueError("min_event_separation_s must be >= 0")
        if self.num_scenarios < 1:
            raise ValueError("num_scenarios must be >= 1")
        return True


# ============================================================================
# Events
# ============================================================================

@dataclass
class ScenarioEvent:
    """Base class for scenario events."""

    timestamp_s: float
    """Event timestamp in seconds."""

    truck_id: int
    """Truck affected by this event (1, 2, or 3)."""

    notes: str = ""
    """Optional descriptive notes."""

    def validate_timestamp(self, scenario_duration_s: float) -> bool:
        """Ensure timestamp is within scenario duration."""
        if self.timestamp_s < 0 or self.timestamp_s > scenario_duration_s:
            raise ValueError(
                f"Event timestamp {self.timestamp_s} out of range [0, {scenario_duration_s}]"
            )
        return True


@dataclass
class VelocityEvent(ScenarioEvent):
    """Velocity change event for leader (Truck #1)."""

    velocity_type: VelocityType = VelocityType.NOMINAL
    """Type of velocity profile."""

    velocity_kph: float = 0.0
    """Velocity value in kph."""

    def __post_init__(self):
        """Validate truck_id is 1 for velocity events."""
        if self.truck_id != 1:
            raise ValueError(f"VelocityEvent only applies to Truck #1, got {self.truck_id}")


@dataclass
class IdentificationLossEvent(ScenarioEvent):
    """Image identification loss or resume event for followers."""

    is_loss: bool = False
    """True = Loss event, False = Resume event."""

    loss_type: Optional[LossType] = None
    """Loss type (only set if is_loss=True)."""

    duration_s: Optional[float] = None
    """Duration from loss to resume (only set if is_loss=True)."""

    def __post_init__(self):
        """Validate truck_id is 2 or 3."""
        if self.truck_id not in [2, 3]:
            raise ValueError(
                f"IdentificationLossEvent applies to Truck #2 or #3, got {self.truck_id}"
            )
        if self.is_loss and self.loss_type is None:
            raise ValueError("Loss events must have loss_type set")
        if self.is_loss and self.duration_s is None:
            raise ValueError("Loss events must have duration_s set")
        if not self.is_loss and self.duration_s is not None:
            raise ValueError("Resume events should not have duration_s")


@dataclass
class FORTEvent(ScenarioEvent):
    """Emergency stop (FORT) event for leader."""

    def __post_init__(self):
        """Validate truck_id is 1 for FORT events."""
        if self.truck_id != 1:
            raise ValueError(f"FORTEvent only applies to Truck #1, got {self.truck_id}")


# ============================================================================
# Composite Event Pairs
# ============================================================================

@dataclass
class LossResumePair:
    """A logical pair of Loss and Resume events."""

    loss_event: IdentificationLossEvent
    """The Loss event at time T."""

    resume_event: IdentificationLossEvent
    """The Resume event at time T + duration."""

    def __post_init__(self):
        """Validate pair consistency."""
        if not self.loss_event.is_loss:
            raise ValueError("First event must be a Loss event")
        if self.resume_event.is_loss:
            raise ValueError("Second event must be a Resume event")
        if self.loss_event.truck_id != self.resume_event.truck_id:
            raise ValueError("Loss and Resume must affect the same truck")

        # Calculate expected resume timestamp
        expected_resume_t = self.loss_event.timestamp_s + self.loss_event.duration_s
        if abs(self.resume_event.timestamp_s - expected_resume_t) > 0.1:
            raise ValueError(
                f"Resume at {self.resume_event.timestamp_s} != "
                f"Loss {self.loss_event.timestamp_s} + duration {self.loss_event.duration_s}"
            )


# ============================================================================
# CSV Output Row
# ============================================================================

@dataclass
class CSVRow:
    """A single row in the scenario CSV output."""

    time_s: float
    """Timestamp in seconds."""

    truck1_velocity_kph: Optional[float] = None
    """Leader velocity (Truck #1 only)."""

    truck1_event: Optional[str] = None
    """Leader event: "FORT activated" or None."""

    truck2_image_event: Optional[str] = None
    """Truck #2 image event: "Loss" or "Resume" or None."""

    truck3_image_event: Optional[str] = None
    """Truck #3 image event: "Loss" or "Resume" or None."""

    notes: str = ""
    """Optional notes."""

    def to_csv_row(self) -> str:
        """Format as CSV line (without newline)."""
        return ",".join([
            f"{self.time_s:.0f}",
            f"{self.truck1_velocity_kph:.2f}" if self.truck1_velocity_kph is not None else "",  # 2 decimals
            self.truck1_event or "",
            self.truck2_image_event or "",
            self.truck3_image_event or "",
            self.notes,
        ])


# ============================================================================
# Scenario Metadata
# ============================================================================

@dataclass
class ScenarioMetadata:
    """Metadata for a generated scenario."""

    name: str
    """Scenario name (filename without .csv, e.g., '3T_hV_mG_idL2qs_1ES')."""

    description: str
    """Human-readable description."""

    generated_at: datetime
    """Timestamp when scenario was generated."""

    seed: Optional[int] = None
    """Random seed used (for reproducibility)."""

    def validate_name_length(self) -> bool:
        """Ensure name <= 30 characters."""
        if len(self.name) > 30:
            raise ValueError(f"Scenario name '{self.name}' exceeds 30 characters")
        return True


# ============================================================================
# Scenario
# ============================================================================

@dataclass
class Scenario:
    """A complete generated convoy scenario."""

    metadata: ScenarioMetadata
    """Scenario metadata and name."""

    truck_count: int
    """Number of trucks (2 or 3)."""

    scenario_duration_s: float
    """Total scenario duration in seconds."""

    velocity_type: VelocityType
    """Type of velocity profile (exactly 1)."""

    gap_type: GapType
    """Type of initial gap configuration (exactly 1)."""

    initial_gaps: List[float]
    """Initial gaps between trucks."""

    velocity_events: List[VelocityEvent] = field(default_factory=list)
    """Velocity change events."""

    loss_resume_pairs: List[LossResumePair] = field(default_factory=list)
    """Identification loss/resume event pairs (0 to N)."""

    fort_event: Optional[FORTEvent] = None
    """Emergency stop event (0 or 1, must be last)."""

    csv_rows: List[CSVRow] = field(default_factory=list)
    """Computed CSV output rows."""

    def get_all_events(self) -> List[ScenarioEvent]:
        """
        Return all events in chronological order.

        Returns:
            List of all events (velocity, loss/resume, FORT) sorted by timestamp.
        """
        all_events: List[ScenarioEvent] = []

        # Add velocity events
        all_events.extend(self.velocity_events)

        # Add loss/resume events
        for pair in self.loss_resume_pairs:
            all_events.append(pair.loss_event)
            all_events.append(pair.resume_event)

        # Add FORT event
        if self.fort_event:
            all_events.append(self.fort_event)

        # Sort by timestamp
        all_events.sort(key=lambda e: e.timestamp_s)

        return all_events

    def validate(self) -> bool:
        """
        Validate scenario constraints.

        Raises:
            ValueError: If any constraint is violated.
        """
        # Truck count
        if self.truck_count not in [2, 3]:
            raise ValueError(f"truck_count must be 2 or 3, got {self.truck_count}")

        # Duration
        if self.scenario_duration_s <= 0:
            raise ValueError(f"scenario_duration_s must be positive, got {self.scenario_duration_s}")

        # Initial gaps
        if len(self.initial_gaps) != self.truck_count - 1:
            raise ValueError(
                f"initial_gaps must have {self.truck_count - 1} values, got {len(self.initial_gaps)}"
            )

        # Event timestamps within range
        for event in self.get_all_events():
            event.validate_timestamp(self.scenario_duration_s)

        # Events ordered by timestamp
        events = self.get_all_events()
        for i in range(1, len(events)):
            if events[i].timestamp_s < events[i-1].timestamp_s:
                raise ValueError(f"Events not in chronological order at index {i}")

        # FORT must be last event
        if self.fort_event:
            all_events = self.get_all_events()
            if all_events[-1] != self.fort_event:
                raise ValueError("FORT event must be the last event in scenario")

        # Metadata
        self.metadata.validate_name_length()

        return True

    def loss_event_count(self) -> int:
        """Return total number of identification loss events."""
        return len(self.loss_resume_pairs)
