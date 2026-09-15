""""""


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
