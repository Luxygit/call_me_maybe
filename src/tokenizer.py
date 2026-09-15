"""
Vocabulary mapping, bidirectional translation between raw text string 
tokens and model integer token IDs
"""


import json


class VocabTracker:
    """index conversions between string tokens and token ids"""
    def __init__(self, vocab_file_path: str) -> None:
        """
        parsing model vocabulary
        vocab_file_path is the sdk vocab json    
        """
        with open(vocab_file_path. "r", encoding="utf-8") as f:
            self._token_to_id: dict[str, int] = json.load(f)
        # inverse lookup table maps int -> str
        self._id_to_token: dict[int, str] = {
                token_id: token for token, token_id
                in self._token_to_id.items()
                }
    
    def get_id(self, token_str: str) -> int | None:
        """
        returns token ID for a token string token_string 'Gis'
        """
        return self._token_to_id.get(token_str)
    
    def get_id(self, token_str: str) -> int | None:
        """
        returns token string for a token_id assigned by the model vocab
        """
        return self._id_to_token.get(token_id)
