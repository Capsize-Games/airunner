# src/airunner/alembic/env.py

from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Import your models here
from airunner.aihandler.models.settings_models import Conversation, Message, Summary
from airunner.aihandler.models.settings_models import (
    ApplicationSettings,
    ActiveGridSettings,
    CanvasSettings,
    ControlnetSettings,
    ImageToImageSettings,
    OutpaintSettings,
    DrawingPadSettings,
    MetadataSettings,
    GeneratorSettings,
    ControlnetImageSettings,
    LLMGeneratorSettings,
    TTSSettings,
    SpeechT5Settings,
    EspeakSettings,
    STTSettings,
    Schedulers,
    BrushSettings,
    GridSettings,
    PathSettings,
    MemorySettings,
    Chatbot,
    TargetFiles,
    TargetDirectories,
    AIModels,
    ShortcutKeys,
    Lora,
    SavedPrompt,
    Embedding,
    PromptTemplate,
    ControlnetModel,
    FontSetting,
    PipelineModel,
    WindowSettings,
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# Combine all model's MetaData objects here
target_metadata = [
    ApplicationSettings.metadata,
    ActiveGridSettings.metadata,
    CanvasSettings.metadata,
    ControlnetSettings.metadata,
    ImageToImageSettings.metadata,
    OutpaintSettings.metadata,
    DrawingPadSettings.metadata,
    MetadataSettings.metadata,
    GeneratorSettings.metadata,
    ControlnetImageSettings.metadata,
    LLMGeneratorSettings.metadata,
    TTSSettings.metadata,
    SpeechT5Settings.metadata,
    EspeakSettings.metadata,
    STTSettings.metadata,
    Schedulers.metadata,
    BrushSettings.metadata,
    GridSettings.metadata,
    PathSettings.metadata,
    MemorySettings.metadata,
    Chatbot.metadata,
    TargetFiles.metadata,
    TargetDirectories.metadata,
    AIModels.metadata,
    ShortcutKeys.metadata,
    Lora.metadata,
    SavedPrompt.metadata,
    Embedding.metadata,
    PromptTemplate.metadata,
    ControlnetModel.metadata,
    FontSetting.metadata,
    PipelineModel.metadata,
    WindowSettings.metadata,
    Conversation.metadata,
    Message.metadata,
    Summary.metadata,
]

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline():
    """Run migrations in 'offline' mode.
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode.
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
