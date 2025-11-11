"""
Mixin providing model unloading operations for Stable Diffusion.

This mixin handles unloading of all SD model components including safety
checker, ControlNet, LoRA, embeddings, Compel, DeepCache, scheduler, and
pipeline to free GPU memory.
"""

import gc

from airunner.components.art.data.lora import Lora
from airunner.components.art.managers.stablediffusion import model_loader
from airunner.enums import ModelStatus, ModelType
from airunner.utils.memory import clear_memory


class SDModelUnloadingMixin:
    """Mixin providing model unloading operations for Stable Diffusion."""

    def _unload_scheduler(self):
        """
        Unload noise scheduler.

        Clears scheduler from pipeline and resets scheduler state.
        """
        self.logger.debug("Unloading scheduler")
        self.scheduler_name = ""
        self.current_scheduler_name = ""
        self.do_change_scheduler = True
        if self._pipe is not None:
            try:
                self._pipe.scheduler = None
            except Exception:
                pass
        self.scheduler = None

    def _unload_controlnet(self):
        """
        Unload ControlNet model and processor.

        Updates model status during unload process.
        """
        self.logger.debug("Unloading controlnet")
        self.change_model_status(ModelType.CONTROLNET, ModelStatus.LOADING)
        self._unload_controlnet_model()
        self._unload_controlnet_processor()
        self.change_model_status(ModelType.CONTROLNET, ModelStatus.UNLOADED)

    def _unload_controlnet_model(self):
        """
        Unload ControlNet model and force garbage collection.

        Removes from both pipeline and instance variables.
        """
        self.logger.debug("Clearing controlnet")
        if self._pipe and hasattr(self._pipe, "controlnet"):
            try:
                if self._pipe.controlnet is not None:
                    del self._pipe.controlnet
                del self._pipe.__controlnet
            except AttributeError:
                pass
            self._pipe.__controlnet = None
        if self._controlnet is not None:
            del self._controlnet
        self._controlnet = None
        # Force garbage collection
        gc.collect()

    def _unload_controlnet_processor(self):
        """
        Unload ControlNet image preprocessor.
        """
        model_loader.unload_controlnet_processor(
            self._controlnet_processor, self.logger
        )
        self._controlnet_processor = None

    def _unload_loras(self):
        """
        Unload all LoRA weights from pipeline.

        Clears both loaded and disabled LoRA tracking.
        """
        self.logger.debug("Unloading lora")
        if self._pipe is not None:
            self._pipe.unload_lora_weights()
        self._loaded_lora = {}
        self._disabled_lora = []

    def _unload_lora(self, lora: Lora):
        """
        Unload single LoRA weight.

        Args:
            lora: LoRA database record to unload.

        If no LoRAs remain loaded, unloads all and clears memory.
        """
        if lora.path in self._loaded_lora:
            self.logger.debug(f"Unloading LORA {lora.path}")
            del self._loaded_lora[lora.path]
        if len(self._loaded_lora) > 0:
            self._set_lora_adapters()
        else:
            self._unload_loras()
            clear_memory(self._device_index)

    def _unload_emebeddings(self):
        """
        Unload all textual inversion embeddings.

        Note: Method name has typo (emebeddings) for compatibility.
        """
        self.logger.debug("Unloading embeddings")
        self._loaded_embeddings = []

    def _unload_embedding(self, embedding):
        """
        Unload single textual inversion embedding.

        Args:
            embedding: Embedding database record with path.
        """
        self._pipe.unload_textual_inversion(embedding.path)
        self._loaded_embeddings.remove(embedding.path)

    def _unload_compel(self):
        """
        Unload Compel processor and textual inversion manager.

        Also clears cached prompt embeddings.
        """
        if (
            self._textual_inversion_manager is not None
            or self._compel_proc is not None
        ):
            self.logger.debug("Unloading compel")
            self._unload_textual_inversion_manager()
            self._unload_compel_proc()
            self._unload_prompt_embeds()

    def _unload_textual_inversion(self):
        """
        Unload textual inversion from pipeline.

        Attempts to unload all textual inversions from pipeline.
        """
        self.logger.info("Attempting to unload textual inversion")
        try:
            self._pipe.unload_textual_inversion()
            self.logger.info("Textual inversion unloaded")
        except Exception as e:
            self.logger.error(f"Failed to unload textual inversion: {e}")

    def _unload_textual_inversion_manager(self):
        """
        Unload textual inversion manager used by Compel.
        """
        self.logger.debug("Unloading textual inversion manager")
        try:
            del self._textual_inversion_manager.pipe
        except TypeError:
            pass
        del self._textual_inversion_manager
        self._textual_inversion_manager = None

    def _unload_compel_proc(self):
        """
        Unload Compel processor.
        """
        self.logger.debug("Unloading compel proc")
        del self._compel_proc
        self._compel_proc = None

    def _unload_prompt_embeds(self):
        """
        Unload cached prompt embeddings.

        Clears all cached prompt and negative prompt embeddings including
        pooled variants for SDXL.
        """
        self.logger.debug("Unloading prompt embeds")
        del self._prompt_embeds
        del self._negative_prompt_embeds
        del self._pooled_prompt_embeds
        del self._negative_pooled_prompt_embeds
        self._prompt_embeds = None
        self._negative_prompt_embeds = None
        self._pooled_prompt_embeds = None
        self._negative_pooled_prompt_embeds = None

    def _unload_deep_cache(self):
        """
        Unload DeepCache helper.

        Disables caching and frees associated memory.
        """
        if self._deep_cache_helper is not None:
            try:
                self._deep_cache_helper.disable()
            except AttributeError:
                pass
        del self._deep_cache_helper
        self._deep_cache_helper = None

    def _unload_generator(self):
        """
        Unload random number generator.
        """
        self.logger.debug("Unloading generator")
        del self._generator
        self._generator = None

    def _unload_safety_checker(self):
        """
        Unload safety checker and feature extractor.

        Frees GPU memory by removing both safety checker and feature extractor models.
        """
        self.logger.debug("Unloading safety checker and feature extractor")

        if self._safety_checker is not None:
            try:
                del self._safety_checker
            except Exception:
                pass
            self._safety_checker = None

        if self._feature_extractor is not None:
            try:
                del self._feature_extractor
            except Exception:
                pass
            self._feature_extractor = None

        self.change_model_status(
            ModelType.SAFETY_CHECKER, ModelStatus.UNLOADED
        )
        gc.collect()
