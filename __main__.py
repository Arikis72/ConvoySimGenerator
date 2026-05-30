"""
__main__.py — CLI entry point for SimGenerator

Usage:
    python -m simgenerator [--duration SECONDS] [--max-events N] [--min-sep SECONDS] [--count N] [--output FOLDER] [--seed SEED]
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from models import ScenarioConfig
from generator import ScenarioGenerator
from csv_writer import CSVWriter


def main():
    """Parse command-line arguments and run generation."""
    parser = argparse.ArgumentParser(
        description="Generate randomized convoy scenarios for ConvoySIM"
    )

    parser.add_argument(
        "--duration",
        type=float,
        default=120.0,
        help="Scenario duration in seconds (default: 120)",
    )

    parser.add_argument(
        "--max-events",
        type=int,
        default=5,
        help="Maximum events per scenario (default: 5)",
    )

    parser.add_argument(
        "--min-sep",
        type=float,
        default=5.0,
        help="Minimum event separation in seconds (default: 5)",
    )

    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of scenarios to generate (default: 10)",
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help=(
            "Scene_Gen root folder.  Each run is saved in a ddmmyyyy_hhmm "
            "sub-folder automatically (default root: Scene_Gen/)"
        ),
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )

    args = parser.parse_args()

    # Always write into a timestamped sub-folder so successive runs are isolated.
    # --output (if given) is the Scene_Gen root; defaults to "Scene_Gen".
    scene_gen_root = args.output or "Scene_Gen"
    timestamp = datetime.now().strftime("%d%m%Y_%H%M")
    output_folder = os.path.join(scene_gen_root, timestamp)

    print(f"SimGenerator v0.1.0")
    print(f"Output folder: {output_folder}")
    print()

    # Create configuration
    config = ScenarioConfig(
        scenario_duration_s=args.duration,
        max_events=args.max_events,
        min_event_separation_s=args.min_sep,
        num_scenarios=args.count,
    )

    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        print(f"ERROR: Invalid configuration: {e}")
        return 1

    # Create generator
    def progress(current, total):
        print(f"Generated {current}/{total} scenarios...", end="\r")

    generator = ScenarioGenerator(config, seed=args.seed, progress_callback=progress)

    # Generate scenarios
    try:
        print("Generating scenarios...")
        scenarios = generator.generate_all()
        print()
        print(f"Generated {len(scenarios)} scenarios")
    except Exception as e:
        print(f"ERROR: Generation failed: {e}")
        return 1

    # Write scenarios
    try:
        print(f"Writing scenarios to {output_folder}...")
        paths = CSVWriter.write_scenarios_batch(scenarios, output_folder)
        print(f"Wrote {len(paths)} CSV files")
        print()
        print("Generated scenarios:")
        for path in paths[:10]:  # Show first 10
            print(f"  {Path(path).name}")
        if len(paths) > 10:
            print(f"  ... and {len(paths) - 10} more")
    except Exception as e:
        print(f"ERROR: Failed to write scenarios: {e}")
        return 1

    print()
    print("Generation complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
