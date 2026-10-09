"""Mixin providing AI model and embedding management operations."""

from typing import Any, List, Optional

from airunner.daemon_client.resource_store import TABLE_TO_RESOURCE as table_to_resource


class ModelManagementMixin:
    """Mixin for managing AI models and embeddings."""

    def update_ai_models(self, models: List[Any]) -> None:
        """Update multiple AI models.

        Args:
            models: List of AIModels instances to update.
        """
        for model in models:
            self.update_ai_model(model)
        self._notify_setting_updated(None, None, None)

    def update_ai_model(self, model: Any) -> None:
        """Update or create a single AI model.

        Args:
            model: AIModels instance to update or create.
        """
        existing = self._find_existing_ai_model(model)

        if existing:
            self._update_existing_ai_model(existing, model)
        else:
            self._create_new_ai_model(model)

        self._notify_setting_updated(None, None, None)

    def update_setting_by_table_name(
        self, table_name: str, column_name: str, val
    ) -> None:
        """Update a setting by table name.

        Args:
            table_name: Database table name.
            column_name: Column to update.
            val: New value.
        """
        # Layer-scoped settings must flow through the layer-aware update paths
        # so the per-layer cache is invalidated correctly. Otherwise, callers
        # would update the DB row while the cached object stays stale.
        layer_tables = {
            "image_to_image_settings": self.update_image_to_image_settings,
            "outpaint_settings": self.update_outpaint_settings,
            "drawing_pad_settings": self.update_drawing_pad_settings,
        }

        lower_table = table_name.lower() if table_name else ""
        if lower_table in layer_tables:
            layer_tables[lower_table](**{column_name: val})
            return

        resource_name = table_to_resource.get(table_name)
        if resource_name is None:
            self.logger.error(f"Resource for {table_name} not found")
            return

        setting = self._get_latest_setting(resource_name)
        if setting:
            self.resource_store.update(setting.resource_name, setting.id, {column_name: val})
            self._notify_setting_updated(resource_name, column_name, val)
        else:
            self.logger.error("Failed to update settings: No setting found")

    def update_embeddings(self, embeddings: List[Any]) -> None:
        """Update multiple embeddings.

        Args:
            embeddings: List of Embedding instances to update.
        """
        for embedding in embeddings:
            existing = self._find_existing_embedding(embedding)

            if existing:
                self.resource_store.update(
                    "Embedding",
                    existing.id,
                    self._record_values(embedding),
                )
            else:
                self._create_new_embedding(embedding)

        self._notify_setting_updated(None, None, None)

    def delete_embedding(self, embedding: Any) -> None:
        """Delete an embedding.

        Args:
            embedding: Embedding instance to delete.
        """
        self.resource_store.delete_many(
            "Embedding",
            filters=self._record_values(embedding),
        )

    def get_embedding_by_name(self, name: str) -> Optional[Any]:
        """Get embedding by name.

        Args:
            name: Name of the embedding.

        Returns:
            Embedding instance or None.
        """
        return self.resource_store.first("Embedding", filters={"name": name})

    def add_embedding(self, embedding: Any) -> None:
        """Add a new embedding.

        Args:
            embedding: Embedding instance to add.
        """
        self.resource_store.create("Embedding", self._record_values(embedding))

    def _find_existing_ai_model(self, model: Any) -> Optional[Any]:
        """Find existing AI model by attributes.

        Args:
            model: AIModels instance to search for.

        Returns:
            Existing model or None.
        """
        return self.resource_store.first(
            "AIModels",
            filters=self._record_values(model),
        )

    def _update_existing_ai_model(
        self, existing: Any, model: Any
    ) -> None:
        """Update one existing AI model through the daemon manager.

        Args:
            existing: Existing model dataclass.
            model: New model data.
        """
        self.resource_store.update(
            "AIModels",
            existing.id,
            self._record_values(model),
        )

    def _create_new_ai_model(self, model: Any) -> None:
        """Create new AI model.

        Args:
            model: AIModels instance to create.
        """
        self.resource_store.create("AIModels", self._record_values(model))

    def _find_existing_embedding(
        self, embedding: Any
    ) -> Optional[Any]:
        """Find existing embedding.

        Args:
            embedding: Embedding to search for.

        Returns:
            Existing embedding or None.
        """
        return self.resource_store.first(
            "Embedding",
            filters=self._record_values(embedding),
        )

    def _create_new_embedding(self, embedding: Any) -> None:
        """Create new embedding.

        Args:
            embedding: Embedding data.
        """
        self.resource_store.create("Embedding", self._record_values(embedding))

    @staticmethod
    def _record_values(record) -> dict:
        """Return serializable column values for one transient model."""
        values = getattr(record, "to_dict", lambda: dict(record.__dict__))()
        values.pop("id", None)
        values.pop("_sa_instance_state", None)
        return values

    def _get_latest_setting(self, resource_name: str):
        """Get latest setting for model class.

        Args:
            resource_name: Resource name.

        Returns:
            Latest setting or None.
        """
        if self.resource_store.is_singleton(resource_name):
            return self.resource_store.get_singleton(resource_name)
        return self.resource_store.first(
            resource_name,
            order_by=[{"field": "id", "direction": "desc"}],
        )
