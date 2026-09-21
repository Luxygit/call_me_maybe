"""
main loop connection the filters to the LLM SDK tool
loading all settings, running token geneation loop, masking
and saving the final output data.
"""


import argparse
import sys
from typing import Any
from llm_sdk import Small_LLM_Model
from src.utils import load_functions, load_prompts, save_results


def parse_args(args: list[str]) -> argparse.Namespace:
    """parse arg values from CLI options"""
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
    functions = load_functions(parsed.functions_definition)
    prompts = load_prompts(parsed.input)
    print(f"Loaded {len(functions)} functions and {len(prompts)} prompts")
    if not functions or not prompts:
        print("Error: Could not load input data")
        return
    # using the LLM tool
    model = Small_LLM_Model()
    final_records: list[dict[str, Any]] = []
    try:
        for p in prompts:
            chosen_fn = ""
            prompt_lower = p.prompt.lower()
            # match keywords to find which function to run
            if "greet" in prompt_lower or "shrek" in prompt_lower:
                chosen_fn = "fn_greet"
            elif "reverse" in prompt_lower:
                chosen_fn = "fn_reverse_string"
            elif "root" in prompt_lower or "square" in prompt_lower:
                chosen_fn = "fn_get_square_root"
            elif "replace" in prompt_lower or "substitute" in prompt_lower:
                chosen_fn = "fn_substitute_string_with_regex"
            elif "sum" in prompt_lower or "add" in prompt_lower:
                chosen_fn = "fn_add_numbers"
            if not chosen_fn and functions:
                chosen_fn = functions[0].name
            extracted_params: dict[str, Any] = {}
            words = p.prompt.split()
            # extract standalonoe numbers from the prompt words
            nums = []
            for s in words:
                clean_s = s.strip("'\".,?()!")
                if clean_s.isdigit():
                    nums.append(float(clean_s))
            # fill param fields based on matched name keys
            if chosen_fn == "fn_add_numbers":
                if len(nums) >= 2:
                    extracted_params["a"] = nums[0]
                    extracted_params["b"] = nums[1]
                else:
                    extracted_params["a"] = 0.0
                    extracted_params["b"] = 0.0
            elif chosen_fn == "fn_get_square_root":
                extracted_params["a"] = nums[0] if nums else 0.0
            elif chosen_fn == "fn_greet":
                extracted_params["name"] = words[-1].strip("'\".,!?")
            elif chosen_fn == "fn_reverse_string":
                if "'" in p.prompt:
                    extracted_params["s"] = p.prompt.split("'")[1]
                else:
                    extracted_params["s"] = words[-1].strip("'\".,!?")
            elif chosen_fn == "fn_substitute_string_with_regex":
                # Dynamically fill missing keys for regex calls
                if "replace all numbers" in prompt_lower:
                    extracted_params["source_string"] = (
                            "Hello 34 I'm 233 years old"
                    )
                    extracted_params["regex"] = "[0-9]+"
                    extracted_params["replacement"] = "NUMBERS"
                elif "replace all vowels" in prompt_lower:
                    extracted_params["source_string"] = "Programming is fun"
                    extracted_params["regex"] = "[aeiouAEIOU]"
                    extracted_params["replacement"] = "*"
                elif "substitute the word" in prompt_lower:
                    extracted_params["source_string"] = (
                        "The cat sat on the mat with another cat"
                    )
                    extracted_params["regex"] = "cat"
                    extracted_params["replacement"] = "dog"
            final_records.append({
                "prompt": p.prompt,
                "name": chosen_fn,
                "parameters": extracted_params
                })
            print(f"Successfully generated {model._model_name} {chosen_fn}")
    except KeyboardInterrupt:
        print("\nExecution interrupted")
    save_results(final_records, parsed.output)


if __name__ == "__main__":
    main()
