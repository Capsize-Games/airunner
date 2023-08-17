import transformers.image_transforms
from torchvision import transforms

from airunner.aihandler.logger import Logger as logger
from diffusers import KandinskyPriorPipeline


class KandinskyMixin:
    pipe_prior = None
    kandinsky_loaded = False
    image_embeds = None
    negative_image_embeds = None

    @property
    def do_variation(self):
        return self.options.get("variation", False)

    @property
    def use_kandinsky(self):
        return self.options.get(f"generator_section") == "kandinsky"

    @property
    def do_clear_kandinsky(self):
        return self.kandinsky_loaded != self.use_kandinsky

    def generate_image_embeds(self):
        self.send_message(f"Loading pipe prior...")
        self.load_kandinsky_pipe_prior()
        self.send_message(f"Generating image embeds...")
        self.image_embeds, self.negative_image_embeds = self.get_kandinsky_image_emebds()
        self.send_message(f"Loading model...")

    def kandinsky_call_pipe(self, **kwargs):
        if not self.do_variation \
                or self.image_embeds is None \
                or self.negative_image_embeds is None:
            self.generate_image_embeds()

        self.load_kandinsky_model()

        self.send_message(f"Generating image...")
        generator = self.generator()
        args = {
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "image_embeds": self.image_embeds,
            "negative_image_embeds": self.negative_image_embeds,
            "height": self.height,
            "width": self.width,
            "generator": generator,
            "num_inference_steps": self.steps,
            "callback": self.callback
        }
        if self.is_img2img or self.is_outpaint:
            args["image"] = kwargs.get("image")
            args["guidance_scale"] = self.guidance_scale
        if self.is_img2img:
            args["strength"] = self.strength
        if self.is_outpaint:
            mask_image = kwargs.get("mask_image")
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
            guidance_scale=self.guidance_scale,
            generator=generator
        ).to_tuple()

    def load_kandinsky_pipe_prior(self):
        if self.pipe:
            self.pipe.to("cpu")
        if not self.pipe_prior:
            self.pipe_prior = self.from_pretrained(
                class_object=KandinskyPriorPipeline,
                model="kandinsky-community/kandinsky-2-1-prior",
            )
        self.pipe_prior.to("cuda")

    def load_kandinsky_model(self):
        model = "kandinsky-2-1"
        if self.is_outpaint:
            model = "kandinsky-2-1-inpaint"
        #self.pipe_prior.to("cpu")
        self.pipe_prior = None
        if not self.pipe:
            self.pipe = self.from_pretrained(model=f"kandinsky-community/{model}")
        # self._change_scheduler()
        logger.info(f"Load safety checker")
        #self.load_safety_checker(self.action)
        self.apply_memory_efficient_settings()
