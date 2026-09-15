"""
constrained decoding state supervisor for grammar enforcement
Monitoring token choices to intercept and mask raw model logits
ensuring JSON structures and function schemas
"""


from enum import Enum
from src.tokenizer import VocabTracker


class JsonState(Enum):
    """tracking sequential structure compliance of JSON"""
    START = "START"
    EXCEPT_NAME_KEY = "EXPECT_NAME_KEY"
    INSIDE_NAME_VALUE = "INSIDE_NAME_VALUE"
    EXPECT_PARAM_KEY = "EXPECT_PARAM_KEY"
    DONE = "DONE"


class MaskingEngine:
    """modify unnormalised probability distribution to guarantee structure"""
    def __init__(self, tracker: VocabTracker) -> None:
        """layout state supervisor variables"""
        self.current_state: JsonState = JsonState.START
        self.generated_text: str = ""
        self.tracker = tracker

    def clean_logits(
            self,
            raw_scores: list[float],
            allowed_words: list[str]) -> list[float]:
        """
        keep scored for allowed words and assign -inf for the rest
        returns updated list of scores
        """
        safe_scores = list(raw_scores)
        allowed_ids = []
        for word in allowed_words:
            word_id = self.tracker.get_id(word)
            if word_id is not None:
                allowed_ids.append(word_id)
        for idx in range(len(safe_scores)):
            if idx not in allowed_ids:
                safe_scores[idx] = float("-inf")
        return safe_scores

    def update_state_and_get_allowed(
            self,
            new_token_text: str,
            available_functions: list[str]) -> list[str]:
        """
        update current position and return next allowed string tokens
        """
        self.generated_text += new_token_text
        if self.current_state == JsonState.START:
            # forcing array and object opening
            self.current_state = JsonState.EXPECT_NAME_KEY
            return ['[{"prompt": "']
        if self.current_state == JsonState.EXPECT_NAME_KEY:
            # then we expect the function name key
            if self.generated_text.endswith('", "name": "'):
                self.current_state = JsonState.INSIDE_NAME_VALUE
                return available_functions
        if self.current_state == JsonState.INSIDE_NAME_VALUE:
            # checking if one of the valid function names was printed
            for fn in available_functions:
                if self.generated_text.endswith(fn):
                    self.current_state = JsonState.EXPECT_PARAM_KEY
                    return ['", "parameters": {']
        if self.current_state == JsonState.EXPECT_PARAM_KEY:
            if self.generated_text.endswith("}]"):
                self.current_state = JsonState.DONE
                return []
            # in the end allow closing characters
            return ["}"] if self.generated_text.endswith("}") else ["}"]
        return []
