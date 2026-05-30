"""
test_events.py — Unit tests for velocity profile generation

Tests VelocityProfile class and event creation helpers.
"""

import unittest
from models import VelocityType, LossType, LossResumePair
from events import VelocityProfile, create_loss_resume_pair, create_fort_event


class TestVelocityProfileNominal(unittest.TestCase):
    """Test nominal (constant) velocity profile."""

    def test_generate_nominal_basic(self):
        """Nominal profile should start from rest, ramp up, then hold constant."""
        profile = VelocityProfile(VelocityType.NOMINAL, 120.0)
        profile.generate_nominal(nominal_kph=60.0)

        # Now 3 points: (0, 0), (ramp_time, 60), (120, 60)
        self.assertEqual(len(profile.points), 3)
        self.assertEqual(profile.points[0], (0.0, 0.0))   # start at rest
        self.assertEqual(profile.points[1][1], 60.0)       # at nominal after ramp
        self.assertEqual(profile.points[2], (120.0, 60.0)) # hold at end

    def test_generate_nominal_different_duration(self):
        """Nominal profile should work with different durations."""
        profile = VelocityProfile(VelocityType.NOMINAL, 300.0, max_velocity_kph=75.0)
        profile.generate_nominal(nominal_kph=75.0)

        self.assertEqual(profile.points[0], (0.0, 0.0))         # start at rest
        self.assertAlmostEqual(profile.points[1][1], 75.0)    # at nominal after ramp
        self.assertAlmostEqual(profile.points[-1][0], 300.0)
        self.assertAlmostEqual(profile.points[-1][1], 75.0)

    def test_to_velocity_events(self):
        """Nominal profile should convert to VelocityEvent list."""
        profile = VelocityProfile(VelocityType.NOMINAL, 120.0)
        profile.generate_nominal(nominal_kph=60.0)

        events = profile.to_velocity_events()
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].timestamp_s, 0.0)
        self.assertEqual(events[0].velocity_kph, 0.0)   # start at rest
        self.assertEqual(events[1].velocity_kph, 60.0)  # at nominal after ramp
        self.assertEqual(events[-1].timestamp_s, 120.0)


class TestVelocityProfileMediumVariable(unittest.TestCase):
    """Test medium variable velocity profile."""

    def test_generate_medium_variable_count(self):
        """Medium variable should generate 9-13 sample points (8-12 + ramp start)."""
        for _ in range(10):  # Try multiple times due to randomness
            profile = VelocityProfile(VelocityType.MEDIUM_VARIABLE, 120.0)
            profile.generate_medium_variable(nominal_kph=60.0)

            # 2 ramp points + (num_samples - 1) walk points = num_samples + 1
            self.assertGreaterEqual(len(profile.points), 9)
            self.assertLessEqual(len(profile.points), 13)

    def test_generate_medium_variable_range(self):
        """Medium variable velocities should stay within bounds after the ramp."""
        profile = VelocityProfile(VelocityType.MEDIUM_VARIABLE, 120.0)
        profile.generate_medium_variable(nominal_kph=60.0, variation_percent=10.0)

        # First point is always (0.0, 0.0) — startup at rest
        self.assertEqual(profile.points[0], (0.0, 0.0))

        min_allowed = 60.0 * 0.8  # 48 kph
        max_allowed = 60.0 * 1.2  # 72 kph

        # All points after the rest point should be in the variation band
        for t, v in profile.points[1:]:
            self.assertGreaterEqual(v, min_allowed - 0.1, f"Velocity {v} below min at t={t}")
            self.assertLessEqual(v, max_allowed + 0.1, f"Velocity {v} above max at t={t}")

    def test_generate_medium_variable_timestamps_monotonic(self):
        """Medium variable timestamps should be monotonically increasing."""
        profile = VelocityProfile(VelocityType.MEDIUM_VARIABLE, 120.0)
        profile.generate_medium_variable()

        times = [t for t, v in profile.points]
        self.assertEqual(times, sorted(times))
        self.assertEqual(times[0], 0.0)
        self.assertEqual(times[-1], 120.0)


class TestVelocityProfileHighVariable(unittest.TestCase):
    """Test high variable velocity profile."""

    def test_generate_high_variable_count(self):
        """High variable should generate 7-11 sample points (6-10 + ramp start)."""
        for _ in range(10):
            profile = VelocityProfile(VelocityType.HIGH_VARIABLE, 120.0)
            profile.generate_high_variable(min_kph=40.0, max_kph=80.0)

            # 2 ramp points + (num_samples - 1) random points = num_samples + 1
            self.assertGreaterEqual(len(profile.points), 7)
            self.assertLessEqual(len(profile.points), 11)

    def test_generate_high_variable_range(self):
        """High variable velocities should be within specified range after the ramp."""
        profile = VelocityProfile(VelocityType.HIGH_VARIABLE, 120.0)
        profile.generate_high_variable(min_kph=40.0, max_kph=80.0)

        # First point is always (0.0, 0.0) — startup at rest
        self.assertEqual(profile.points[0], (0.0, 0.0))

        # All points after rest should be in the specified range
        for t, v in profile.points[1:]:
            self.assertGreaterEqual(v, 39.9, f"Velocity {v} below min at t={t}")
            self.assertLessEqual(v, 80.1, f"Velocity {v} above max at t={t}")

    def test_generate_high_variable_timestamps_monotonic(self):
        """High variable timestamps should be monotonically increasing."""
        profile = VelocityProfile(VelocityType.HIGH_VARIABLE, 120.0)
        profile.generate_high_variable()

        times = [t for t, v in profile.points]
        self.assertEqual(times, sorted(times))


