from airunner.aihandler.logger import Logger
from compel import Compel, DiffusersTextualInversionManager

from airunner.utils import clear_memory


class CompelMixin:
    def __init__(self):
        self._compel_proc = None
        self._compel_proc = None
        self._prompt_embeds = None
        self._prompt_embeds = None
        self._negative_prompt_embeds = None
        self._negative_prompt_embeds = None
        self._prompt_embeds = None
        self._negative_prompt_embeds = None

    @property
    def compel_proc(self):
        if not self._compel_proc:
            textual_inversion_manager = DiffusersTextualInversionManager(self.pipe)
            self._compel_proc = Compel(
                tokenizer=self.pipe.tokenizer,
                text_encoder=self.pipe.text_encoder,
                truncate_long_prompts=False,
                textual_inversion_manager=textual_inversion_manager
            )
        return self._compel_proc

    @compel_proc.setter
    def compel_proc(self, value):
        self._compel_proc = value

    @property
    def prompt_embeds(self):
        # try:
        #     if self._prompt_embeds is not None:
        #         shape = self._prompt_embeds.shape
        #         size = shape[0]
        #         if size == 1:
        #             self.logger.error("Prompt embeds are not valid, clearing")
        #             self._prompt_embeds = None
        #     if self._prompt_embeds is None:
        #         self.load_prompt_embeds()
        # except Exception as e:
        #     self.logger.error(f"Error loading prompt embeds: {e}")
        #     self._prompt_embeds = None
        if self._prompt_embeds is None:
            self.load_prompt_embeds()
        return self._prompt_embeds

    @prompt_embeds.setter
    def prompt_embeds(self, value):
        self._prompt_embeds = value

    @property
    def negative_prompt_embeds(self):
        # if self._negative_prompt_embeds is not None:
        #     shape = self._negative_prompt_embeds.shape
        #     size = shape[0]
        #     if size == 1:
        #         self.logger.error("Negative prompt embeds are not valid, clearing")
        #         self._negative_prompt_embeds = None
        if self._negative_prompt_embeds is None:
            self.load_prompt_embeds()
        return self._negative_prompt_embeds

    @negative_prompt_embeds.setter
    def negative_prompt_embeds(self, value):
        self._negative_prompt_embeds = value

    def clear_prompt_embeds(self):
        self.logger.info("Clearing prompt embeds")
        self._prompt_embeds = None
        self._negative_prompt_embeds = None

    def load_prompt_embeds(self):
        self.logger.info("Loading prompt embeds")
        self.compel_proc = None
        clear_memory()
        prompt = self.prompt if self.prompt else ""
        negative_prompt = self.negative_prompt if self.negative_prompt else ""

        # check if prompt is string
        if isinstance(prompt, str):
            prompt_embeds = self.compel_proc.build_conditioning_tensor(prompt)
            negative_prompt_embeds = self.compel_proc.build_conditioning_tensor(negative_prompt)
        else:
            prompt_embeds = self.compel_proc(prompt)
            negative_prompt_embeds = self.compel_proc(negative_prompt)
        [prompt_embeds, negative_prompt_embeds] = self.compel_proc.pad_conditioning_tensors_to_same_length([prompt_embeds, negative_prompt_embeds])
        self.prompt_embeds = prompt_embeds
        self.negative_prompt_embeds = negative_prompt_embeds

        if prompt_embeds is not None:
            self.prompt_embeds.to(self.device)

        if negative_prompt_embeds is not None:
            self.negative_prompt_embeds.to(self.device)
