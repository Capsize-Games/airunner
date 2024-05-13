from airunner.aihandler.stablediffusion.sd_request import SDRequest


class UpscaleRequest(SDRequest):
    def prepare_args(self, **kwargs) -> dict:
        args = super().prepare_args(**kwargs)
        args.update({
            "image": kwargs.get("image"),
            "generator": self.generator,
        })
        return args

    def load_prompt_embed_args(
        self,
        prompt_embeds,
        negative_prompt_embeds,
        args
    ):
        """
        Load prompt embeds
        """
        args["prompt"] = self.generator_settings.prompt
        args["negative_prompt"] = self.generator_settings.negative_prompt
        return args
