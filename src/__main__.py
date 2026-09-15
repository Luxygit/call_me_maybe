"""
main loop connection the filters to the LLM SDK tool
loading all settings, running token geneation loop, masking
and saving the final output data.
"""


import argparse
import sys
from llm_sdk import Small_LLM_Model
from src.tokenizer import VocabTracker
from src.decoder import MaskingEngine, JsonState
from src.writer import save_results
from src.utils import load_functions, load_prompts


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
    print(f"Loaded {len(functions)}functions and {len(prompts)} prompts")
    if not functions or not prompts:
        print("Error: Could not load input data")
        return
    # using the LLM tool
    model = Small_LLM_Model()
    vocab_path = model.get_path_to_vocab_file()
    tracker = VocabTracker(vocab_path)
    # getting functions names from loaded schemas
    valid_function_names = [fn.name for fn in functions]
    final_records: list[dict] = []
    # running loop for each user prompt question
    for p in prompts:
        engine = MaskingEngine(tracker)
        current_ids = model.encode(p.prompt)
        # generate tokens until JSON is finished
        while engine.current_state != JsonState.DONE:
            raw_logits = model.get_logits_from_input_ids(current_ids)
            # get words safe to use next
            allowed = engine.update_state_and_get_allowed(
                    "", valid_function_names)
            # mask out bad options
            clean_logits = engine.clean_logits(raw_logits, allowed)
            # select token with highest score
            best_id = clean_logits.index(max(clean_logits))
            # update tracker with the new generated text token
            token_text = tracker.get_token(best_id) or ""
            engine.update_state_and_get_allowed(
                    token_text, valid_function_names)
            current_ids.append(best_id)
        print("Successfully generated text!")
    save_results(final_records, parsed.output)


if __name__ == "__main__":
    main()
