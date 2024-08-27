from compel import Compel, DiffusersTextualInversionManager, ReturnedEmbeddingsType
from airunner.utils.get_torch_device import get_torch_device


class CompelMixin:
    def __init__(self):
        self.prompt_embeds = None
        self.negative_prompt_embeds = None
        self.pooled_prompt_embeds = None
        self.pooled_negative_prompt_embeds = None
        self.compel_proc = None
        self._current_prompt = ""
        self._current_negative_prompt = ""

    def clear_prompt_embeds(self):
        self.logger.debug("Clearing prompt embeds")
        self.prompt_embeds = None
        self.negative_prompt_embeds = None
        self.pooled_prompt_embeds = None
        self.pooled_negative_prompt_embeds = None

    def load_prompt_embeds(
        self,
        pipe,
        do_reload=True,
        prompt="",
        negative_prompt="",
        prompt_2="",
        negative_prompt_2="",
    ):
        if (
            self.prompt_embeds is not None and
            self.negative_prompt_embeds is not None
        ):
            self.logger.debug("Prompt embeds already loaded, skipping load_prompt_embeds")
            return

        try:
            if self.compel_proc is None:
                self.logger.debug("Loading Compel proc")
                textual_inversion_manager = DiffusersTextualInversionManager(pipe)

                parameters = dict(
                    truncate_long_prompts=False,
                    textual_inversion_manager=textual_inversion_manager
                )

                if self.is_sd_xl:
                    tokenizer = [pipe.tokenizer, pipe.tokenizer_2]
                    text_encoder = [pipe.text_encoder, pipe.text_encoder_2]
                    parameters["returned_embeddings_type"] = ReturnedEmbeddingsType.PENULTIMATE_HIDDEN_STATES_NON_NORMALIZED
                    parameters["requires_pooled"] = [False, True]
                else:
                    tokenizer = pipe.tokenizer
                    text_encoder = pipe.text_encoder

                parameters.update(dict(
                    tokenizer=tokenizer,
                    text_encoder=text_encoder
                ))

                self.compel_proc = Compel(
                    **parameters
                )
        except Exception as e:
            self.logger.error(f"Error creating compel proc: {e}")
            return None

        prompt_embeds = None
        negative_prompt_embeds = None
        pooled_prompt_embeds = None
        pooled_negative_prompt_embeds = None

        # check if prompt is string
        if isinstance(prompt, str):
            self.logger.debug("Loading prompt embeds from str")
            try:
                if self.is_sd_xl:
                    prompt_embeds, pooled_prompt_embeds = self.compel_proc.build_conditioning_tensor(prompt)
                else:
                    prompt_embeds = self.compel_proc.build_conditioning_tensor(prompt)
            except RuntimeError as e:
                self.logger.error("Error building prompt embeds from str")
                self.logger.error(e)

            try:
                if self.is_sd_xl:
                    negative_prompt_embeds, pooled_negative_prompt_embeds = self.compel_proc.build_conditioning_tensor(negative_prompt)
                else:
                    negative_prompt_embeds = self.compel_proc.build_conditioning_tensor(negative_prompt)
            except RuntimeError as e:
                self.logger.error("Error building negative prompt embeds from str")
                self.logger.error(e)
        else:
            self.logger.debug("Loading prompt embeds")
            try:
                if self.is_sd_xl:
                    prompt_embeds, pooled_prompt_embeds = self.compel_proc(prompt)
                else:
                    prompt_embeds = self.compel_proc(prompt)
            except RuntimeError as e:
                self.logger.error("Error building prompt embeds")
                self.logger.error(e)
            try:
                if self.is_sd_xl:
                    negative_prompt_embeds, pooled_negative_prompt_embeds = self.compel_proc(negative_prompt)
                else:
                    negative_prompt_embeds = self.compel_proc(negative_prompt)
            except RuntimeError as e:
                self.logger.error("Error building negative prompt embeds")
                self.logger.error(e)

        if prompt_embeds is None or negative_prompt_embeds is None:
            if do_reload:
                return self.load_prompt_embeds(
                    pipe,
                    do_reload=False,
                    prompt=prompt,
                    negative_prompt=negative_prompt
                )
            else:
                self.logger.error("Prompt embeds are None")
                return

        [
            prompt_embeds,
            negative_prompt_embeds
        ] = self.compel_proc.pad_conditioning_tensors_to_same_length([
            prompt_embeds,
            negative_prompt_embeds
        ])

        self.prompt_embeds = prompt_embeds
        self.negative_prompt_embeds = negative_prompt_embeds
        self.pooled_prompt_embeds = pooled_prompt_embeds
        self.pooled_negative_prompt_embeds = pooled_negative_prompt_embeds

        device = get_torch_device(self.settings["memory_settings"]["default_gpu"]["sd"])

        if prompt_embeds is not None:
            self.logger.debug(f"Moving prompt embeds to device: {device}")
            self.prompt_embeds.half().to(device)

        if negative_prompt_embeds is not None:
            self.negative_prompt_embeds.half().to(device)

        if pooled_prompt_embeds is not None:
            self.pooled_prompt_embeds.half().to(device)

        if pooled_negative_prompt_embeds is not None:
            self.pooled_negative_prompt_embeds.half().to(device)
