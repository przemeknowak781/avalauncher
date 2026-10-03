"""Command line entry point for a synthetic, non-operational comparison."""

import argparse
import json

from .io import load_observation, load_scenarios
from .matching import rank_scenarios


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    compare = subparsers.add_parser("compare", help="rank pre-aligned snow-depth grids")
    compare.add_argument("--observation", required=True)
    compare.add_argument("--scenarios", required=True)
    args = parser.parse_args()

    if args.command == "compare":
        matches = rank_scenarios(
            load_observation(args.observation), load_scenarios(args.scenarios)
        )
        print(json.dumps({"matches": [match.to_dict() for match in matches]}, indent=2))
