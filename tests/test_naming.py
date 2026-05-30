"""
test_naming.py — Scenario naming and parsing tests

Tests scenario name encoding, decoding, and round-trip conversion.
"""

import unittest
from models import VelocityType, GapType, LossType
from naming import ScenarioNameEncoder, ScenarioNameParser


class TestScenarioNameEncoding(unittest.TestCase):
    """Test encoding scenario attributes into names."""

    def test_encode_truck_count_2(self):
        """Test encoding truck count 2."""
        result = ScenarioNameEncoder.encode_truck_count(2)
        self.assertEqual(result, "2T")

    def test_encode_truck_count_3(self):
        """Test encoding truck count 3."""
        result = ScenarioNameEncoder.encode_truck_count(3)
        self.assertEqual(result, "3T")

    def test_encode_truck_count_invalid(self):
        """Test encoding invalid truck count."""
        with self.assertRaises(ValueError):
            ScenarioNameEncoder.encode_truck_count(4)
        with self.assertRaises(ValueError):
            ScenarioNameEncoder.encode_truck_count(1)

    def test_encode_all_velocity_types(self):
        """Test encoding all velocity types."""
        expected = {
            VelocityType.NOMINAL: "nV",
            VelocityType.MEDIUM_VARIABLE: "mV",
            VelocityType.HIGH_VARIABLE: "hV",
            VelocityType.HARD_BRAKE: "hB",
        }

        for velocity_type, expected_code in expected.items():
            result = ScenarioNameEncoder.encode_velocity_type(velocity_type)
            self.assertEqual(result, expected_code)

    def test_encode_all_gap_types(self):
        """Test encoding all gap types."""
        expected = {
            GapType.SMALL: "sG",
            GapType.MEDIUM: "mG",
            GapType.BIG: "bG",
            GapType.VARIANT: "vG",
        }

        for gap_type, expected_code in expected.items():
            result = ScenarioNameEncoder.encode_gap_type(gap_type)
            self.assertEqual(result, expected_code)

    def test_loss_type_codes(self):
        """Test that loss type codes are correctly defined."""
        expected = {
            LossType.QUICK_SHORT: "qs",
            LossType.SLOW: "sl",
            LossType.FREQUENT_VARIANT: "fv",
        }

        for loss_type, expected_code in expected.items():
            # Verify the codes are in the encoder's LOSS_CODES dict
            actual_code = ScenarioNameEncoder.LOSS_CODES.get(loss_type)
            self.assertEqual(actual_code, expected_code)

    def test_encode_loss_events_empty(self):
        """Test encoding with no loss events."""
        result = ScenarioNameEncoder.encode_loss_events([])
        self.assertEqual(result, "none")

    def test_encode_loss_events_single_quick(self):
        """Test encoding single QUICK_SHORT loss."""
        result = ScenarioNameEncoder.encode_loss_events([LossType.QUICK_SHORT])
        self.assertEqual(result, "idL1qs")

    def test_encode_loss_events_multiple_same_type(self):
        """Test encoding multiple losses of same type."""
        result = ScenarioNameEncoder.encode_loss_events(
            [LossType.SLOW, LossType.SLOW]
        )
        self.assertEqual(result, "idL2sl")

    def test_encode_loss_events_multiple_different_types(self):
        """Test encoding multiple losses of different types."""
        # When multiple types, encoder uses first type (current behavior)
        result = ScenarioNameEncoder.encode_loss_events(
            [LossType.QUICK_SHORT, LossType.SLOW]
        )
        self.assertEqual(result, "idL2qs")

    def test_encode_fort_true(self):
        """Test encoding FORT presence."""
        result = ScenarioNameEncoder.encode_fort(True)
        self.assertEqual(result, "1ES")

    def test_encode_fort_false(self):
        """Test encoding FORT absence."""
        result = ScenarioNameEncoder.encode_fort(False)
        self.assertEqual(result, "0ES")


