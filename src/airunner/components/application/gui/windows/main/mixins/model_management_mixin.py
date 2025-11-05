"""Mixin providing AI model, LoRA, and embedding management operations."""

from typing import List, Optional
from airunner.components.data.session_manager import session_scope
from airunner.components.art.data.ai_models import AIModels
from airunner.components.art.data.lora import Lora
from airunner.components.art.data.embedding import Embedding
from airunner.components.application.data import table_to_class


class ModelManagementMixin:
    """Mixin for managing AI models, LoRAs, and embeddings."""

    def update_ai_models(self, models: List[AIModels]) -> None:
        """Update multiple AI models.

        Args:
            models: List of AIModels instances to update.
        """
        for model in models:
            self.update_ai_model(model)
        self._notify_setting_updated(None, None, None)

    def update_ai_model(self, model: AIModels) -> None:
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
        model_class_ = table_to_class.get(table_name)
        if model_class_ is None:
            self.logger.error(f"Model class for {table_name} not found")
            return

        setting = self._get_latest_setting(model_class_)
        if setting:
            model_class_.objects.update(setting.id, **{column_name: val})
            self._notify_setting_updated(table_name, column_name, val)
        else:
            self.logger.error("Failed to update settings: No setting found")

    def update_lora(self, lora: Lora) -> None:
        """Update or create a LoRA.

        Args:
            lora: Lora instance to update or create.
        """
        existing = self._find_lora_by_name(lora.name)

        if existing:
            self._update_existing_lora(existing, lora)
        else:
            self._create_new_lora(lora)

        self._notify_setting_updated(None, None, None)

    def update_loras(self, loras: List[Lora]) -> None:
        """Update multiple LoRAs.

        Args:
            loras: List of Lora instances to update.
        """
        for lora in loras:
            existing = self._find_lora_by_name(lora.name)

            if existing:
                self._update_existing_lora(existing, lora)
            else:
                self._create_new_lora(lora)

        self._notify_setting_updated(None, None, None)

    def update_embeddings(self, embeddings: List[Embedding]) -> None:
        """Update multiple embeddings.

        Args:
            embeddings: List of Embedding instances to update.
        """
        for embedding in embeddings:
            existing = self._find_existing_embedding(embedding)

            if existing:
                self._copy_embedding_attributes(existing, embedding)
                existing.save()
            else:
                self._create_new_embedding(embedding)

        self._notify_setting_updated(None, None, None)

    @staticmethod
    def delete_lora(lora: Lora) -> None:
        """Delete a LoRA by name.

        Args:
            lora: Lora instance to delete.
        """
        loras = Lora.objects.filter_by(name=lora.name)
        for lora_instance in loras:
            lora_instance.delete()

    @staticmethod
    def delete_lora_by_name(lora_name: str, version: str) -> None:
        """Delete LoRA by name and version.

        Args:
            lora_name: Name of the LoRA.
            version: Version of the LoRA.
        """
        loras = Lora.objects.filter_by(name=lora_name, version=version)
        for lora in loras:
            lora.delete()

    @staticmethod
    def delete_embedding(embedding: Embedding) -> None:
        """Delete an embedding.

        Args:
            embedding: Embedding instance to delete.
        """
        Embedding.objects.delete_by(
            name=embedding.name,
            path=embedding.path,
            branch=embedding.branch,
            version=embedding.version,
            category=embedding.category,
            pipeline_action=embedding.pipeline_action,
            enabled=embedding.enabled,
            model_type=embedding.model_type,
            is_default=embedding.is_default,
        )

    @staticmethod
    def get_lora_by_name(name: str) -> Optional[Lora]:
        """Get LoRA by name.

        Args:
            name: Name of the LoRA.

        Returns:
            Lora instance or None.
        """
        return Lora.objects.filter_by_first(name=name)

    @staticmethod
    def add_lora(lora: Lora) -> None:
        """Add a new LoRA.

        Args:
            lora: Lora instance to add.
        """
        lora.save()

    @staticmethod
    def create_lora(lora: Lora) -> None:
        """Create a new LoRA.

        Args:
            lora: Lora instance to create.
        """
        lora.save()

    @staticmethod
    def get_embedding_by_name(name: str) -> Optional[Embedding]:
        """Get embedding by name.

        Args:
            name: Name of the embedding.

        Returns:
            Embedding instance or None.
        """
        return Embedding.objects.filter_by_first(name=name)

    @staticmethod
    def add_embedding(embedding: Embedding) -> None:
        """Add a new embedding.

        Args:
            embedding: Embedding instance to add.
        """
        embedding.save()

    def _find_existing_ai_model(self, model: AIModels) -> Optional[AIModels]:
        """Find existing AI model by attributes.

        Args:
            model: AIModels instance to search for.

        Returns:
            Existing model or None.
        """
        return AIModels.objects.filter_by_first(
            name=model.name,
            path=model.path,
            branch=model.branch,
            version=model.version,
            category=model.category,
            pipeline_action=model.pipeline_action,
            enabled=model.enabled,
            model_type=model.model_type,
            is_default=model.is_default,
        )

    def _update_existing_ai_model(
        self, existing: AIModels, model: AIModels
    ) -> None:
        """Update existing AI model in database.

        Args:
            existing: Existing model dataclass.
            model: New model data.
        """
        with session_scope() as session:
            orm_instance = self._get_orm_instance(session, existing)

            if orm_instance:
                self._copy_model_attributes(orm_instance, model)
                session.commit()
            else:
                self._create_ai_model_in_session(session, model)

    def _create_new_ai_model(self, model: AIModels) -> None:
        """Create new AI model.

        Args:
            model: AIModels instance to create.
        """
        new_model = AIModels(
            name=model.name,
            path=model.path,
            branch=model.branch,
            version=model.version,
            category=model.category,
            pipeline_action=model.pipeline_action,
            enabled=model.enabled,
            model_type=model.model_type,
            is_default=model.is_default,
        )
        new_model.save()

    def _get_orm_instance(
        self, session, existing: AIModels
    ) -> Optional[AIModels]:
        """Get ORM instance from dataclass.

        Args:
            session: Database session.
            existing: Existing dataclass instance.

        Returns:
            ORM instance or None.
        """
        return (
            session.query(AIModels).filter(AIModels.id == existing.id).first()
        )

    def _copy_model_attributes(
        self, target: AIModels, source: AIModels
    ) -> None:
        """Copy attributes from source to target model.

        Args:
            target: Target model to update.
            source: Source model with new values.
        """
        for key in source.__dict__.keys():
            if key not in ("_sa_instance_state", "id"):
                setattr(target, key, getattr(source, key))

    def _create_ai_model_in_session(self, session, model: AIModels) -> None:
        """Create AI model in session.

        Args:
            session: Database session.
            model: Model data.
        """
        new_model = AIModels(
            name=model.name,
            path=model.path,
            branch=model.branch,
            version=model.version,
            category=model.category,
            pipeline_action=model.pipeline_action,
            enabled=model.enabled,
            model_type=model.model_type,
            is_default=model.is_default,
        )
        session.add(new_model)
        session.commit()

    def _find_lora_by_name(self, name: str) -> Optional[Lora]:
        """Find LoRA by name.

        Args:
            name: LoRA name.

        Returns:
            Lora instance or None.
        """
        return Lora.objects.filter_by_first(name=name)

    def _update_existing_lora(self, existing: Lora, lora: Lora) -> None:
        """Update existing LoRA.

        Args:
            existing: Existing LoRA.
            lora: New LoRA data.
        """
        self._copy_lora_attributes(existing, lora)
        Lora.objects.update(existing.id, **existing.__dict__)

    def _create_new_lora(self, lora: Lora) -> None:
        """Create new LoRA instance.

        Args:
            lora: LoRA data.
        """
        new_lora = Lora(
            name=lora.name,
            path=getattr(lora, "path", ""),
            branch=getattr(lora, "branch", ""),
            version=getattr(lora, "version", ""),
            category=getattr(lora, "category", ""),
            pipeline_action=getattr(lora, "pipeline_action", ""),
            enabled=getattr(lora, "enabled", True),
            model_type=getattr(lora, "model_type", ""),
            is_default=getattr(lora, "is_default", False),
        )
        new_lora.save()

    def _copy_lora_attributes(self, target: Lora, source: Lora) -> None:
        """Copy LoRA attributes.

        Args:
            target: Target LoRA.
            source: Source LoRA.
        """
        for key in source.__dict__.keys():
            if key != "_sa_instance_state":
                setattr(target, key, getattr(source, key))

    def _find_existing_embedding(
        self, embedding: Embedding
    ) -> Optional[Embedding]:
        """Find existing embedding.

        Args:
            embedding: Embedding to search for.

        Returns:
            Existing embedding or None.
        """
        return Embedding.objects.filter_by_first(
            name=embedding.name,
            path=embedding.path,
            branch=embedding.branch,
            version=embedding.version,
            category=embedding.category,
            pipeline_action=embedding.pipeline_action,
            enabled=embedding.enabled,
            model_type=embedding.model_type,
            is_default=embedding.is_default,
        )

    def _create_new_embedding(self, embedding: Embedding) -> None:
        """Create new embedding.

        Args:
            embedding: Embedding data.
        """
        new_embedding = Embedding(
            name=embedding.name,
            path=embedding.path,
            branch=embedding.branch,
            version=embedding.version,
            category=embedding.category,
            pipeline_action=embedding.pipeline_action,
            enabled=embedding.enabled,
            model_type=embedding.model_type,
            is_default=embedding.is_default,
        )
        new_embedding.save()

    def _copy_embedding_attributes(
        self, target: Embedding, source: Embedding
    ) -> None:
        """Copy embedding attributes.

        Args:
            target: Target embedding.
            source: Source embedding.
        """
        for key in source.__dict__.keys():
            if key != "_sa_instance_state":
                setattr(target, key, getattr(source, key))

    def _get_latest_setting(self, model_class_):
        """Get latest setting for model class.

        Args:
            model_class_: Model class.

        Returns:
            Latest setting or None.
        """
        return model_class_.objects.order_by(model_class_.id.desc()).first()

    def _notify_setting_updated(self, table_name, column_name, val) -> None:
        """Notify that a setting was updated.

        Args:
            table_name: Table name.
            column_name: Column name.
            val: New value.
        """
        # Placeholder for actual notification implementation
