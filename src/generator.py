"""
handles token generation loop and state transitions
for a single prompt
"""


import json
from typing import Any
from llm_sdk import Small_LLM_Model
from src.tokenizer import VocabTracker
from src.decoder import MaskingEngine, JsonState


def generate_single_call(
        model: Small_LLM_Model,
        tracker: VocabTracker,
        engine: MaskingEngine,
        prompt_text: str,
        valid_names: list[str],
        context_prefix: str) -> dict[str, Any]:
    """
    MODIFICATION: Extracted the while loop from __main__.py
    into this dedicated file to keep the codebase modular.
    """
    escaped = json.dumps(prompt_text)[1:-1]
    engine.generated_text = f'[{{"prompt": "{escaped}", "name": "'
    engine.current_state = JsonState.INSIDE_NAME_VALUE

    tk_count = 0
    value_tokens = 0
    MAX_VAL_TK = 30

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

        allowed = engine.get_allowed_tokens(valid_names)

        current_ids = [int(i) for i in model.encode(
                context_prefix + engine.generated_text
                ).flatten().tolist()]
        raw_logits = model.get_logits_from_input_ids(current_ids)

        # MODIFICATION: Fixed the lookahead logic for numbers.
        # Added "-" to the valid check so negative numbers aren't
        # cut off immediately after the minus sign is generated.
        is_num = (engine.current_state == JsonState.EXPECT_PARAM_VALUE
                  and engine.current_param_type() == "number")

        if is_num and value_tokens > 0:
            raw_top = raw_logits.index(max(raw_logits))
            raw_top_text = tracker.get_token(raw_top) or ""
            clean_top = raw_top_text.lstrip("\u0120")
            is_valid = clean_top in ("0", "1", "2", "3", "4", "5",
                                     "6", "7", "8", "9", ".", "-")
            if not is_valid:
                try:
                    float(clean_top)
                    is_valid = True
                except ValueError:
                    pass
            if not is_valid:
                engine.active_key_index += 1
                next_state = (JsonState.INSIDE_PARAM_KEY
                              if engine.active_key_index <
                              len(engine.expected_keys)
                              else JsonState.DONE)
                sep = ", " if (next_state ==
                               JsonState.INSIDE_PARAM_KEY) else "}}]"
                engine.inject_deterministic(sep, next_state)
                value_tokens = 0
                continue

        clean_logits = engine.clean_logits(raw_logits, allowed)
        if all(x == float("-inf") for x in clean_logits):
            break

        best_id = clean_logits.index(max(clean_logits))
        raw_token = tracker.get_token(best_id) or ""

        if (engine.current_state == JsonState.EXPECT_PARAM_VALUE
                and engine.current_param_type() == "string"):
            token_text = raw_token.replace("\u0120", " ")
            token_text = token_text.replace("\\", "\\\\")
        else:
            token_text = raw_token.lstrip("\u0120")
        if (engine.current_state == JsonState.EXPECT_PARAM_VALUE
                and engine.current_param_type() == "string"
                and '"' in token_text):
            # Cut off the generated token exactly at the quote mark
            prefix = token_text.split('"')[0]
            engine.advance_state(prefix, valid_names)
            engine.active_key_index += 1
            next_state = (JsonState.INSIDE_PARAM_KEY
                          if engine.active_key_index <
                          len(engine.expected_keys)
                          else JsonState.DONE)
            # Manually inject the quote and proper separator
            sep = '", ' if (next_state ==
                            JsonState.INSIDE_PARAM_KEY) else '"}}]'
            engine.inject_deterministic(sep, next_state)
            value_tokens = 0
            continue
        engine.advance_state(token_text, valid_names)
        tk_count += 1
        if engine.current_state == JsonState.EXPECT_PARAM_VALUE:
            value_tokens += 1
            if value_tokens >= MAX_VAL_TK:
                engine.active_key_index += 1
                next_state = (JsonState.INSIDE_PARAM_KEY
                              if engine.active_key_index <
                              len(engine.expected_keys)
                              else JsonState.DONE)
                closer = '"' if engine.current_param_type() == "string" else ""
                sep = ", " if (next_state ==
                               JsonState.INSIDE_PARAM_KEY) else "}}]"
                engine.inject_deterministic(closer + sep, next_state)
                value_tokens = 0
        else:
            value_tokens = 0

    clean_output = engine.generated_text.strip()
    if (engine.current_state == JsonState.EXPECT_PARAM_VALUE
            and engine.current_param_type() == "string"
            and not clean_output.endswith('"')):
        clean_output += '"'

    if not clean_output.startswith("["):
        clean_output = "[" + clean_output
    if not clean_output.endswith("}]"):
        if clean_output.endswith(", "):
            clean_output = clean_output[:-2]
        elif clean_output.endswith(","):
            clean_output = clean_output[:-1]
        clean_output += ("}}]" if '"parameters":' in clean_output
                         else ', "parameters": {}}]')
    try:
        parsed = json.loads(clean_output)
        return parsed[0] if isinstance(parsed, list) and parsed else {}
    except json.JSONDecodeError as err:
        print(f"Warning: Invalid syntax - {err}")
        return {}
