"""
naming.py — Scenario naming and parsing

Handles encoding scenario attributes into names (e.g., 3T_hV_mG_idL2qs_1ES.csv)
and parsing names back to attributes.
"""

import re
from typing import Tuple, List, Optional
from models import VelocityType, GapType, LossType


class ScenarioNameEncoder:
    """Encodes scenario attributes into standardized names."""

    VELOCITY_CODES = {
        VelocityType.NOMINAL: "nV",
        VelocityType.MEDIUM_VARIABLE: "mV",
        VelocityType.HIGH_VARIABLE: "hV",
        VelocityType.HARD_BRAKE: "hB",
    }

    GAP_CODES = {
        GapType.SMALL: "sG",
        GapType.MEDIUM: "mG",
        GapType.BIG: "bG",
        GapType.VARIANT: "vG",
    }

    LOSS_CODES = {
        LossType.QUICK_SHORT: "qs",
        LossType.SLOW: "sl",
        LossType.FREQUENT_VARIANT: "fv",
    }

    @staticmethod
    def encode_truck_count(count: int) -> str:
        """Encode truck count (2 or 3) as '2T' or '3T'."""
        if count not in [2, 3]:
            raise ValueError(f"truck_count must be 2 or 3, got {count}")
        return f"{count}T"

    @staticmethod
    def encode_velocity_type(velocity_type: VelocityType) -> str:
        """Encode velocity type."""
        code = ScenarioNameEncoder.VELOCITY_CODES.get(velocity_type)
        if code is None:
            raise ValueError(f"Unknown velocity_type: {velocity_type}")
        return code

    @staticmethod
    def encode_gap_type(gap_type: GapType) -> str:
        """Encode gap type."""
        code = ScenarioNameEncoder.GAP_CODES.get(gap_type)
        if code is None:
            raise ValueError(f"Unknown gap_type: {gap_type}")
        return code

    @staticmethod
    def encode_loss_events(loss_types: List[LossType]) -> str:
        """
        Encode identification loss events.

        Args:
            loss_types: List of LossType values. Can be empty or contain duplicates.

        Returns:
            String like 'idL2qs' (2 quick-short losses) or 'none' if empty.
        """
        if not loss_types:
            return "none"

        count = len(loss_types)

        # For simple cases, use first loss type
        # TODO: Handle multiple different types (e.g., 'idL2qssl' for mixed)
        if len(set(loss_types)) == 1:
            loss_code = ScenarioNameEncoder.LOSS_CODES.get(loss_types[0])
            if loss_code is None:
                raise ValueError(f"Unknown loss_type: {loss_types[0]}")
            return f"idL{count}{loss_code}"
        else:
            # Multiple loss types: sort and concatenate
            # e.g., [QUICK, SLOW, QUICK] → 'idL2qssl' or similar
            # Placeholder: just use first type for now
            loss_code = ScenarioNameEncoder.LOSS_CODES.get(loss_types[0])
            return f"idL{count}{loss_code}"

    @staticmethod
    def encode_fort(has_fort: bool) -> str:
        """Encode FORT event presence."""
        return "1ES" if has_fort else "0ES"

    @staticmethod
    def generate_name(
        truck_count: int,
        velocity_type: VelocityType,
        gap_type: GapType,
        loss_types: List[LossType],
        has_fort: bool,
    ) -> str:
        """
        Generate scenario name from attributes.

        Format: <trucks>_<velocity>_<gaps>_<idLoss>_<FORT>

        Args:
            truck_count: 2 or 3
            velocity_type: One of VelocityType enum
            gap_type: One of GapType enum
            loss_types: List of loss types (can be empty)
            has_fort: Whether scenario includes FORT event

        Returns:
            Name string (e.g., '3T_hV_mG_idL2qs_1ES')

        Raises:
            ValueError: If name would exceed 30 characters
        """
        trucks = ScenarioNameEncoder.encode_truck_count(truck_count)
        velocity = ScenarioNameEncoder.encode_velocity_type(velocity_type)
        gaps = ScenarioNameEncoder.encode_gap_type(gap_type)
        losses = ScenarioNameEncoder.encode_loss_events(loss_types)
        fort = ScenarioNameEncoder.encode_fort(has_fort)

        name = f"{trucks}_{velocity}_{gaps}_{losses}_{fort}"

        if len(name) > 30:
            raise ValueError(f"Generated name exceeds 30 characters: '{name}'")

        return name


