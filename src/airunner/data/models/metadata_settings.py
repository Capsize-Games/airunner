from sqlalchemy import Column, Integer, Boolean

from airunner.data.models.base import BaseModel


class MetadataSettings(BaseModel):
    __tablename__ = 'metadata_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    image_export_metadata_prompt = Column(Boolean, default=True)
    image_export_metadata_negative_prompt = Column(Boolean, default=True)
    image_export_metadata_scale = Column(Boolean, default=True)
    image_export_metadata_seed = Column(Boolean, default=True)
    image_export_metadata_steps = Column(Boolean, default=True)
    image_export_metadata_ddim_eta = Column(Boolean, default=True)
    image_export_metadata_iterations = Column(Boolean, default=True)
    image_export_metadata_samples = Column(Boolean, default=True)
    image_export_metadata_model = Column(Boolean, default=True)
    image_export_metadata_model_branch = Column(Boolean, default=True)
    image_export_metadata_scheduler = Column(Boolean, default=True)
    image_export_metadata_strength = Column(Boolean, default=True)
    image_export_metadata_clip_skip = Column(Boolean, default=True)
    image_export_metadata_version = Column(Boolean, default=True)
    image_export_metadata_lora = Column(Boolean, default=True)
    image_export_metadata_embeddings = Column(Boolean, default=True)
    image_export_metadata_timestamp = Column(Boolean, default=True)
    image_export_metadata_controlnet = Column(Boolean, default=True)
    export_metadata = Column(Boolean, default=True)
    import_metadata = Column(Boolean, default=True)
