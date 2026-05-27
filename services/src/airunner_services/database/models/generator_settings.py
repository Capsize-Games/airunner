"""Service-owned art generator settings model."""

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from airunner_services.database.base import BaseModel
from airunner_model.contract_enums import DEFAULT_ART_VERSION, DEFAULT_IMAGE_GENERATOR
from airunner_services.settings import (
    AIRUNNER_DEFAULT_SCHEDULER,
    AIRUNNER_SD_DEFAULT_VAE_PATH,
)


class GeneratorSettings(BaseModel):
    """Persisted art-generation configuration and defaults."""

    __tablename__ = "generator_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_action = Column(String, default="txt2img")
    generator_name = Column(
        String,
        default=DEFAULT_IMAGE_GENERATOR.value,
    )
    quality_effects = Column(String, default="")
    image_preset = Column(String, default="")
    prompt = Column(String, default="")
    negative_prompt = Column(String, default="")
    second_prompt = Column(String, default="")
    second_negative_prompt = Column(String, default="")
    random_seed = Column(Boolean, default=True)
    model_name = Column(String, default="")
    model = Column(Integer, ForeignKey("aimodels.id"), nullable=True)
    aimodel = relationship("AIModels", back_populates="generator_settings")
    custom_path = Column(String, default="")
    vae = Column(String, default=AIRUNNER_SD_DEFAULT_VAE_PATH)
    scheduler = Column(String, default=AIRUNNER_DEFAULT_SCHEDULER)
    variation = Column(Boolean, default=False)
    use_prompt_builder = Column(Boolean, default=False)
    version = Column(String, default=DEFAULT_ART_VERSION.value)
    is_preset = Column(Boolean, default=False)
    use_compel = Column(Boolean, default=True)
    steps = Column(Integer, default=20)
    ddim_eta = Column(Float, default=0.5)
    scale = Column(Integer, default=750)
    seed = Column(BigInteger, default=42)
    prompt_triggers = Column(String, default="")
    strength = Column(Integer, default=50)
    n_samples = Column(Integer, default=1)
    images_per_batch = Column(Integer, default=1)
    clip_skip = Column(Integer, default=0)
    crops_coords_top_left = Column(JSON, default={"x": 0, "y": 0})
    negative_crops_coords_top_left = Column(
        JSON,
        default={"x": 0, "y": 0},
    )
    original_size = Column(
        JSON,
        default={"width": 1024, "height": 1024},
    )
    target_size = Column(
        JSON,
        default={"width": 1024, "height": 1024},
    )
    negative_original_size = Column(
        JSON,
        default={"width": 1024, "height": 1024},
    )
    negative_target_size = Column(
        JSON,
        default={"width": 1024, "height": 1024},
    )
    use_refiner = Column(Boolean, default=False)
    generate_infinite_images = Column(Boolean, default=False)
    dtype = Column(String, default="bfloat16")


__all__ = ["GeneratorSettings"]