class TestScenarioNameGeneration(unittest.TestCase):
    """Test complete name generation."""

    def test_generate_name_simple(self):
        """Test generating a simple scenario name."""
        name = ScenarioNameEncoder.generate_name(
            truck_count=3,
            velocity_type=VelocityType.NOMINAL,
            gap_type=GapType.SMALL,
            loss_types=[],
            has_fort=False,
        )

        self.assertEqual(name, "3T_nV_sG_none_0ES")

    def test_generate_name_with_loss(self):
        """Test generating name with loss events."""
        name = ScenarioNameEncoder.generate_name(
            truck_count=2,
            velocity_type=VelocityType.HIGH_VARIABLE,
            gap_type=GapType.MEDIUM,
            loss_types=[LossType.QUICK_SHORT],
            has_fort=False,
        )

        self.assertEqual(name, "2T_hV_mG_idL1qs_0ES")

    def test_generate_name_with_fort(self):
        """Test generating name with FORT event."""
        name = ScenarioNameEncoder.generate_name(
            truck_count=3,
            velocity_type=VelocityType.HARD_BRAKE,
            gap_type=GapType.BIG,
            loss_types=[LossType.SLOW],
            has_fort=True,
        )

        self.assertEqual(name, "3T_hB_bG_idL1sl_1ES")

    def test_generate_name_all_combinations(self):
        """Test that name generation works for multiple valid combinations."""
        velocity_types = list(VelocityType)
        gap_types = list(GapType)

        count = 0
        for v_type in velocity_types:
            for g_type in gap_types:
                name = ScenarioNameEncoder.generate_name(
                    truck_count=2,
                    velocity_type=v_type,
                    gap_type=g_type,
                    loss_types=[],
                    has_fort=False,
                )

                # Should be valid format
                self.assertIsNotNone(name)
                self.assertLessEqual(len(name), 30)
                count += 1

        self.assertEqual(count, 16)  # 4 velocity types × 4 gap types

    def test_name_length_constraint(self):
        """Test that generated names don't exceed 30 characters."""
        # Most combinations should be short enough
        # The longest would be something like: 2T_hB_vG_idL99fv_1ES = 21 chars (still OK)

        name = ScenarioNameEncoder.generate_name(
            truck_count=2,
            velocity_type=VelocityType.HARD_BRAKE,
            gap_type=GapType.VARIANT,
            loss_types=[LossType.FREQUENT_VARIANT] * 10,  # Many losses
            has_fort=True,
        )

        self.assertLessEqual(len(name), 30, f"Name too long: {name}")


class TestScenarioNameParsing(unittest.TestCase):
    """Test parsing names back to attributes."""

    def test_parse_name_simple(self):
        """Test parsing a simple scenario name."""
        truck_count, velocity_type, gap_type, loss_types, has_fort = (
            ScenarioNameParser.parse_name("3T_nV_sG_none_0ES")
        )

        self.assertEqual(truck_count, 3)
        self.assertEqual(velocity_type, VelocityType.NOMINAL)
        self.assertEqual(gap_type, GapType.SMALL)
        self.assertEqual(loss_types, [])
        self.assertFalse(has_fort)

    def test_parse_name_with_loss(self):
        """Test parsing name with loss events."""
        truck_count, velocity_type, gap_type, loss_types, has_fort = (
            ScenarioNameParser.parse_name("2T_hV_mG_idL1qs_0ES")
        )

        self.assertEqual(truck_count, 2)
        self.assertEqual(velocity_type, VelocityType.HIGH_VARIABLE)
        self.assertEqual(gap_type, GapType.MEDIUM)
        self.assertEqual(loss_types, [LossType.QUICK_SHORT])
        self.assertFalse(has_fort)

    def test_parse_name_with_fort(self):
        """Test parsing name with FORT event."""
        truck_count, velocity_type, gap_type, loss_types, has_fort = (
            ScenarioNameParser.parse_name("3T_hB_bG_idL1sl_1ES")
        )

        self.assertEqual(truck_count, 3)
        self.assertEqual(velocity_type, VelocityType.HARD_BRAKE)
        self.assertEqual(gap_type, GapType.BIG)
        self.assertEqual(loss_types, [LossType.SLOW])
        self.assertTrue(has_fort)

    def test_parse_name_multiple_losses(self):
        """Test parsing name with multiple loss events."""
        truck_count, velocity_type, gap_type, loss_types, has_fort = (
            ScenarioNameParser.parse_name("2T_mV_vG_idL3fv_1ES")
        )

        self.assertEqual(truck_count, 2)
        self.assertEqual(loss_types, [LossType.FREQUENT_VARIANT] * 3)
        self.assertTrue(has_fort)

    def test_parse_name_with_csv_extension(self):
        """Test parsing name with .csv extension."""
        truck_count, velocity_type, gap_type, loss_types, has_fort = (
            ScenarioNameParser.parse_name("3T_nV_sG_none_0ES.csv")
        )

        self.assertEqual(truck_count, 3)
        self.assertEqual(velocity_type, VelocityType.NOMINAL)

    def test_parse_name_invalid_format(self):
        """Test parsing invalid name format."""
        with self.assertRaises(ValueError):
            ScenarioNameParser.parse_name("invalid_name")

    def test_parse_name_invalid_truck_count(self):
        """Test parsing name with invalid truck count."""
        with self.assertRaises(ValueError):
            ScenarioNameParser.parse_name("4T_nV_sG_none_0ES")

    def test_parse_name_unknown_velocity_code(self):
        """Test parsing name with unknown velocity code."""
        with self.assertRaises(ValueError):
            ScenarioNameParser.parse_name("2T_XX_sG_none_0ES")

    def test_parse_name_unknown_gap_code(self):
        """Test parsing name with unknown gap code."""
        with self.assertRaises(ValueError):
            ScenarioNameParser.parse_name("2T_nV_XX_none_0ES")

    def test_parse_name_unknown_loss_code(self):
        """Test parsing name with unknown loss code."""
        with self.assertRaises(ValueError):
            ScenarioNameParser.parse_name("2T_nV_sG_idL2XX_0ES")

    def test_parse_to_dict(self):
        """Test parsing name to dictionary."""
        result = ScenarioNameParser.parse_to_dict("3T_hV_mG_idL2qs_1ES")

        self.assertEqual(result["truck_count"], 3)
        self.assertEqual(result["velocity_type"], VelocityType.HIGH_VARIABLE)
        self.assertEqual(result["gap_type"], GapType.MEDIUM)
        self.assertEqual(result["loss_count"], 2)
        self.assertEqual(result["loss_types"], [LossType.QUICK_SHORT] * 2)
        self.assertTrue(result["has_fort"])


