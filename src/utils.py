"""
getting raw data functions and prompts from test files
saves function callings into JSON
"""


import json
import os
from pydantic import ValidationError
from src.models import FunctionDefinition, PromptInput


def load_functions(file_path: str) -> list[FunctionDefinition]:
    """loads function definitions from raw JSON config"""
    if not os.path.exists(file_path):
        print("Error: Function schema not found.")
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        return [FunctionDefinition(**item) for item in raw_data]
    except json.JSONDecodeError:
        print("Error: Invalid JSON syntax")
        return []
    except ValidationError as err:
        print("Error: Validation failed")
        print(err)
        return []


def load_prompts(file_path: str) -> list[PromptInput]:
    """loads prompts from test file"""
    if not os.path.exists(file_path):
        print("Error: Prompt file not found")
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        return [PromptInput(**item) for item in raw_data]
    except json.JSONDecodeError:
        print("Error: Invalid JSON syntax")
        return []
    except ValidationError as err:
        print("Error: Validation failed")
        print(err)
        return []


def save_results(results: list[dict], output_file_path: str) -> bool:
    """
    saving prediction dictionaries to a JSON file
    results is a list of dicts with a prompt name and parameters
    Returns true if the file was written properly
    """
    folder = os.path.dirname(output_file_path)
    # create dirs if they dont exist
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    try:
        with open(output_file_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4)
        return True
    except (OSError, IOError) as err:
        print("Error: Could not write output")
        print(err)
        return False
