"""
events.py — Event creation and composition helpers

Provides utilities for creating velocity profiles, loss/resume pairs, and event sequences.
"""

import math
import random
from typing import List, Tuple
from models import (
    VelocityEvent,
    IdentificationLossEvent,
    LossResumePair,
    LossType,
    VelocityType,
    FORTEvent,
)


class VelocityProfile:
    """
    A velocity profile for Truck #1 leader.

    Represents the velocity over time as a list of (timestamp, velocity) points.
    ConvoySIM will interpolate between points.
    """

    def __init__(
        self,
        velocity_type: VelocityType,
        scenario_duration_s: float,
        max_velocity_kph: float = 60.0,
        max_acceleration_mps2: float = 10.0,
    ):
        """
        Initialize velocity profile.

        Args:
            velocity_type: Type of velocity profile to generate
            scenario_duration_s: Total scenario duration in seconds
            max_velocity_kph: Hard ceiling for all velocity waypoints (kph).
                All generated velocities are capped at this value.
            max_acceleration_mps2: Maximum positive acceleration rate (m/s²).
                Upward velocity changes are smoothed to never exceed this rate.
                Default 10.0 m/s² is effectively unconstrained for most profiles.
        """
        self.velocity_type = velocity_type
        self.scenario_duration_s = scenario_duration_s
        self.max_velocity_kph = max_velocity_kph
        self.max_acceleration_mps2 = max_acceleration_mps2
        self.points: List[Tuple[float, float]] = []  # (timestamp, kph)

    @staticmethod
    def _clamp_velocity(velocity_kph: float, min_kph: float, max_kph: float) -> float:
        """
        Clamp velocity to safe range.

        Args:
            velocity_kph: Velocity to clamp
            min_kph: Minimum velocity
            max_kph: Maximum velocity

        Returns:
            Clamped velocity
        """
        return max(min_kph, min(max_kph, velocity_kph))

    def _calc_ramp_time(self, target_kph: float) -> float:
        """
        Calculate time needed to accelerate from 0 to target_kph at max_acceleration_mps2.

        Returns the ceiling integer seconds so that the whole-second CSV timestamp
        never causes the effective acceleration to exceed max_acceleration_mps2.
        e.g. raw=3.07 s → ceil → 4 s: actual accel = v/3.6/4 ≤ max ✓

        Args:
            target_kph: Target velocity in kph

        Returns:
            Ramp duration in seconds (integer-valued float, always ≥ raw minimum)
        """
        target_mps = target_kph / 3.6
        raw_time = target_mps / self.max_acceleration_mps2
        return float(math.ceil(raw_time))

    def _generate_sample_times(self, num_samples: int) -> List[float]:
        """
        Generate evenly-spaced sample timestamps.

        Args:
            num_samples: Number of samples to generate

        Returns:
            List of timestamps from 0 to scenario_duration_s
        """
        if num_samples <= 1:
            return [0.0, self.scenario_duration_s]

        step = self.scenario_duration_s / (num_samples - 1)
        times = [i * step for i in range(num_samples)]
        # Pin last point exactly to avoid floating-point drift
        # (e.g. 119.99999999999999 instead of 120.0)
        times[-1] = self.scenario_duration_s
        return times

    def _apply_constraints(self) -> None:
        """
        Post-process self.points to enforce velocity cap and acceleration limit.

        Two passes:
        1. Cap every velocity at self.max_velocity_kph.
        2. Forward pass: if consecutive velocity increase exceeds
           max_acceleration_mps2 * dt * 3.6 kph, clamp it.
           Deceleration is not limited (hard-brake profiles need free decel).
        """
        if not self.points:
            return

        # Pass 1: cap all velocities
        self.points = [
            (t, min(v, self.max_velocity_kph)) for t, v in self.points
        ]

        # Pass 2: limit positive acceleration
        for i in range(1, len(self.points)):
            t_prev, v_prev = self.points[i - 1]
            t_curr, v_curr = self.points[i]
            dt = t_curr - t_prev
            if dt > 0:
                max_dv_kph = self.max_acceleration_mps2 * dt * 3.6
                if v_curr - v_prev > max_dv_kph:
                    v_curr = v_prev + max_dv_kph
                    self.points[i] = (t_curr, v_curr)

    def generate_nominal(self, nominal_kph: float = 60.0) -> "VelocityProfile":
        """
        Generate nominal (constant) velocity profile.

        Args:
            nominal_kph: Constant velocity in kph (default 60)

        Returns:
            Self for chaining
        """
        # Start from rest and ramp up to nominal, then hold constant
        ramp_time_s = self._calc_ramp_time(nominal_kph)
        self.points = [
            (0.0, 0.0),
            (ramp_time_s, nominal_kph),
            (self.scenario_duration_s, nominal_kph),
        ]
        self._apply_constraints()
        return self

    def generate_medium_variable(
        self, nominal_kph: float = 60.0, variation_percent: float = 10.0
    ) -> "VelocityProfile":
        """
        Generate medium variable velocity profile.

        Velocity varies by ±variation_percent around nominal using a random walk.
        Creates smooth variations in velocity around the nominal value.

        Args:
            nominal_kph: Nominal velocity in kph
            variation_percent: Variation range as percentage (e.g., 10.0 for ±10%)

        Returns:
            Self for chaining
        """
        # Random walk: smooth variations around nominal, starting from rest
        num_samples = random.randint(8, 12)  # 8-12 points for smooth profile
        sample_times = self._generate_sample_times(num_samples)

        min_kph = nominal_kph * (1 - variation_percent / 100.0)
        max_kph = nominal_kph * (1 + variation_percent / 100.0)

        # Prepend startup ramp: (0, 0) → (ramp_time, nominal)
        ramp_time_s = self._calc_ramp_time(nominal_kph)
        velocity = nominal_kph
        self.points = [(0.0, 0.0), (ramp_time_s, velocity)]

        # Add random-walk points after the ramp (skip sample_times[0]=0.0)
        for i, t in enumerate(sample_times[1:], 1):
            if t <= ramp_time_s:
                continue  # Skip any sample times within the ramp period
            # Random step: ±10% of nominal per step (larger steps for visible variation)
            step = random.uniform(-0.10 * nominal_kph, 0.10 * nominal_kph)
            velocity = velocity + step
            velocity = self._clamp_velocity(velocity, min_kph, max_kph)
            self.points.append((t, velocity))

        self._apply_constraints()
        return self

    def generate_high_variable(
        self, min_kph: float = 40.0, max_kph: float = 80.0
    ) -> "VelocityProfile":
        """
        Generate high variable velocity profile.

        Velocity randomly jumps within [min_kph, max_kph] range, creating
        frequent rapid changes in speed.

        Args:
            min_kph: Minimum velocity in kph
            max_kph: Maximum velocity in kph

        Returns:
            Self for chaining
        """
        # Random jumps across full range, starting from rest
        num_samples = random.randint(6, 10)  # Fewer samples for "choppier" feel
        sample_times = self._generate_sample_times(num_samples)

        # Prepend startup ramp: (0, 0) → (ramp_time, first_velocity)
        first_velocity = random.uniform(min_kph, max_kph)
        ramp_time_s = self._calc_ramp_time(first_velocity)
        self.points = [(0.0, 0.0), (ramp_time_s, first_velocity)]

        # Add random-jump points after the ramp (skip sample_times[0]=0.0)
        for t in sample_times[1:]:
            if t <= ramp_time_s:
                continue  # Skip any sample times within the ramp period
            velocity = random.uniform(min_kph, max_kph)
            self.points.append((t, velocity))

        self._apply_constraints()
        return self

    def generate_hard_brake(
        self,
        nominal_kph: float = 60.0,
        brake_time_s: float = None,
        brake_target_kph: float = 20.0,
    ) -> "VelocityProfile":
        """
        Generate hard brake velocity profile.

        Creates realistic sharp deceleration (~2 m/s²) by placing two velocity events
        close together in time. For example: 60 kph → 20 kph over ~5 seconds gives
        (40 kph / 5 s ≈ 2.2 m/s²).

        Args:
            nominal_kph: Velocity before braking
            brake_time_s: Time of brake event (None = random in [0.3*duration, 0.8*duration])
            brake_target_kph: Velocity after braking

        Returns:
            Self for chaining
        """
        if brake_time_s is None:
            # Randomize brake time: somewhere in middle/late portion of scenario
            brake_time_s = random.uniform(
                self.scenario_duration_s * 0.3, self.scenario_duration_s * 0.8
            )

        # Calculate deceleration time to achieve ~2 m/s²
        # delta_v (m/s) = (nominal_kph - brake_target_kph) / 3.6
        # time = delta_v / 2.0
        delta_v_ms = (nominal_kph - brake_target_kph) / 3.6
        decel_time_s = max(0.5, delta_v_ms / 2.0)  # At least 0.5s, aim for 2 m/s² deceleration

        # Ensure brake start time doesn't go negative
        brake_start_time = max(0.0, brake_time_s - decel_time_s)

        # Prepend startup ramp: (0, 0) → (ramp_time, nominal)
        ramp_time_s = self._calc_ramp_time(nominal_kph)
        if ramp_time_s < brake_start_time:
            self.points = [
                (0.0, 0.0),
                (ramp_time_s, nominal_kph),   # Ramp complete — at full speed
                (brake_start_time, nominal_kph),  # Hold nominal until decel starts
                (brake_time_s, brake_target_kph),  # Complete deceleration
                (self.scenario_duration_s, brake_target_kph),  # Hold at target until end
            ]
        else:
            # Edge case: ramp duration ≥ brake_start (very slow acceleration or early brake).
            # Ramp directly to brake_start; the profile goes 0 → nominal over brake_start time.
            self.points = [
                (0.0, 0.0),
                (brake_start_time, nominal_kph),
                (brake_time_s, brake_target_kph),
                (self.scenario_duration_s, brake_target_kph),
            ]
        self._apply_constraints()
        return self

    def to_velocity_events(self) -> List[VelocityEvent]:
        """
        Convert profile points to VelocityEvent list.

        Every profile point is emitted — the simulator needs all waypoints
        to interpolate the velocity curve correctly.  No significance filter
        is applied; filtering at this layer caused variable profiles to appear
        as constant speed (BUG-05 fix).
        """
        if not self.points:
            return []

        return [
            VelocityEvent(
                timestamp_s=timestamp_s,
                truck_id=1,
                velocity_type=self.velocity_type,
                velocity_kph=velocity_kph,
                notes=f"Velocity ({velocity_kph:.2f} kph)",
            )
            for timestamp_s, velocity_kph in self.points
        ]


