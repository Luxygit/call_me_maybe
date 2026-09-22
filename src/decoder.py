"""
constrained decoding state supervisor for grammar enforcement
Monitoring token choices to intercept and mask raw model logits
ensuring JSON structures and function schemas
"""

from __future__ import annotations
import numpy as np
from enum import Enum
from src.tokenizer import VocabTracker
from typing import cast, Any


class JsonState(Enum):
    """tracking sequential structure compliance of JSON"""
    INSIDE_NAME_VALUE = "INSIDE_NAME_VALUE"
    EXPECT_PARAM_OBJECT = "EXPECT_PARAM_KEY"
    INSIDE_PARAM_KEY = "INSIDE_PARAM_KEY"
    EXPECT_PARAM_VALUE = "EXPECT_PARAM_VALUE"
    DONE = "DONE"


class MaskingEngine:
    """modify unnormalised probability distribution to guarantee structure"""
    def __init__(self, tracker: VocabTracker, raw_schemas: list) -> None:
        """layout state supervisor variables"""
        self.tracker = tracker
        self.raw_schemas = raw_schemas
        self.current_state: JsonState = JsonState.INSIDE_NAME_VALUE
        self.generated_text: str = ""
        self.chosen_function: str | None = None
        self.expected_keys: list[str] = []
        self.active_key_index: int = 0
        self.prompt_words: list[str] = []

    def inject_deterministic(self, text: str, new_state: "JsonState") -> None:
        self.generated_text += text
        self.current_state = new_state

    def current_param_type(self) -> Any:
        """look up the schema type of the parameter being filled"""
        for f in self.raw_schemas:
            if f.name == self.chosen_function:
                key = self.expected_keys[self.active_key_index]
                return f.parameters[key].type
        return "string"

    def clean_logits(
            self,
            raw_scores: list[float],
            allowed_words: list[str]) -> list[float]:
        """
        keep scored for allowed words and assign -inf for the rest
        returns updated list of scores
        """
        # converting raw list into a numpy mem array
        scores_array = np.array(raw_scores, dtype=np.float32)
        # check vocab dict indices for whitelisted keys
        allowed_ids: list[int] = []
        for word in allowed_words:
            tid1 = self.tracker.get_id(word)
            if tid1 is not None:
                allowed_ids.append(tid1)
            tid2 = self.tracker.get_id(f"Ġ{word}")
            if tid2 is not None:
                allowed_ids.append(tid2)
        # not leaving mask empty, keep original scores to continue loop
        if not allowed_ids:
            return raw_scores
        # build a fast mask to block out bad options
        mask = np.ones_like(scores_array, dtype=bool)
        # Open only our whitelisted spaces inside the mask
        mask[allowed_ids] = False
        # painting all remaining unallowed slots with -inf
        scores_array[mask] = float("-inf")
        return cast(list[float], scores_array.tolist())

    def get_allowed_tokens(
            self,
            available_functions: list[str]) -> list[str]:
        """
        look current state and return next allowed string tokens
        """
        if self.current_state == JsonState.INSIDE_NAME_VALUE:
            marker = '"name": "'
            already = (
                self.generated_text.split(marker)[-1]
                if marker in self.generated_text else ""
            )
            legal_tokens = []
            for fn in available_functions:
                if fn.startswith(already):
                    rem = fn[len(already):]
                    for token in self.tracker._token_to_id:
                        if token and (rem.startswith(token)
                                      or token == f"Ġ{rem}"):
                            legal_tokens.append(token)
            return list(set(legal_tokens))[:300]

        if self.current_state == JsonState.EXPECT_PARAM_OBJECT:
            # Match raw characters step-by-step
            return ['"', ',', 'Ġ', 'parameters', ':',
                    'Ġ:', '{', '", "parameters": {']

        if self.current_state == JsonState.INSIDE_PARAM_KEY:
            if not self.expected_keys and self.chosen_function:
                for f in self.raw_schemas:
                    if f.name == self.chosen_function:
                        self.expected_keys = list(f.parameters.keys())
            if self.active_key_index < len(self.expected_keys):
                target_key = self.expected_keys[self.active_key_index]
                return [
                    f'"{target_key}":', f'"{target_key}"', 'Ġ', '"', ':',
                    '": ', f'Ġ"{target_key}":', f'Ġ"{target_key}"'
                ]
            return ["}}]", "}", "}]", "Ġ}]"]

        if self.current_state == JsonState.EXPECT_PARAM_VALUE:
            current_type = self.current_param_type()
            if current_type == "number":
                return ["0", "1", "2", "3", "4", "5", "6", "7", "8",
                        "9", "."]
            if current_type == "boolean":
                return ["true", "false"]
            key = self.expected_keys[self.active_key_index]
            marker = f'"{key}": "'
            already = (
                self.generated_text.split(marker)[-1]
                if marker in self.generated_text else ""
            )
            legal_tokens = []
            for word in self.prompt_words:
                clean = word.strip("'\".,()!?")
                if clean.startswith(already):
                    rem = clean[len(already):]
                    for token in self.tracker._token_to_id:
                        if token and (rem.startswith(token)
                                      or token == f"Ġ{rem}"):
                            legal_tokens.append(token)
            return list(set(legal_tokens))[:300]
        return []

    def advance_state(
            self,
            token_text: str,
            available_functions: list[str]
            ) -> None:
        """
        add the text and shift to the next state logically
        token_text is the last piece of generated text by model
        avail_functions list of valid function names in the JSON
        """
        self.generated_text += token_text
        # consume forced struct tokens if present
        # name selection
        if self.current_state == JsonState.INSIDE_NAME_VALUE:
            # filter candidates that no longer match growing name
            # check if a full function was completed
            for fn in available_functions:
                if fn in self.generated_text:
                    self.chosen_function = fn
                    self.current_state = JsonState.EXPECT_PARAM_OBJECT
                    for f in self.raw_schemas:
                        if f.name == fn:
                            self.expected_keys = list(f.parameters.keys())
                    break
        elif self.current_state == JsonState.EXPECT_PARAM_OBJECT:
            if '"parameters": {' in self.generated_text:
                self.current_state = JsonState.INSIDE_PARAM_KEY
                self.active_key_index = 0
        elif self.current_state == JsonState.INSIDE_PARAM_KEY:
            if (self.generated_text.endswith(":")
                or self.generated_text.endswith('": ')
               or self.generated_text.strip().endswith(":")):
                self.current_state = JsonState.EXPECT_PARAM_VALUE
            # closure detection
            elif self.generated_text.rstrip().endswith("}]"):
                self.current_state = JsonState.DONE
        elif self.current_state == JsonState.EXPECT_PARAM_VALUE:
            if token_text.strip().endswith(","):
                self.active_key_index += 1
                self.current_state = JsonState.INSIDE_PARAM_KEY
            elif self.generated_text.rstrip().endswith("}]"):
                self.current_state = JsonState.DONE
