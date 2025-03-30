from sqlalchemy import Column, Integer, Boolean

from airunner.data.models.base import BaseModel


class MemorySettings(BaseModel):
    __tablename__ = 'memory_settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    use_last_channels = Column(Boolean, default=True)
    use_attention_slicing = Column(Boolean, default=False)
    use_tf32 = Column(Boolean, default=False)
    use_enable_vae_slicing = Column(Boolean, default=True)
    use_accelerated_transformers = Column(Boolean, default=True)
    use_tiled_vae = Column(Boolean, default=True)
    enable_model_cpu_offload = Column(Boolean, default=False)
    use_enable_sequential_cpu_offload = Column(Boolean, default=False)
    use_cudnn_benchmark = Column(Boolean, default=True)
    use_torch_compile = Column(Boolean, default=False)
    use_tome_sd = Column(Boolean, default=True)
    tome_sd_ratio = Column(Integer, default=600)
    move_unused_model_to_cpu = Column(Boolean, default=False)
    unload_unused_models = Column(Boolean, default=True)
    default_gpu_sd = Column(Integer, default=0)
    default_gpu_llm = Column(Integer, default=0)
    default_gpu_tts = Column(Integer, default=0)
    default_gpu_stt = Column(Integer, default=0)
    prevent_unload_on_llm_image_generation = Column(Boolean, default=False)