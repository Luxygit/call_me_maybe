"""
constrained decoding state supervisor for grammar enforcement
Monitoring token choices to intercept and mask raw model logits
ensuring JSON structures and function schemas
"""

from __future__ import annotations
import numpy as np
from enum import Enum
from src.tokenizer import VocabTracker
from typing import cast


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
        # if struct tokens pending, only allow the next one
        if self.current_state == JsonState.INSIDE_NAME_VALUE:
            # only allow tokens that continue one remaining name
            return available_functions
        if self.current_state == JsonState.EXPECT_PARAM_OBJECT:
            # struct tokens are forced via queue
            return ['", "parameters": {']
        if self.current_state == JsonState.INSIDE_PARAM_KEY:
            # allow digits, quotes, common punctuation, closing
            if not self.expected_keys and self.chosen_function:
                for f in self.raw_schemas:
                    if f.name == self.chosen_function:
                        self.expected_keys = list(f.parameters.keys())
            if self.active_key_index < len(self.expected_keys):
                target_key = self.expected_keys[self.active_key_index]
                return [f'"{target_key}":', f'"{target_key}"']
            return ["}}]", "}", "}]"]
        if self.current_state == JsonState.EXPECT_PARAM_VALUE:
            base_tokens = [
                    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", ".",
                    '"', ",", "Ġ", "true", "false", "null", "}", "}]", ":"
                    ]
            for word in self.prompt_words:
                clean = word.strip("'\".,()!?")
                if clean:
                    base_tokens.append(clean)
            return list(set(base_tokens))
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
                    break
        elif self.current_state == JsonState.EXPECT_PARAM_OBJECT:
            if '"parameters": {' in self.generated_text:
                self.current_state = JsonState.INSIDE_PARAM_KEY
                self.active_key_index = 0
        elif self.current_state == JsonState.INSIDE_PARAM_KEY:
            if (self.generated_text.endswith(":")
               or self.generated_text.endswith('": ')):
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
