"""
Mixin providing model unloading operations for Stable Diffusion.

This mixin handles unloading of all SD model components including safety
checker, Compel, DeepCache, scheduler, and
pipeline to free GPU memory.
"""

import gc

from airunner_services.art.runtime_enums import ModelStatus, ModelType


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

    def _unload_compel(self):
        """
        Unload Compel processor.

        Also clears cached prompt embeddings.
        """
        if self._compel_proc is not None:
            self.logger.debug("Unloading compel")
            self._unload_compel_proc()
            self._unload_prompt_embeds()

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
        pooled variants.
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
