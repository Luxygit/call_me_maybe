"""
output utlity for saving function callings
formats extracted model predictions into a JSON array of the
required output file standard
"""


import json
import os


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
