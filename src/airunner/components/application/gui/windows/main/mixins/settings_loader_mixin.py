"""Mixin providing database loading operations for settings models."""

from typing import Type, Any, Optional, List

from sqlalchemy.orm import joinedload, make_transient
from sqlalchemy import inspect as sa_inspect

from airunner.components.data.session_manager import session_scope
from airunner.components.application.gui.windows.main.settings_model_factory import (
    get_settings_model,
)
from airunner.utils.application.get_logger import get_logger
from airunner.settings import AIRUNNER_LOG_LEVEL


class SettingsLoaderMixin:
    """Provides static methods for loading settings and models from database."""

    @staticmethod
    def load_schedulers() -> List[Any]:
        """Load all scheduler configurations.

        Returns:
            List of Schedulers instances.
        """
        Schedulers = get_settings_model("Schedulers")
        return Schedulers.objects.all()

    @staticmethod
    def load_ai_models() -> List[Any]:
        """Load all AI model configurations.

        Returns:
            List of AIModels instances.
        """
        AIModels = get_settings_model("AIModels")
        return AIModels.objects.all()

    @staticmethod
    def load_chatbots() -> List[Any]:
        """Load all chatbot instances.

        Returns:
            List of Chatbot instances.
        """
        Chatbot = get_settings_model("Chatbot")
        return Chatbot.objects.all()

    @staticmethod
    def load_saved_prompts() -> List[Any]:
        """Load all saved prompt configurations.

        Returns:
            List of SavedPrompt instances.
        """
        SavedPrompt = get_settings_model("SavedPrompt")
        return SavedPrompt.objects.all()

    @staticmethod
    def load_font_settings() -> List[Any]:
        """Load all font configurations.

        Returns:
            List of FontSetting instances.
        """
        FontSetting = get_settings_model("FontSetting")
        return FontSetting.objects.all()

    @staticmethod
    def load_prompt_templates() -> List[Any]:
        """Load all prompt template configurations.

        Returns:
            List of PromptTemplate instances.
        """
        PromptTemplate = get_settings_model("PromptTemplate")
        return PromptTemplate.objects.all()

    @staticmethod
    def load_controlnet_models() -> List[Any]:
        """Load all ControlNet model configurations.

        Returns:
            List of ControlnetModel instances.
        """
        ControlnetModel = get_settings_model("ControlnetModel")
        return ControlnetModel.objects.all()

    @staticmethod
    def load_pipelines() -> List[Any]:
        """Load all pipeline configurations.

        Returns:
            List of PipelineModel instances.
        """
        PipelineModel = get_settings_model("PipelineModel")
        return PipelineModel.objects.all()

    @staticmethod
    def load_shortcut_keys() -> List[Any]:
        """Load all keyboard shortcut configurations.

        Returns:
            List of ShortcutKeys instances.
        """
        from airunner.components.application.data import ShortcutKeys

        return ShortcutKeys.objects.all()

    @staticmethod
    def load_lora() -> List[Any]:
        """Load all LoRA configurations.

        Returns:
            List of Lora instances.
        """
        Lora = get_settings_model("Lora")
        return Lora.objects.all()

    @staticmethod
    def load_settings_from_db(
        model_class_: Type[Any], eager_load: Optional[List[str]] = None
    ) -> Any:
        """Load settings instance from database, creating if not exists.

        Args:
            model_class_: SQLAlchemy model class for the settings table.
            eager_load: Optional list of relationship names to eager-load.

        Returns:
            Instance of the settings model.
        """
        try:
            with session_scope() as session:
                settings_instance = SettingsLoaderMixin._query_settings(
                    session, model_class_, eager_load
                )

                if settings_instance is None:
                    settings_instance = SettingsLoaderMixin._create_settings(
                        session, model_class_, eager_load
                    )

                if settings_instance:
                    SettingsLoaderMixin._detach_instance(
                        settings_instance, model_class_, eager_load
                    )

                return settings_instance

        except Exception as e:
            return SettingsLoaderMixin._handle_load_error(e, model_class_)

    @staticmethod
    def _query_settings(
        session: Any, model_class_: Type[Any], eager_load: Optional[List[str]]
    ) -> Optional[Any]:
        """Query settings from database with optional eager loading.

        Args:
            session: Database session.
            model_class_: Model class to query.
            eager_load: Relationships to eager-load.

        Returns:
            Settings instance or None.
        """
        query = session.query(model_class_)

        if eager_load:
            for relation in eager_load:
                query = SettingsLoaderMixin._add_joinedload(
                    query, model_class_, relation
                )

        return query.first()

    @staticmethod
    def _add_joinedload(
        query: Any, model_class_: Type[Any], relation: str
    ) -> Any:
        """Add joinedload option to query for a relationship.

        Args:
            query: Base query object.
            model_class_: Model class being queried.
            relation: Relationship name to eager-load.

        Returns:
            Query with joinedload added.
        """
        try:
            relation_attr = getattr(model_class_, relation, None)
            if relation_attr is not None:
                return query.options(joinedload(relation_attr))
        except Exception as e:
            logger = get_logger("AI Runner SettingsMixin", AIRUNNER_LOG_LEVEL)
            logger.warning(
                f"Could not eager load {relation} for "
                f"{model_class_.__name__}: {e}"
            )
        return query

    @staticmethod
    def _create_settings(
        session: Any, model_class_: Type[Any], eager_load: Optional[List[str]]
    ) -> Optional[Any]:
        """Create new settings instance in database.

        Args:
            session: Database session.
            model_class_: Model class to create instance of.
            eager_load: Relationships to load after creation.

        Returns:
            Created settings instance or None.
        """
        logger = get_logger("AI Runner SettingsMixin", AIRUNNER_LOG_LEVEL)
        logger.info(
            f"No settings found for {model_class_.__name__}, "
            "creating new entry."
        )

        settings_instance = model_class_()
        session.add(settings_instance)
        session.commit()

        if settings_instance.id is None:
            logger.error(
                f"Failed to get ID for new {model_class_.__name__} "
                "instance after commit."
            )
            return None

        if eager_load:
            return SettingsLoaderMixin._reload_with_relationships(
                session, model_class_, settings_instance.id, eager_load
            )

        return settings_instance

    @staticmethod
    def _reload_with_relationships(
        session: Any,
        model_class_: Type[Any],
        instance_id: int,
        eager_load: List[str],
    ) -> Optional[Any]:
        """Reload instance with relationships eager-loaded.

        Args:
            session: Database session.
            model_class_: Model class to query.
            instance_id: ID of instance to reload.
            eager_load: Relationships to eager-load.

        Returns:
            Reloaded instance with relationships.
        """
        query = session.query(model_class_).filter(
            model_class_.id == instance_id
        )

        for relation in eager_load:
            query = SettingsLoaderMixin._add_joinedload(
                query, model_class_, relation
            )

        return query.first()

    @staticmethod
    def _detach_instance(
        instance: Any, model_class_: Type[Any], eager_load: Optional[List[str]]
    ) -> None:
        """Detach instance from session to prevent DetachedInstanceError.

        Args:
            instance: Instance to detach.
            model_class_: Model class for inspection.
            eager_load: Relationships to force-load before detaching.
        """
        try:
            # Force-load all scalar attributes
            mapper = sa_inspect(model_class_)
            for attr in mapper.column_attrs:
                _ = getattr(instance, attr.key)

            # Force-load requested relationships
            if eager_load:
                for relation in eager_load:
                    try:
                        _ = getattr(instance, relation)
                    except Exception:
                        pass

            make_transient(instance)
        except Exception:
            # Fallback: If make_transient fails, instance may already be detached
            # or session is in an invalid state. Log and continue.
            logger = get_logger("AI Runner SettingsMixin", AIRUNNER_LOG_LEVEL)
            logger.debug(
                f"Could not make instance of {model_class_.__name__} transient"
            )

    @staticmethod
    def _handle_load_error(error: Exception, model_class_: Type[Any]) -> Any:
        """Handle error during settings loading.

        Args:
            error: Exception that occurred.
            model_class_: Model class that failed to load.

        Returns:
            Fallback default instance.

        Raises:
            RuntimeError: If even fallback instance creation fails.
        """
        logger = get_logger("AI Runner SettingsMixin", AIRUNNER_LOG_LEVEL)
        logger.error(
            f"Error loading settings for {model_class_.__name__}: {error}. "
            "Attempting to return a new transient default instance.",
            exc_info=True,
        )

        try:
            return model_class_()
        except Exception as e_fallback:
            logger.critical(
                f"CRITICAL: Failed to create fallback instance for "
                f"{model_class_.__name__} during error handling. "
                f"Fallback error: {e_fallback}",
                exc_info=True,
            )
            raise RuntimeError(
                f"Fatal error in settings: Could not instantiate default "
                f"for {model_class_.__name__} after initial load failed. "
                f"Original error: {error}"
            ) from e_fallback
