# src/airunner/alembic/env.py
import os

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, MetaData
from alembic import context

config = context.config
db_path = os.path.expanduser("~/.local/share/airunner/data/airunner.db")
config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

# Import your models here
from airunner.data.models.settings_models import (
    Conversation, Message, Summary,
    ApplicationSettings, ActiveGridSettings, ControlnetSettings,
    ImageToImageSettings, OutpaintSettings, DrawingPadSettings, MetadataSettings,
    GeneratorSettings, LLMGeneratorSettings, TTSSettings,
    SpeechT5Settings, EspeakSettings, STTSettings, Schedulers, BrushSettings,
    GridSettings, PathSettings, MemorySettings, Chatbot, TargetFiles, TargetDirectories,
    AIModels, ShortcutKeys, Lora, SavedPrompt, Embedding, PromptTemplate, ControlnetModel,
    FontSetting, PipelineModel, WindowSettings
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# Create a single MetaData object
metadata = MetaData()

# Bind all models to the single MetaData object
for model in [
    ApplicationSettings, ActiveGridSettings, ControlnetSettings,
    ImageToImageSettings, OutpaintSettings, DrawingPadSettings, MetadataSettings,
    GeneratorSettings, LLMGeneratorSettings, TTSSettings,
    SpeechT5Settings, EspeakSettings, STTSettings, Schedulers, BrushSettings,
    GridSettings, PathSettings, MemorySettings, Chatbot, TargetFiles, TargetDirectories,
    AIModels, ShortcutKeys, Lora, SavedPrompt, Embedding, PromptTemplate, ControlnetModel,
    FontSetting, PipelineModel, WindowSettings, Conversation, Message, Summary
]:
    model.metadata = metadata

# Combine all model's MetaData objects here
target_metadata = metadata

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
