"""
main loop connection the filters to the LLM SDK tool
loading all settings, running token geneation loop, masking
and saving the final output data.
"""


import argparse
import sys
from typing import Any
from llm_sdk import Small_LLM_Model
from src.tokenizer import VocabTracker
from src.decoder import MaskingEngine
from src.utils import load_functions, load_prompts, save_results
from src.generator import generate_single_call


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
    vocab_path = model.get_path_to_vocab_file()
    tracker = VocabTracker(vocab_path)
    valid_names = [fn.name for fn in functions]
    catalog_lines = []
    for fn in functions:
        params = ", ".join(
                f"{k}: {v.type}" for k, v in fn.parameters.items())
        catalog_lines.append(f"- {fn.name}({params}): {fn.description}")
    sys_msg = "Task: Extract exact values from the prompt into JSON.\
                Preserve negative signs!"
    example = ('Example: [{"prompt": "Add -5 and 3", '
               '"name": "fn_add_numbers", '
               '"parameters": {"a": -5, "b": 3}}]')
    context_prefix = (
            f"{sys_msg}\n{example}\n\nAvailable functions:\n" +
            "\n".join(catalog_lines) + "\n\n")
    final_records: list[dict[str, Any]] = []
    try:
        for p in prompts:
            engine = MaskingEngine(tracker, functions)
            engine.prompt_words = p.prompt.split()
            engine.prompt_text = p.prompt.replace("'", "").replace('"', "")
            result = generate_single_call(
                    model, tracker, engine, p.prompt,
                    valid_names, context_prefix)
            if result:
                final_records.append({
                        "prompt": p.prompt,
                        "name": result.get("name", ""),
                        "parameters": result.get("parameters", {})
                })
                print(f"Successfully generated {result.get('name')}")
    except KeyboardInterrupt:
        print("\nExecution interrupted")
    save_results(final_records, parsed.output)


if __name__ == "__main__":
    main()
