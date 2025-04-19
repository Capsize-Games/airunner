from airunner.gui.widgets.nodegraph.nodes.base_workflow_node import BaseWorkflowNode
from airunner.handlers.stablediffusion.image_request import ImageRequest
from airunner.enums import ImagePreset
from airunner.settings import AIRUNNER_DEFAULT_SCHEDULER


class ImageGenerationNode(BaseWorkflowNode):
    NODE_NAME = "Image Generation"

    def __init__(self):
        super().__init__()

        # Basic inputs
        self.add_input("prompt_data")

        # Model configuration
        self.add_input("pipeline_action", display_name=True)
        self.add_input("generator_name", display_name=True)
        self.add_input("model_path", display_name=True)
        self.add_input("version", display_name=True)

        # Generation parameters
        self.add_input("random_seed", display_name=True)
        self.add_input("seed", display_name=True)
        self.add_input("steps", display_name=True)
        self.add_input("ddim_eta", display_name=True)
        self.add_input("scale", display_name=True)
        self.add_input("strength", display_name=True)
        self.add_input("n_samples", display_name=True)
        self.add_input("clip_skip", display_name=True)
        self.add_input("lora_scale", display_name=True)
        self.add_input("width", display_name=True)
        self.add_input("height", display_name=True)
        self.add_input("use_compel", display_name=True)

        # Advanced parameters
        self.add_input("crops_coord_top_left", display_name=True)
        self.add_input("original_size", display_name=True)
        self.add_input("target_size", display_name=True)
        self.add_input("negative_original_size", display_name=True)
        self.add_input("negative_target_size", display_name=True)
        self.add_input("additional_prompts", display_name=True)

        # Output
        self.add_output("image")

        # UI elements
        self.add_combo_menu(
            name="model_name",
            label="Model Name",
            items=["stable-diffusion-v1-5", "sdxl", "controlnet"],
            tooltip="Select the model to use for image generation.",
            tab="settings",
        )

        self.add_combo_menu(
            name="scheduler",
            label="Scheduler",
            items=[
                "ddim",
                "pndm",
                "lms",
                "euler",
                "euler_ancestral",
                "dpm",
                "dpm_sde",
            ],
            tooltip="Select the scheduler to use for image generation.",
            tab="settings",
        )

        self.add_combo_menu(
            name="image_preset",
            label="Image Preset",
            items=[preset.name for preset in ImagePreset],
            tooltip="Select an image preset.",
            tab="settings",
        )

        # Add spin boxes for numerical inputs
        self.add_text_input(
            name="image_width",
            label="Width",
            text="512",
            placeholder_text="Width of the generated image",
        )

        self.add_text_input(
            name="image_height",
            label="Height",
            text="512",
            placeholder_text="Height of the generated image",
        )

        self.add_text_input(
            name="steps",
            label="Steps",
            text="20",
            placeholder_text="Number of steps for image generation",
        )

        self.add_text_input(
            name="seed",
            label="Seed",
            text="42",
            placeholder_text="Random seed for generation",
        )

        self.add_checkbox(
            name="random_seed",
            label="Random Seed",
            text="Use Random Seed",
            state=True,
            tab="parameters",
        )

        self.add_checkbox(
            name="use_compel",
            label="Use Compel",
            text="Use Compel",
            state=True,
            tab="parameters",
        )

    def execute(self, input_data):
        # Convert inputs to proper types
        prompt_data = input_data.get("prompt_data", {})
        request = ImageRequest(
            pipeline_action=input_data.get("pipeline_action", ""),
            generator_name=input_data.get("generator_name", "stablediffusion"),
            prompt=prompt_data.get("prompt", ""),
            negative_prompt=prompt_data.get("negative_prompt", ""),
            second_prompt=prompt_data.get("prompt_2", ""),
            second_negative_prompt=prompt_data.get("negative_prompt_2", ""),
            random_seed=input_data.get("random_seed", True),
            model_path=input_data.get("model_path", ""),
            scheduler=input_data.get("scheduler", AIRUNNER_DEFAULT_SCHEDULER),
            version=input_data.get("version", "SD 1.5"),
            use_compel=input_data.get("use_compel", True),
            steps=int(input_data.get("steps", 20)),
            ddim_eta=float(input_data.get("ddim_eta", 0.5)),
            scale=float(input_data.get("scale", 7.5)),
            seed=int(input_data.get("seed", 42)),
            strength=float(input_data.get("strength", 0.5)),
            n_samples=int(input_data.get("n_samples", 1)),
            clip_skip=int(input_data.get("clip_skip", 0)),
            crops_coord_top_left=input_data.get("crops_coord_top_left"),
            original_size=input_data.get("original_size"),
            target_size=input_data.get("target_size"),
            negative_original_size=input_data.get("negative_original_size"),
            negative_target_size=input_data.get("negative_target_size"),
            lora_scale=float(input_data.get("lora_scale", 1.0)),
            width=int(input_data.get("width", 512)),
            height=int(input_data.get("height", 512)),
            image_preset=(
                ImagePreset[input_data.get("image_preset", "NONE")]
                if isinstance(input_data.get("image_preset"), str)
                else ImagePreset.NONE
            ),
            additional_prompts=input_data.get("additional_prompts"),
        )

        # TODO: Implement the actual image generation using the request
        # This would involve calling the appropriate backend service

        # Placeholder for now
        img = None

        return {"image": img}
