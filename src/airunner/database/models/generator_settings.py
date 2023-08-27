from sqlalchemy import Column, String, Integer, Float, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class GeneratorSettings(Base):
    __tablename__ = 'generator_settings'

    id = Column(Integer, primary_key=True)
    generator_type = Column(String)
    prompt = Column(String, default="")
    negative_prompt = Column(String, default="")
    steps = Column(Integer, default=20)
    ddim_eta = Column(Float, default=0.5)
    height = Column(Integer, default=512)
    width = Column(Integer, default=512)
    scale = Column(Float, default=750)
    seed = Column(Integer, default=42)
    random_seed = Column(Boolean, default=True)
    model_var = Column(String, default="Stable Diffusion V2")
    scheduler_var = Column(String, default="Euler a")
    prompt_triggers = Column(String, default="")
    strength = Column(Float, default=50)
    image_guidance_scale = Column(Float, default=150)
    n_samples = Column(Integer, default=1)
    do_upscale_full_image = Column(Boolean, default=True)
    do_upscale_by_active_grid = Column(Boolean, default=False)
    downscale_amount = Column(Integer, default=1)
    deterministic = Column(Boolean, default=False)
    controlnet_var = Column(String, default="")
    enable_controlnet = Column(Boolean, default=False)
    controlnet_guidance_scale = Column(Integer, default=50)
    clip_skip = Column(Integer, default=0)
