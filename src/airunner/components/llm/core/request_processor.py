"""
Request processing pipeline for LLM requests.

Handles the complete lifecycle of an LLM request:
1. Validate and normalize request
2. Apply database settings with proper overrides
3. Prepare context and memory
4. Execute the request
5. Process and stream responses
"""

from typing import Optional, Any
from dataclasses import replace

from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.enums import LLMActionType
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class RequestProcessor:
    """
    Processes LLM requests with proper settings management.

    Handles the complexity of merging database settings with
    request-specific overrides while maintaining clean separation.
    """

    def __init__(
        self,
        default_settings: Optional[Any] = None,
        logger: Optional[Any] = None,
    ):
        """
        Initialize request processor.

        Args:
            default_settings: Default generator settings from database
            logger: Logger instance
        """
        self.default_settings = default_settings
        self.logger = logger or get_logger(__name__, AIRUNNER_LOG_LEVEL)

    def merge_settings(
        self,
        request: LLMRequest,
        db_settings: Optional[Any] = None,
    ) -> LLMRequest:
        """
        Merge request with database settings.

        Request-specific values override database defaults.

        Args:
            request: LLM request with possible overrides
            db_settings: Settings from database

        Returns:
            Merged LLMRequest with all values resolved
        """
        settings = db_settings or self.default_settings
        if not settings:
            return request

        # Build merged settings dict
        merged = {}

        # Map database settings to request fields
        db_mapping = {
            "do_sample": "do_sample",
            "early_stopping": "early_stopping",
            "eta_cutoff": "eta_cutoff",
            "length_penalty": "length_penalty",
            "max_new_tokens": "max_new_tokens",
            "min_length": "min_length",
            "no_repeat_ngram_size": "no_repeat_ngram_size",
            "num_beams": "num_beams",
            "num_return_sequences": "num_return_sequences",
            "repetition_penalty": "repetition_penalty",
            "temperature": "temperature",
            "top_k": "top_k",
            "top_p": "top_p",
            "use_cache": "use_cache",
        }

        # Apply database defaults
        for db_key, req_key in db_mapping.items():
            if hasattr(settings, db_key):
                merged[req_key] = getattr(settings, db_key)

        # Override with request-specific values
        request_dict = request.__dict__
        for key, value in request_dict.items():
            if key in merged and value is not None:
                # Only override if explicitly set
                merged[key] = value

        # Create new request with merged values
        return replace(request, **merged)

    def validate_request(self, request: LLMRequest) -> bool:
        """
        Validate request parameters.

        Args:
            request: Request to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check ranges
            if request.max_new_tokens < 1:
                self.logger.error("max_new_tokens must be >= 1")
                return False

            if request.temperature < 0.0001:
                self.logger.error("temperature must be >= 0.0001")
                return False

            if not (0 < request.top_p <= 1):
                self.logger.error("top_p must be between 0 and 1")
                return False

            if request.top_k < 1:
                self.logger.error("top_k must be >= 1")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating request: {e}")
            return False

    def prepare_request(
        self,
        prompt: str,
        action: LLMActionType = LLMActionType.CHAT,
        llm_request: Optional[LLMRequest] = None,
        db_settings: Optional[Any] = None,
    ) -> LLMRequest:
        """
        Prepare complete request for execution.

        Args:
            prompt: User prompt
            action: Action type
            llm_request: Optional request overrides
            db_settings: Database settings

        Returns:
            Validated and merged LLMRequest
        """
        # Create default request if none provided
        if llm_request is None:
            llm_request = LLMRequest()

        # Merge with database settings
        merged_request = self.merge_settings(llm_request, db_settings)

        # Validate
        if not self.validate_request(merged_request):
            self.logger.warning(
                "Using default request due to validation failure"
            )
            merged_request = LLMRequest()

        return merged_request
