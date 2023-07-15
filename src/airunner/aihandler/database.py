import os
from aihandler.qtvar import Var, BooleanVar, IntVar, StringVar, DoubleVar, FloatVar, ListVar, DictVar
from aihandler.settings import \
    DEFAULT_MODEL, \
    DEFAULT_SCHEDULER, \
    DEFAULT_CANVAS_COLOR, \
    DEFAULT_GRID_COLOR, \
    DEFAULT_WORKING_SIZE, \
    DEFAULT_BRUSH_PRIMARY_COLOR, \
    DEFAULT_BRUSH_SECONDARY_COLOR
DEFAULT_BRUSH_OPACITY = 255
DEFAULT_GRID_SETTINGS = {
    "line_color": DEFAULT_GRID_COLOR,
    "line_width": 1,
    "line_stipple": True,
    "size": 64,
    "show_grid": True,
    "snap_to_grid": True,
}
DEFAULT_MEMORY_SETTINGS = {
    "use_accelerated_transformers": True,
    "use_attention_slicing": False,
    "use_last_channels": False,
    "use_enable_sequential_cpu_offload": False,
    "enable_model_cpu_offload": False,
    "use_tf32": True,
    "use_enable_vae_slicing": False,
    "use_tiled_vae": False,
    "use_cudnn_benchmark": True,
    "use_torch_compile": False
}
DEFAULT_GENERATOR_SETTINGS = {
    "prompt": "",
    "negative_prompt": "",
    "steps": 20,
    "ddim_eta": 0.5,
    "height": 512,
    "width": 512,
    "scale": 750,
    "seed": 42,
    "random_seed": True,
    "model_var": DEFAULT_MODEL,
    "scheduler_var": DEFAULT_SCHEDULER,
    "prompt_triggers": "",
    "strength": 50,
    "image_guidance_scale": 150,
    "n_samples": 1,
    "do_upscale_full_image": True,
    "do_upscale_by_active_grid": False,
    "downscale_amount": 1,
    "deterministic": False,
    "controlnet_var": "",
    "enable_controlnet": False,
    "controlnet_guidance_scale": 50,
    "zeroshot": False,
}
GENERATOR_TYPES = {
    "prompt": StringVar,
    "negative_prompt": StringVar,
    "steps": IntVar,
    "ddim_eta": DoubleVar,
    "height": IntVar,
    "width": IntVar,
    "scale": DoubleVar,
    "seed": IntVar,
    "random_seed": BooleanVar,
    "model_var": StringVar,
    "scheduler_var": StringVar,
    "prompt_triggers": StringVar,
    "strength": DoubleVar,
    "image_guidance_scale": DoubleVar,
    "n_samples": IntVar,
    "do_upscale_full_image": BooleanVar,
    "do_upscale_by_active_grid": BooleanVar,
    "downscale_amount": IntVar,
    "deterministic": BooleanVar,
    "controlnet_var": StringVar,
    "enable_controlnet": BooleanVar,
    "controlnet_guidance_scale": IntVar,
    "zeroshot": BooleanVar,
}
USER = os.environ.get("USER", "")
default_model_path = os.path.join("/", "home", USER, "stablediffusion")
GENERATORS = [
    "txt2img",
    "img2img",
    "riffusion",
    "pix2pix",
    "inpaint",
    "outpaint",
    "depth2img",
    "upscale",
    "superresolution",
    "controlnet",
    "txt2vid",
    "kandinsky_txt2img",
    "kandinsky_img2img",
    "kandinsky_inpaint",
    "kandinsky_outpaint",
    "shapegif_txt2img",
    "shapegif_img2img",
]

class PropertyBase:
    """
    A base class used for collections of properties that are stored in the database.
    This is an interface into the database with a tkinter var representation of
    the columns within the database. The TkVarMapperBase class is used to map
    the tkinter variable to the database column and update the database when
    the tkinter variable is changed.
    """
    settings = None
    def __init__(self, app):
        self.app = app
        self.mapped = {}

    def initialize(self):
        """
        Implement this class and initialize all tkinter variables within in.
        :return:
        """
        pass

    def read(self):
        """
        Implement this class - return the items from the database.
        :return:
        """
        pass


