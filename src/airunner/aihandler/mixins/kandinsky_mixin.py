import torch
from aihandler.logger import logger


class KandinskyMixin:
    pipe_prior = None
    kandinsky_loaded = False

    @property
    def use_kandinsky(self):
        return self.options.get(f"generator_section") == "kandinsky"

    @property
    def do_clear_kandinsky(self):
        return self.kandinsky_loaded != self.use_kandinsky

    def kandinsky_call_pipe(self, **kwargs):
        self.kandinsky_loaded = True
        self.load_kandinsky_pipe_prior()
        image_embeds, negative_image_embeds = self.get_kandinsky_image_emebds()
        self.load_kandinsky_model()
        generator = self.generator()
        args = {
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "image_embeds": image_embeds,
            "negative_image_embeds": negative_image_embeds,
            "height": self.height,
            "width": self.width,
            "generator": generator,
            "num_inference_steps": self.steps,
        }
        if self.is_img2img or self.is_outpaint:
            args["image"] = kwargs.get("image")
            args["guidance_scale"] = self.guidance_scale
        if self.is_img2img:
            args["strength"] = self.strength
        if self.is_outpaint:
            mask_image = kwargs.get("mask_image")
            # invert mask image
            mask_image = mask_image.point(lambda x: 255 - x)
            args["mask_image"] = mask_image

        return self.pipe(**args)

    def clear_kandinsky(self):
        self.pipe_prior = None
        self.unload_unused_models()
        self.reload_model = True
        self.kandinsky_loaded = False
        self.clear_scheduler()
        self.current_model = None

    def get_kandinsky_image_emebds(self):
        generator = self.generator()
        if self.use_interpolation:
            interpolation_prompt = []
            weights = []
            for index, item in enumerate(self.interpolation_data):
                interpolation_prompt.append(item[item["type"]])
                weights.append(item["weight"])
            return self.pipe_prior.interpolate(interpolation_prompt, weights).to_tuple()
        return self.pipe_prior(
            prompt=self.prompt,
            negative_prompt=self.negative_prompt,
            guidance_scale=1.0,
            generator=generator
        ).to_tuple()

    def load_kandinsky_pipe_prior(self):
        from diffusers import KandinskyPriorPipeline
        if self.pipe:
            self.pipe.to("cpu")
        if not self.pipe_prior:
            self.pipe_prior = KandinskyPriorPipeline.from_pretrained(
                "kandinsky-community/kandinsky-2-1-prior",
                torch_dtype=self.data_type
            )
        self.pipe_prior.to("cuda")

    def load_kandinsky_model(self):
        from diffusers import KandinskyPipeline, KandinskyImg2ImgPipeline, KandinskyInpaintPipeline
        model = "kandinsky-2-1"
        if self.is_txt2img:
            class_name = KandinskyPipeline
        elif self.is_img2img:
            class_name = KandinskyImg2ImgPipeline
        elif self.is_outpaint:
            class_name = KandinskyInpaintPipeline
            model = "kandinsky-2-1-inpaint"
        self.pipe_prior.to("cpu")
        if not self.pipe:
            self.pipe = class_name.from_pretrained(
                f"kandinsky-community/{model}",
                torch_dtype=self.data_type
            )
        # self._change_scheduler()
        logger.info(f"Load safety checker")
        #self.load_safety_checker(self.action)
        self.apply_memory_efficient_settings()
