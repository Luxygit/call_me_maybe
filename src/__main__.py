""" """


import argparse
import sys
from typing import Sequence


def parse_args(args: Sequence[str]) -> argparse.Namespace:
    """parse args"""
    parser = argparse.ArgumentParser(
            description="Constrained decoding function caller"
            )
    parser.add_argument(
            "--functions_definition",
            default="data/input/functions_definition.json",
            help="Path to functions definition JSON file"
            )
    parser.add_argument(
            "--input",
            default="data/input/function_calling_tests.json",
            help="Path to input test prompts JSON file"
            )
    parser.add_argument(
            "--output",
            default="data/output/function_calling_results.json",
            help="Path to write the results JSON file"
            )
    return parser.parse_args(args)


def main() -> None:
    parsed = parse_args(sys.argv[1:])
    print(f"Functions path: {parsed.functions_definition}")


if __name__ == "__main__":
    main()
