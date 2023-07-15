from aihandler.logger import logger
from compel import Compel, DiffusersTextualInversionManager


class CompelMixin:
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
        # reset prompt_embeds if deterministic_generation is True and it has a size of 1
        if self._prompt_embeds is not None and self.deterministic_generation:
            shape = self._prompt_embeds.shape
            size = shape[0]
            if size == 1:
                self._prompt_embeds = None
        if self._prompt_embeds is None:
            self.load_prompt_embeds()
        return self._prompt_embeds

    @prompt_embeds.setter
    def prompt_embeds(self, value):
        self._prompt_embeds = value

    @property
    def negative_prompt_embeds(self):
        # reset negative_prompt_embeds if deterministic_generation is True and it has a size of 1
        if self._negative_prompt_embeds is not None and self.deterministic_generation:
            shape = self._negative_prompt_embeds.shape
            size = shape[0]
            if size == 1:
                self._negative_prompt_embeds = None
        if self._negative_prompt_embeds is None:
            self.load_prompt_embeds()
        return self._negative_prompt_embeds

    @negative_prompt_embeds.setter
    def negative_prompt_embeds(self, value):
        self._negative_prompt_embeds = value

    def clear_prompt_embeds(self):
        self._prompt_embeds = None
        self._negative_prompt_embeds = None

    def load_prompt_embeds(self):
        logger.info("Loading prompt embeds")
        self.compel_proc = None
        self.clear_memory()
        prompt = self.prompt
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