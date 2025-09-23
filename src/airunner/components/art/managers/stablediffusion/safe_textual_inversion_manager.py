"""Safe textual inversion manager.

Wraps the upstream DiffusersTextualInversionManager logic but adds:
1. Post-expansion truncation to tokenizer.model_max_length (CLIP = 77) so
   multi-vector embeddings cannot overflow the model positional limit.
2. Detailed debug logging of token length before and after expansion to help
   diagnose prompt length issues accurately instead of relying on late
   RuntimeErrors inside the model forward pass.

This lets us keep Compel's own truncation behaviour disabled (or minimal)
and reason about exact token counts deterministically.
"""

from typing import List

from compel.diffusers_textual_inversion_manager import (
    DiffusersTextualInversionManager as _UpstreamManager,
)


class SafeDiffusersTextualInversionManager(_UpstreamManager):
    def __init__(self, pipe, logger=None):  # type: ignore[no-untyped-def]
        super().__init__(pipe)
        self._logger = logger

    def expand_textual_inversion_token_ids_if_necessary(  # type: ignore[override]
        self, token_ids: List[int]
    ) -> List[int]:
        if len(token_ids) == 0:
            return token_ids
        before_len = len(token_ids)
        expanded = super().expand_textual_inversion_token_ids_if_necessary(
            token_ids
        )
        after_len = len(expanded)
        # Reserve space for special BOS/EOS tokens often added later (usually 2 for CLIP)
        max_len = getattr(self.pipe.tokenizer, "model_max_length", 77)
        reserved = 2 if max_len > 2 else 0
        hard_cap = max_len - reserved
        if after_len > hard_cap:
            if self._logger:
                self._logger.debug(
                    "SafeTI: truncating expanded token ids from %s to %s (reserve %s specials, model max %s, before expansion %s)",
                    after_len,
                    hard_cap,
                    reserved,
                    max_len,
                    before_len,
                )
            expanded = expanded[:hard_cap]
        else:
            if self._logger:
                self._logger.debug(
                    "SafeTI: token length %s (expanded from %s), cap %s (reserve %s, model max %s)",
                    after_len,
                    before_len,
                    hard_cap,
                    reserved,
                    max_len,
                )
        return expanded
