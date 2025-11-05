"""Adapter loading functionality for LLM models.

This mixin handles:
- Retrieving enabled adapter names from settings
- Querying adapters from database
- Applying PEFT adapters to models
- Loading all enabled adapters
"""

import json
import os
from typing import List, TYPE_CHECKING

from airunner.components.llm.data.fine_tuned_model import FineTunedModel
from airunner.utils.settings.get_qsettings import get_qsettings

if TYPE_CHECKING:
    pass

# Optional import for PEFT support
try:
    from peft import PeftModel
except ImportError:
    PeftModel = None


class AdapterLoaderMixin:
    """Mixin for LLM adapter loading functionality."""

    def _get_enabled_adapter_names(self) -> List[str]:
        """Retrieve enabled adapter names from QSettings.

        Returns:
            List of adapter names that are currently enabled
        """
        try:
            qs = get_qsettings()
            enabled_adapters_json = qs.value(
                "llm_settings/enabled_adapters", "[]"
            )
            return json.loads(enabled_adapters_json)
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing enabled adapters JSON: {e}")
            return []

    def _get_enabled_adapters(
        self, adapter_names: List[str]
    ) -> List[FineTunedModel]:
        """Query database for adapters matching the given names.

        Args:
            adapter_names: List of adapter names to retrieve

        Returns:
            List of FineTunedModel objects matching the names
        """
        if not adapter_names:
            return []
        try:
            adapters = FineTunedModel.objects.all()
            return [a for a in adapters if a.name in adapter_names]
        except Exception as e:
            # Table might not exist if migrations haven't run
            self.logger.error(f"Error querying adapters: {e}")
            return []

    def _apply_adapter(self, adapter: FineTunedModel) -> bool:
        """Apply a single PEFT adapter to the model.

        Args:
            adapter: FineTunedModel instance with adapter path

        Returns:
            True if adapter was applied successfully, False otherwise
        """
        if not adapter.adapter_path or not os.path.exists(
            adapter.adapter_path
        ):
            self.logger.warning(
                f"Adapter '{adapter.name}' path does not exist"
            )
            return False

        try:
            self._model = PeftModel.from_pretrained(
                self._model, adapter.adapter_path
            )
            self._model.eval()
            return True
        except Exception as e:
            self.logger.error(f"Error loading adapter '{adapter.name}': {e}")
            return False

    def _load_adapters(self) -> None:
        """Load all enabled adapters onto the base model.

        Retrieves enabled adapter names from settings, queries them from
        the database, and applies each one to the loaded model.
        """
        if PeftModel is None:
            return

        try:
            adapter_names = self._get_enabled_adapter_names()
            if not adapter_names:
                return

            enabled_adapters = self._get_enabled_adapters(adapter_names)
            loaded_count = sum(
                self._apply_adapter(a) for a in enabled_adapters
            )

            if loaded_count > 0:
                self.logger.info(f"Loaded {loaded_count} adapter(s)")
        except Exception as e:
            self.logger.error(f"Error loading adapters: {e}")