class TestRoundTripConversion(unittest.TestCase):
    """Test encoding and then decoding (round-trip)."""

    def test_roundtrip_simple(self):
        """Test round-trip conversion for simple scenario."""
        original = (2, VelocityType.NOMINAL, GapType.SMALL, [], False)

        # Encode
        name = ScenarioNameEncoder.generate_name(*original)

        # Decode
        decoded = ScenarioNameParser.parse_name(name)

        self.assertEqual(original, decoded)

    def test_roundtrip_with_loss(self):
        """Test round-trip with loss events."""
        original = (
            3,
            VelocityType.HIGH_VARIABLE,
            GapType.BIG,
            [LossType.QUICK_SHORT, LossType.QUICK_SHORT],
            True,
        )

        name = ScenarioNameEncoder.generate_name(*original)
        decoded = ScenarioNameParser.parse_name(name)

        self.assertEqual(original, decoded)

    def test_roundtrip_all_velocity_types(self):
        """Test round-trip for all velocity types."""
        for velocity_type in VelocityType:
            original = (
                2,
                velocity_type,
                GapType.SMALL,
                [],
                False,
            )

            name = ScenarioNameEncoder.generate_name(*original)
            decoded = ScenarioNameParser.parse_name(name)

            self.assertEqual(original, decoded)

    def test_roundtrip_all_gap_types(self):
        """Test round-trip for all gap types."""
        for gap_type in GapType:
            original = (
                2,
                VelocityType.NOMINAL,
                gap_type,
                [],
                False,
            )

            name = ScenarioNameEncoder.generate_name(*original)
            decoded = ScenarioNameParser.parse_name(name)

            self.assertEqual(original, decoded)

    def test_roundtrip_all_loss_types(self):
        """Test round-trip for all loss types."""
        for loss_type in LossType:
            original = (
                2,
                VelocityType.NOMINAL,
                GapType.SMALL,
                [loss_type],
                False,
            )

            name = ScenarioNameEncoder.generate_name(*original)
            decoded = ScenarioNameParser.parse_name(name)

            self.assertEqual(original, decoded)

    def test_roundtrip_with_csv_extension(self):
        """Test round-trip with .csv extension."""
        original = (2, VelocityType.NOMINAL, GapType.SMALL, [], False)

        name = ScenarioNameEncoder.generate_name(*original) + ".csv"
        decoded = ScenarioNameParser.parse_name(name)

        self.assertEqual(original, decoded)


class TestNameConstraints(unittest.TestCase):
    """Test name constraints and validations."""

    def test_name_length_is_reasonable(self):
        """Test that all generated names are reasonable length."""
        for trucks in [2, 3]:
            for velocity in VelocityType:
                for gaps in GapType:
                    for losses in [[], [LossType.QUICK_SHORT]]:
                        for fort in [True, False]:
                            name = ScenarioNameEncoder.generate_name(
                                trucks, velocity, gaps, losses, fort
                            )

                            self.assertLessEqual(
                                len(name),
                                30,
                                f"Name too long: {name}",
                            )
                            self.assertGreater(len(name), 0)

    def test_name_format_consistency(self):
        """Test that all generated names follow consistent format."""
        import re

        for trucks in [2, 3]:
            for velocity in VelocityType:
                for gaps in GapType:
                    name = ScenarioNameEncoder.generate_name(
                        trucks, velocity, gaps, [], False
                    )

                    # Should match pattern: {digit}T_{2 chars}_{2 chars}_{...}_{0-1 ES}
                    pattern = r"^[23]T_[a-zA-Z]{2}_[a-zA-Z]{2}_(idL\d+[a-z]+|none)_[01]ES$"
                    self.assertIsNotNone(
                        re.match(pattern, name),
                        f"Name doesn't match format: {name}",
                    )


if __name__ == "__main__":
    unittest.main()