class TestVelocityProfileHardBrake(unittest.TestCase):
    """Test hard brake velocity profile."""

    def test_generate_hard_brake_with_explicit_time(self):
        """Hard brake with explicit brake time should start from rest, ramp, then brake sharply."""
        profile = VelocityProfile(VelocityType.HARD_BRAKE, 120.0)
        profile.generate_hard_brake(
            nominal_kph=60.0, brake_time_s=60.0, brake_target_kph=20.0
        )

        # Should have 5 points: (0,0), (ramp, nominal), (brake_start, nominal), (brake, target), (end, target)
        self.assertEqual(len(profile.points), 5)

        # First point at rest
        self.assertEqual(profile.points[0], (0.0, 0.0))

        # Second point at nominal (end of ramp)
        self.assertAlmostEqual(profile.points[1][1], 60.0)

        # Third point still at nominal (brake hasn't started)
        self.assertAlmostEqual(profile.points[2][1], 60.0)

        # Last two points at brake target
        self.assertEqual(profile.points[3][1], 20.0)
        self.assertEqual(profile.points[4][1], 20.0)

    def test_generate_hard_brake_random_time(self):
        """Hard brake with None brake time should randomize timing."""
        times = []
        for _ in range(20):
            profile = VelocityProfile(VelocityType.HARD_BRAKE, 120.0)
            profile.generate_hard_brake(nominal_kph=60.0, brake_time_s=None)
            # points[2] is brake_start_time (after ramp at points[1])
            brake_start = profile.points[2][0]
            times.append(brake_start)

        # Brake start times should be varied (at least some spread)
        self.assertGreater(max(times) - min(times), 10.0)

        # All should be in reasonable range (brake_time in [0.3*120, 0.8*120] minus decel_time)
        for t in times:
            self.assertGreater(t, 24.0)   # brake_time - decel_time > 0.3*120 - ~12s
            self.assertLess(t, 100.0)


class TestCreateLossResumePair(unittest.TestCase):
    """Test loss/resume pair creation."""

    def test_create_loss_resume_pair_quick_short(self):
        """Quick short loss should have randomized 0-15s duration (ENH-06)."""
        pair = create_loss_resume_pair(
            truck_id=2, loss_timestamp_s=30.0, loss_type=LossType.QUICK_SHORT
        )

        self.assertEqual(pair.loss_event.truck_id, 2)
        self.assertEqual(pair.loss_event.timestamp_s, 30.0)
        # ENH-06: Duration is now randomized in range [0, 15]
        self.assertGreaterEqual(pair.loss_event.duration_s, 0)
        self.assertLessEqual(pair.loss_event.duration_s, 15.0)

        self.assertEqual(pair.resume_event.truck_id, 2)
        # Resume time = loss time + duration
        expected_min_resume = 30.0 + 0
        expected_max_resume = 30.0 + 15.0
        self.assertGreaterEqual(pair.resume_event.timestamp_s, expected_min_resume)
        self.assertLessEqual(pair.resume_event.timestamp_s, expected_max_resume)

    def test_create_loss_resume_pair_slow(self):
        """Slow loss should have randomized 40-60s duration (ENH-06)."""
        pair = create_loss_resume_pair(
            truck_id=3, loss_timestamp_s=20.0, loss_type=LossType.SLOW
        )

        # ENH-06: Duration is now randomized in range [40, 60]
        self.assertGreaterEqual(pair.loss_event.duration_s, 40.0)
        self.assertLessEqual(pair.loss_event.duration_s, 60.0)
        # Resume time = loss time + duration
        expected_min_resume = 20.0 + 40.0
        expected_max_resume = 20.0 + 60.0
        self.assertGreaterEqual(pair.resume_event.timestamp_s, expected_min_resume)
        self.assertLessEqual(pair.resume_event.timestamp_s, expected_max_resume)

    def test_create_loss_resume_pair_validation(self):
        """Loss/resume pair should validate consistency (ENH-06: randomized durations)."""
        pair = create_loss_resume_pair(
            truck_id=2, loss_timestamp_s=30.0, loss_type=LossType.QUICK_SHORT
        )

        # Both should be in same truck
        self.assertEqual(pair.loss_event.truck_id, pair.resume_event.truck_id)

        # Resume time should be loss time + duration (account for random range)
        expected_resume = pair.loss_event.timestamp_s + pair.loss_event.duration_s
        self.assertAlmostEqual(pair.resume_event.timestamp_s, expected_resume)


class TestCreateFORTEvent(unittest.TestCase):
    """Test FORT event creation."""

    def test_create_fort_event(self):
        """FORT event should be created correctly."""
        fort = create_fort_event(timestamp_s=100.0)

        self.assertEqual(fort.timestamp_s, 100.0)
        self.assertEqual(fort.truck_id, 1)
        self.assertIn("Emergency", fort.notes)

    def test_create_fort_event_custom_notes(self):
        """FORT event should accept custom notes."""
        fort = create_fort_event(timestamp_s=100.0, notes="Custom FORT note")

        self.assertEqual(fort.notes, "Custom FORT note")


class TestVelocityProfileClampVelocity(unittest.TestCase):
    """Test velocity clamping utility."""

    def test_clamp_velocity_below_min(self):
        """Velocity below min should be clamped to min."""
        result = VelocityProfile._clamp_velocity(30.0, 40.0, 80.0)
        self.assertEqual(result, 40.0)

    def test_clamp_velocity_above_max(self):
        """Velocity above max should be clamped to max."""
        result = VelocityProfile._clamp_velocity(90.0, 40.0, 80.0)
        self.assertEqual(result, 80.0)

    def test_clamp_velocity_within_range(self):
        """Velocity within range should not be modified."""
        result = VelocityProfile._clamp_velocity(60.0, 40.0, 80.0)
        self.assertEqual(result, 60.0)


if __name__ == "__main__":
    unittest.main()