def create_loss_resume_pair(
    truck_id: int,
    loss_timestamp_s: float,
    loss_type: LossType,
) -> LossResumePair:
    """
    Create a loss/resume event pair.

    ENH-06: Loss durations now randomized within type-specific ranges instead of fixed.

    Args:
        truck_id: Truck affected (2 or 3)
        loss_timestamp_s: Time of loss event
        loss_type: Type of loss (determines resume duration range)

    Returns:
        LossResumePair with calculated resume timestamp
    """
    # ENH-06: Determine resume duration based on loss type with randomized ranges
    if loss_type == LossType.QUICK_SHORT:
        # Quick-Short: 0-15 seconds
        duration_s = random.uniform(0, 15.0)
    elif loss_type == LossType.SLOW:
        # Slow: 40-60 seconds
        duration_s = random.uniform(40.0, 60.0)
    elif loss_type == LossType.FREQUENT_VARIANT:
        # Frequent Variant: mix of medium durations (15-40 seconds)
        # Placeholder for variant behavior
        duration_s = random.uniform(15.0, 40.0)
    else:
        raise ValueError(f"Unknown loss_type: {loss_type}")

    loss_event = IdentificationLossEvent(
        timestamp_s=loss_timestamp_s,
        truck_id=truck_id,
        is_loss=True,
        loss_type=loss_type,
        duration_s=duration_s,
        notes=f"Image identification loss ({loss_type.value})",
    )

    resume_event = IdentificationLossEvent(
        timestamp_s=loss_timestamp_s + duration_s,
        truck_id=truck_id,
        is_loss=False,
        notes=f"Resume tracking (after {duration_s:.1f}s)",
    )

    return LossResumePair(loss_event, resume_event)


def create_fort_event(
    timestamp_s: float,
    notes: str = "Emergency stop",
) -> FORTEvent:
    """
    Create a FORT (emergency stop) event.

    Args:
        timestamp_s: Time of FORT event
        notes: Optional description

    Returns:
        FORTEvent
    """
    return FORTEvent(
        timestamp_s=timestamp_s,
        truck_id=1,
        notes=notes,
    )
