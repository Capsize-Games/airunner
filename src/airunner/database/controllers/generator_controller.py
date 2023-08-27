from airunner.database.controllers.base_controller import BaseController
from airunner.database.models.generator_settings import GeneratorSettings


class GeneratorController(BaseController):
    model_class = GeneratorSettings

    @property
    def id(self):
        return self.settings.id

    @property
    def generator_type(self):
        return self.settings.generator_type

    @property
    def prompt(self):
        return self.settings.prompt

    @property
    def negative_prompt(self):
        return self.settings.negative_prompt

    @property
    def steps(self):
        return self.settings.steps

    @property
    def ddim_eta(self):
        return self.settings.ddim_eta

    @property
    def height(self):
        return self.settings.height

    @property
    def width(self):
        return self.settings.width

    @property
    def scale(self):
        return self.settings.scale

    @property
    def seed(self):
        return self.settings.seed

    @property
    def random_seed(self):
        return self.settings.random_seed

    @property
    def model_var(self):
        return self.settings.model_var

    @property
    def scheduler_var(self):
        return self.settings.scheduler_var

    @property
    def prompt_triggers(self):
        return self.settings.prompt_triggers

    @property
    def strength(self):
        return self.settings.strength

    @property
    def image_guidance_scale(self):
        return self.settings.image_guidance_scale

    @property
    def n_samples(self):
        return self.settings.n_samples

    @property
    def do_upscale_full_image(self):
        return self.settings.do_upscale_full_image

    @property
    def do_upscale_by_active_grid(self):
        return self.settings.do_upscale_by_active_grid

    @property
    def downscale_amount(self):
        return self.settings.downscale_amount

    @property
    def deterministic(self):
        return self.settings.deterministic

    @property
    def controlnet_var(self):
        return self.settings.controlnet_var

    @property
    def enable_controlnet(self):
        return self.settings.enable_controlnet

    @property
    def controlnet_guidance_scale(self):
        return self.settings.controlnet_guidance_scale

    @property
    def clip_skip(self):
        return self.settings.clip_skip
