from airunner.aihandler.logger import Logger
from compel import Compel, DiffusersTextualInversionManager

from airunner.utils import clear_memory


class CompelMixin:
    def __init__(self):
        self._prompt_embeds = None
        self._negative_prompt_embeds = None
        self.compel_proc = None

    @property
    def prompt_embeds(self):
        return self._prompt_embeds

    @prompt_embeds.setter
    def prompt_embeds(self, value):
        self._prompt_embeds = value

    @property
    def negative_prompt_embeds(self):
        return self._negative_prompt_embeds

    @negative_prompt_embeds.setter
    def negative_prompt_embeds(self, value):
        self._negative_prompt_embeds = value

    def clear_prompt_embeds(self):
        self.logger.info("Clearing prompt embeds")
        self._prompt_embeds = None
        self._negative_prompt_embeds = None

    _current_prompt = ""
    _current_negative_prompt = ""

    def load_prompt_embeds(self, do_reload=True):
        self.logger.info("Loading prompt embeds")
        prompt = self.prompt if self.prompt else ""
        negative_prompt = self.negative_prompt if self.negative_prompt else ""
        try:
            if self.compel_proc is None:
                textual_inversion_manager = DiffusersTextualInversionManager(self.pipe)
                self.compel_proc = Compel(
                    tokenizer=self.pipe.tokenizer,
                    text_encoder=self.pipe.text_encoder,
                    truncate_long_prompts=False,
                    textual_inversion_manager=textual_inversion_manager,
                    dtype_for_device_getter=lambda _x: self.data_type,
                    device=self.pipe.device
                )
        except Exception as e:
            self.logger.error(f"Error creating compel proc: {e}")
            return None
        compel_proc = self.compel_proc
        clear_memory()
        self._current_prompt = prompt
        self._current_negative_prompt = negative_prompt

        prompt_embeds = None
        negative_prompt_embeds = None

        # check if prompt is string
        if isinstance(prompt, str):
            try:
                prompt_embeds = compel_proc.build_conditioning_tensor(prompt)
            except RuntimeError as e:
                self.logger.error("Error building prompt embeds")
                self.logger.error(e)

            try:
                negative_prompt_embeds = compel_proc.build_conditioning_tensor(negative_prompt)
            except RuntimeError as e:
                self.logger.error("Error building negative prompt embeds")
                self.logger.error(e)
        else:
            try:
                prompt_embeds = compel_proc(prompt)
            except RuntimeError as e:
                self.logger.error("Error building prompt embeds")
                self.logger.error(e)
            try:
                negative_prompt_embeds = compel_proc(negative_prompt)
            except RuntimeError as e:
                self.logger.error("Error building negative prompt embeds")
                self.logger.error(e)

        if prompt_embeds is None or negative_prompt_embeds is None:
            if do_reload:
                return self.load_prompt_embeds(do_reload=False)
            else:
                self.logger.error("Prompt embeds are None")
                return

        [
            prompt_embeds,
            negative_prompt_embeds
        ] = compel_proc.pad_conditioning_tensors_to_same_length([
            prompt_embeds,
            negative_prompt_embeds
        ])
        self.prompt_embeds = prompt_embeds
        self.negative_prompt_embeds = negative_prompt_embeds

        if prompt_embeds is not None:
            self.logger.info(f"Moving prompt embeds to device: {self.device}")
            self.prompt_embeds.to(self.device)

        if negative_prompt_embeds is not None:
            self.negative_prompt_embeds.to(self.device)
