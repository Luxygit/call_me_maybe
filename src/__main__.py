"""
main loop connection the filters to the LLM SDK tool
loading all settings, running token geneation loop, masking
and saving the final output data.
"""


import argparse
import sys
import json
from typing import Any
from llm_sdk import Small_LLM_Model
from src.tokenizer import VocabTracker
from src.decoder import MaskingEngine, JsonState
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
    vocab_path = model.get_path_to_vocab_file()
    tracker = VocabTracker(vocab_path)
    valid_function_names = [fn.name for fn in functions]
    catalog_lines = []
    for fn in functions:
        params = ", ".join(
                f"{k}: {v.type}" for k, v in fn.parameters.items())
        catalog_lines.append(f"- {fn.name}({params}): {fn.description}")
    context_prefix = (
            "Available functions:\n" + "\n".join(catalog_lines) + "\n\n")
    final_records: list[dict[str, Any]] = []
    try:
        for p in prompts:
            engine = MaskingEngine(tracker, functions)
            engine.prompt_words = p.prompt.split()
            escaped_prompt = json.dumps(p.prompt)[1:-1]
            prefix_context = f'[{{"prompt": "{escaped_prompt}", "name": "'
            engine.generated_text = prefix_context
            engine.current_state = JsonState.INSIDE_NAME_VALUE
            tk_count = 0
            value_tokens = 0
            MAX_VALUE_TOKENS = 10
            while engine.current_state != JsonState.DONE and tk_count < 150:
                if engine.current_state == JsonState.EXPECT_PARAM_OBJECT:
                    engine.inject_deterministic(
                            '", "parameters": {', JsonState.INSIDE_PARAM_KEY)
                    continue
                if engine.current_state == JsonState.INSIDE_PARAM_KEY:
                    if engine.active_key_index < len(engine.expected_keys):
                        key = engine.expected_keys[engine.active_key_index]
                        opener = (f'"{key}": "'
                                  if engine.current_param_type() == "string"
                                  else f'"{key}": ')
                        engine.inject_deterministic(
                                opener, JsonState.EXPECT_PARAM_VALUE)
                    else:
                        engine.inject_deterministic("}}]", JsonState.DONE)
                    continue

                allowed = engine.get_allowed_tokens(valid_function_names)
                current_ids = [int(i) for i in model.encode(
                        context_prefix + engine.generated_text
                        ).flatten().tolist()]
                raw_logits = model.get_logits_from_input_ids(current_ids)
                is_number = (engine.current_state
                             == JsonState.EXPECT_PARAM_VALUE
                             and engine.current_param_type() == "number")
                if is_number and value_tokens > 0:
                    raw_top = raw_logits.index(max(raw_logits))
                    raw_top_text = tracker.get_token(raw_top) or ""
                    if raw_top_text.lstrip("\u0120") not in (
                            "0", "1", "2", "3", "4", "5", "6", "7",
                            "8", "9", "."):
                        closer = ""
                        engine.active_key_index += 1
                        next_state = (
                                JsonState.INSIDE_PARAM_KEY
                                if (engine.active_key_index
                                    < len(engine.expected_keys))
                                else JsonState.DONE)
                        sep = (", " if next_state ==
                               JsonState.INSIDE_PARAM_KEY else "}}]")
                        engine.inject_deterministic(
                                closer + sep, next_state)
                        value_tokens = 0
                        continue
                clean_logits = engine.clean_logits(raw_logits, allowed)
                if all(x == float("-inf") for x in clean_logits):
                    break
                best_id = clean_logits.index(max(clean_logits))
                token_text = (tracker.get_token(best_id) or "").lstrip(
                        "\u0120")
                engine.advance_state(token_text, valid_function_names)
                tk_count += 1
                if engine.current_state == JsonState.EXPECT_PARAM_VALUE:
                    value_tokens += 1
                    if value_tokens >= MAX_VALUE_TOKENS:
                        closer = ('"' if engine.current_param_type()
                                  == "string" else "")
                        engine.active_key_index += 1
                        next_state = (
                                JsonState.INSIDE_PARAM_KEY
                                if (engine.active_key_index
                                    < len(engine.expected_keys))
                                else JsonState.DONE)
                        sep = (", " if next_state ==
                               JsonState.INSIDE_PARAM_KEY else "}}]")
                        engine.inject_deterministic(
                                closer + sep, next_state)
                        value_tokens = 0
                else:
                    value_tokens = 0
            # Fallback syntax completion engine layer
            clean_output = engine.generated_text.strip()
            if not clean_output.startswith("["):
                clean_output = "[" + clean_output
            if not clean_output.endswith("}]"):
                if '"parameters":' in clean_output:
                    clean_output += "}]"
                else:
                    clean_output += ', "parameters": {}}]'
            try:
                parsed_json = json.loads(clean_output)
                if isinstance(parsed_json, list) and len(parsed_json) > 0:
                    inner = parsed_json[0]
                    final_records.append({
                        "prompt": p.prompt,
                        "name": inner.get("name", ""),
                        "parameters": inner.get("parameters", {})
                        })
                    print(f"Successfully generated {inner.get('name')}")
            except (json.JSONDecodeError, IndexError, KeyError) as err:
                print("Warning: Invalid syntax")
                print("  reason:", err)
                print("  raw buffer:", repr(clean_output))
    except KeyboardInterrupt:
        print("\nExecution interrupted")
    save_results(final_records, parsed.output)


if __name__ == "__main__":
    main()
