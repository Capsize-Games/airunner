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

    def to_dict(self):
        return {
            "use_last_channels": self.use_last_channels,
            "use_attention_slicing": self.use_attention_slicing,
            "use_tf32": self.use_tf32,
            "use_enable_vae_slicing": self.use_enable_vae_slicing,
            "use_accelerated_transformers": self.use_accelerated_transformers,
            "use_tiled_vae": self.use_tiled_vae,
            "enable_model_cpu_offload": self.enable_model_cpu_offload,
            "use_enable_sequential_cpu_offload": self.use_enable_sequential_cpu_offload,
            "use_cudnn_benchmark": self.use_cudnn_benchmark,
            "use_torch_compile": self.use_torch_compile,
            "use_tome_sd": self.use_tome_sd,
            "tome_sd_ratio": self.tome_sd_ratio,
            "move_unused_model_to_cpu": self.move_unused_model_to_cpu,
            "unload_unused_models": self.unload_unused_models,
            "default_gpu_sd": self.default_gpu_sd,
            "default_gpu_llm": self.default_gpu_llm,
            "default_gpu_tts": self.default_gpu_tts,
            "default_gpu_stt": self.default_gpu_stt
        }