class ScenarioNameParser:
    """Parses scenario names back to attributes."""

    # Reverse mappings
    VELOCITY_CODES_REV = {v: k for k, v in ScenarioNameEncoder.VELOCITY_CODES.items()}
    GAP_CODES_REV = {v: k for k, v in ScenarioNameEncoder.GAP_CODES.items()}
    LOSS_CODES_REV = {v: k for k, v in ScenarioNameEncoder.LOSS_CODES.items()}

    @staticmethod
    def parse_name(name: str) -> Tuple[int, VelocityType, GapType, List[LossType], bool]:
        """
        Parse scenario name into components.

        Args:
            name: Name string (e.g., '3T_hV_mG_idL2qs_1ES')

        Returns:
            Tuple of (truck_count, velocity_type, gap_type, loss_types_list, has_fort)

        Raises:
            ValueError: If name format is invalid
        """
        # Remove .csv extension if present
        if name.endswith(".csv"):
            name = name[:-4]

        # Pattern: <digit(2-3)T>_<2 letters(mixed case)>_<2 letters(mixed case)>_<idL[0-9]+[a-z]+|none>_<0-1ES>
        # Velocity/gap codes can have uppercase: hB, vG, etc.
        pattern = r"^([23])T_([a-zA-Z]{2})_([a-zA-Z]{2})_(idL\d+[a-z]+|none)_([01])ES$"
        match = re.match(pattern, name)

        if not match:
            raise ValueError(f"Invalid scenario name format: '{name}'")

        truck_str, velocity_str, gap_str, loss_str, fort_str = match.groups()

        # Parse truck count
        truck_count = int(truck_str)
        if truck_count not in [2, 3]:
            raise ValueError(f"Invalid truck count: {truck_count}")

        # Parse velocity type
        velocity_type = ScenarioNameParser.VELOCITY_CODES_REV.get(velocity_str)
        if velocity_type is None:
            raise ValueError(f"Unknown velocity code: {velocity_str}")

        # Parse gap type
        gap_type = ScenarioNameParser.GAP_CODES_REV.get(gap_str)
        if gap_type is None:
            raise ValueError(f"Unknown gap code: {gap_str}")

        # Parse loss events
        loss_types = []
        if loss_str == "none":
            loss_types = []
        else:
            # Parse 'idL2qs' → count=2, loss_type=QUICK_SHORT
            loss_match = re.match(r"idL(\d+)([a-z]+)", loss_str)
            if not loss_match:
                raise ValueError(f"Invalid loss format: {loss_str}")

            count_str, loss_code_str = loss_match.groups()
            count = int(count_str)

            # TODO: Handle mixed loss types (e.g., 'qssl')
            # For now, assume all losses are same type
            loss_code = loss_code_str[:2]  # Take first 2 chars
            loss_type = ScenarioNameParser.LOSS_CODES_REV.get(loss_code)

            if loss_type is None:
                raise ValueError(f"Unknown loss code: {loss_code}")

            loss_types = [loss_type] * count

        # Parse FORT
        has_fort = fort_str == "1"

        return truck_count, velocity_type, gap_type, loss_types, has_fort

    @staticmethod
    def parse_to_dict(name: str) -> dict:
        """
        Parse scenario name to dictionary.

        Args:
            name: Name string

        Returns:
            Dict with keys: truck_count, velocity_type, gap_type, loss_count, has_fort, etc.
        """
        truck_count, velocity_type, gap_type, loss_types, has_fort = (
            ScenarioNameParser.parse_name(name)
        )

        return {
            "truck_count": truck_count,
            "velocity_type": velocity_type,
            "gap_type": gap_type,
            "loss_count": len(loss_types),
            "loss_types": loss_types,
            "has_fort": has_fort,
        }