class BaseSettings(PropertyBase):
    namespace = ""
    generator = "stablediffusion"

    def __getattr__(self, name):
        """
        when a property is called such as `steps` and it is not found, an
        AttributeError is raised. This function will catch that and try to find
        the property on this classed based on namespace. If it is not found, it
        will raise the AttributeError again.
        """
        try:
            super().__getattribute__(name)
        except AttributeError as e:
            # check if the property is on this class
            # check if name_spaced already in name
            namespace = self.namespace
            if self.generator == "kandinsky":
                namespace = f"kandinsky_{namespace}"
            if self.generator == "shapegif":
                namespace = f"shapegif_{namespace}"
            if name.startswith(namespace):
                raise e
            else:
                name_spaced = f"{namespace}_{name}"
                if hasattr(self, name_spaced):
                    return getattr(self, name_spaced)
            raise e

    def set_namespace(self, namespace, generator="stablediffusion"):
        self.namespace = namespace
        self.set_generator(generator)

    def set_generator(self, generator):
        self.generator = generator

    def reset_settings_to_default(self):
        pass

    def initialize(self, settings=None):
        pass


class RunAISettings(BaseSettings):
    """
    An interface class which stores all of the application settings.
    This class should be used to interact with the settings database from
    within the application.
    """

    def initialize(self, settings=None):
        app = self.app

        # general settings
        self.nsfw_filter = BooleanVar(app)
        self.nsfw_filter._default = True
        self.allow_hf_downloads = BooleanVar(app)
        self.pixel_mode = BooleanVar(app)
        self.canvas_color = StringVar(app, DEFAULT_CANVAS_COLOR)
        self.paste_at_working_size = BooleanVar(app)
        self.outpaint_on_paste = BooleanVar(app)
        self.fast_load_last_session = BooleanVar(app)
        self.available_embeddings = StringVar(app, "")
        self.do_settings_reset = BooleanVar(app)
        self.dark_mode_enabled = BooleanVar(app)
        self.resize_on_paste = BooleanVar(app)
        self.image_to_new_layer = BooleanVar(app)

        # toolkit
        self.primary_color = StringVar(app, DEFAULT_BRUSH_PRIMARY_COLOR)
        self.secondary_color = StringVar(app, DEFAULT_BRUSH_SECONDARY_COLOR)
        self.blur_radius = FloatVar(app, 0.0)
        self.cyan_red = IntVar(app, 0.0)
        self.magenta_green = IntVar(app, 0.0)
        self.yellow_blue = IntVar(app, 0.0)
        self.current_tool = StringVar(app, "")

        # stable diffusion memory options
        self.use_last_channels = BooleanVar(app, DEFAULT_MEMORY_SETTINGS["use_last_channels"])
        self.use_enable_sequential_cpu_offload = BooleanVar(app, DEFAULT_MEMORY_SETTINGS["use_enable_sequential_cpu_offload"])
        self.use_attention_slicing = BooleanVar(app, DEFAULT_MEMORY_SETTINGS["use_attention_slicing"])
        self.use_tf32 = BooleanVar(app, DEFAULT_MEMORY_SETTINGS["use_tf32"])
        self.use_cudnn_benchmark = BooleanVar(app, DEFAULT_MEMORY_SETTINGS["use_cudnn_benchmark"])
        self.use_enable_vae_slicing = BooleanVar(app, DEFAULT_MEMORY_SETTINGS["use_enable_vae_slicing"])
        self.use_tiled_vae = BooleanVar(app, DEFAULT_MEMORY_SETTINGS["use_tiled_vae"])
        self.enable_model_cpu_offload = BooleanVar(app, DEFAULT_MEMORY_SETTINGS["enable_model_cpu_offload"])
        self.use_accelerated_transformers = BooleanVar(app, DEFAULT_MEMORY_SETTINGS["use_accelerated_transformers"])
        self.use_torch_compile = BooleanVar(app, DEFAULT_MEMORY_SETTINGS["use_torch_compile"])

        # size settings
        self.working_width = IntVar(app, DEFAULT_WORKING_SIZE[0])
        self.working_height = IntVar(app, DEFAULT_WORKING_SIZE[1])

        # huggingface settings
        self.hf_api_key = StringVar(app, "")

        # model settings
        self.model_base_path = StringVar(app, default_model_path)
        self.depth2img_model_path = StringVar(app)
        self.pix2pix_model_path = StringVar(app)
        self.outpaint_model_path = StringVar(app)
        self.upscale_model_path = StringVar(app)
        self.txt2vid_model_path = StringVar(app)

        self.mask_brush_size = IntVar(app, 10)

        self.line_color = StringVar(app, DEFAULT_GRID_SETTINGS["line_color"])
        self.line_width = IntVar(app, DEFAULT_GRID_SETTINGS["line_width"])
        self.line_stipple = BooleanVar(app, DEFAULT_GRID_SETTINGS["line_stipple"])
        self.size = IntVar(app, DEFAULT_GRID_SETTINGS["size"])
        self.show_grid = BooleanVar(app, DEFAULT_GRID_SETTINGS["show_grid"])
        self.snap_to_grid = BooleanVar(app, DEFAULT_GRID_SETTINGS["snap_to_grid"])

        for key, value in DEFAULT_GENERATOR_SETTINGS.items():
            for generator in GENERATORS:
                self.__dict__[f"{generator}_{key}"] = GENERATOR_TYPES[key](app, value)

        """
        TODO: extensions
        self.available_extensions = ListVar(app, [])
        self.enabled_extensions = ListVar(app, [])
        self.active_extensions = ListVar(app, [])
        self.extensions_path = StringVar(app, "")
        """

        self.primary_brush_opacity = IntVar(app, DEFAULT_BRUSH_OPACITY)
        self.secondary_brush_opacity = IntVar(app, DEFAULT_BRUSH_OPACITY)

        self.embeddings_path = StringVar(app, "")

        self.lora_path = StringVar(app, "")
        self.available_loras = ListVar(app, [])

        self.force_reset = BooleanVar(app, True)

        # Image export preferences
        self.auto_export_images = BooleanVar(app)
        self.image_path = StringVar(app, "")
        self.gif_path = StringVar(app, "")
        self.image_export_type = StringVar(app, "png")

        # Video export preferences
        self.video_path = StringVar(app, "")

        ## Image export preferences metadata
        self.image_export_metadata_prompt = BooleanVar(app)
        self.image_export_metadata_negative_prompt = BooleanVar(app)
        self.image_export_metadata_scale = BooleanVar(app)
        self.image_export_metadata_seed = BooleanVar(app)
        self.image_export_metadata_steps = BooleanVar(app)
        self.image_export_metadata_ddim_eta = BooleanVar(app)
        self.image_export_metadata_iterations = BooleanVar(app)
        self.image_export_metadata_samples = BooleanVar(app)
        self.image_export_metadata_model = BooleanVar(app)
        self.image_export_metadata_model_branch = BooleanVar(app)
        self.image_export_metadata_scheduler = BooleanVar(app)
        self.export_metadata = BooleanVar(app)
        self.import_metadata = BooleanVar(app)
        self.latest_version_check = BooleanVar(app, True)

        self.show_active_image_area = BooleanVar(app, False)

        self.use_interpolation = BooleanVar(app, False)
        self.is_maximized = BooleanVar(app, False)

        self.main_splitter_sizes = IntVar(app, [-1, -1, -1])
        self.bottom_splitter_sizes = IntVar(app, [0, 0])

        self.use_prompt_builder_checkbox = BooleanVar(app, False)

        self.auto_prompt_weight = FloatVar(app, 0.5)
        self.auto_negative_prompt_weight = FloatVar(app, 0.5)
        self.negative_auto_prompt_weight = FloatVar(app, 0.5)
        self.prompt_generator_category = StringVar(app, "")
        self.prompt_generator_prompt = StringVar(app, "")
        self.prompt_generator_weighted_values = DictVar(app, {})
        self.prompt_generator_prompt_color = StringVar(app, "")
        self.prompt_generator_prompt_genre = StringVar(app, "")
        self.prompt_generator_prompt_style = StringVar(app, "")
        self.prompt_generator_advanced = BooleanVar(app, False)
        self.prompt_generator_prefix = StringVar(app, "")
        self.prompt_generator_suffix = StringVar(app, "")
        self.negative_prompt_generator_prefix = StringVar(app, "")
        self.negative_prompt_generator_suffix = StringVar(app, "")


    def reset_settings_to_default(self):
        # pasting / generating
        self.paste_at_working_size.set(False)
        self.outpaint_on_paste.set(False)
        self.resize_on_paste.set(False)
        self.image_to_new_layer.set(False)

        # misc
        self.nsfw_filter.set(True)
        self.allow_hf_downloads.set(True)
        self.fast_load_last_session.set(False)
        self.do_settings_reset.set(False)

        # colors and theme
        self.dark_mode_enabled.set(False)
        self.canvas_color.set(DEFAULT_CANVAS_COLOR)
        self.primary_color.set(DEFAULT_BRUSH_PRIMARY_COLOR)
        self.secondary_color.set(DEFAULT_BRUSH_SECONDARY_COLOR)
        self.primary_brush_opacity.set(DEFAULT_BRUSH_OPACITY)
        self.secondary_brush_opacity.set(DEFAULT_BRUSH_OPACITY)

        # grid settings
        self.line_color.set(DEFAULT_GRID_SETTINGS["line_color"])
        self.line_width.set(DEFAULT_GRID_SETTINGS["line_width"])
        self.line_stipple.set(DEFAULT_GRID_SETTINGS["line_stipple"])
        self.size.set(DEFAULT_GRID_SETTINGS["size"])
        self.show_grid.set(DEFAULT_GRID_SETTINGS["show_grid"])
        self.snap_to_grid.set(DEFAULT_GRID_SETTINGS["snap_to_grid"])

        # memory
        for key, value in DEFAULT_MEMORY_SETTINGS.items():
            getattr(self, key).set(value)

        # size
        self.working_width.set(DEFAULT_WORKING_SIZE[0])
        self.working_height.set(DEFAULT_WORKING_SIZE[1])

        # generator
        # iterate over DEFAULT_GEENRATOR_SETTINGS
        for key, value in DEFAULT_GENERATOR_SETTINGS.items():
            for generator in GENERATORS:
                if hasattr(self, f"{generator}_{key}"):
                    setattr(self, f"{generator}_{key}", GENERATOR_TYPES[key](self.app, value))

        # Image export preferences
        self.auto_export_images.set(False)
        self.image_export_metadata_prompt.set(False)
        self.image_export_metadata_negative_prompt.set(False)
        self.image_export_metadata_scale.set(False)
        self.image_export_metadata_seed.set(False)
        self.image_export_metadata_steps.set(False)
        self.image_export_metadata_ddim_eta.set(False)
        self.image_export_metadata_iterations.set(False)
        self.image_export_metadata_samples.set(False)
        self.image_export_metadata_model.set(False)
        self.image_export_metadata_model_branch.set(False)
        self.image_export_metadata_scheduler.set(False)
        self.export_metadata.set(False)
        self.import_metadata.set(False)
        self.show_active_image_area.set(False)

        self.app.use_interpolation = False
        self.is_maximized.set(False)

        self.auto_prompt_weight.set(0.5)
        self.auto_negative_prompt_weight.set(0.5)
        self.negative_auto_prompt_weight.set(0.5)
        self.prompt_generator_category.set("")
        self.prompt_generator_prompt.set("")
        self.prompt_generator_weighted_values.set({})
        self.prompt_generator_prompt_genre.set("")
        self.prompt_generator_prompt_color.set()
        self.prompt_generator_prompt_style.set("")
        self.prompt_generator_advanced.set(False)
        self.prompt_generator_prefix.set("")
        self.prompt_generator_suffix.set("")
        self.negative_prompt_generator_prefix.set("")
        self.negative_prompt_generator_suffix.set("")


class PromptSettings(BaseSettings):
    namespace = "prompts"

    def initialize(self, settings=None):
        self.prompts = ListVar(self.app, [])
