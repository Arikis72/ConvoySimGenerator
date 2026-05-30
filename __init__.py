"""
SimGenerator — Convoy scenarios generator for ConvoySIM

A tool to generate randomized convoy scenarios as CSV files compatible with ConvoySIM Stage A.
"""

__version__ = "0.1.0"

from models import (
    ScenarioConfig,
    Scenario,
    VelocityType,
    GapType,
    LossType,
    CSVRow,
)
from generator import ScenarioGenerator
from csv_writer import CSVWriter
from naming import ScenarioNameEncoder, ScenarioNameParser
from validation import ScenarioValidator

__all__ = [
    "ScenarioConfig",
    "Scenario",
    "VelocityType",
    "GapType",
    "LossType",
    "CSVRow",
    "ScenarioGenerator",
    "CSVWriter",
    "ScenarioNameEncoder",
    "ScenarioNameParser",
    "ScenarioValidator",
]
