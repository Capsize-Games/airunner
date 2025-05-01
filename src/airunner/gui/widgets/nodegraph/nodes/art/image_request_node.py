from typing import Dict
from PySide6.QtWidgets import QFileDialog

from NodeGraphQt.constants import NodePropWidgetEnum

from airunner.gui.widgets.nodegraph.nodes.art.base_art_node import (
    BaseArtNode,
)
from airunner.handlers.stablediffusion.image_request import ImageRequest
from airunner.enums import (
    ImagePreset,
    QualityEffects,
    Scheduler,
    StableDiffusionVersion,
)


class ImageRequestNode(BaseArtNode):
    """
    A node that outputs an ImageRequest object with configurable parameters.

    This node provides input ports for all ImageRequest parameters and outputs
    a properly constructed ImageRequest object for stable diffusion image generation.
    """

    NODE_NAME = "Image Request"
    has_exec_in_port = False
    has_exec_out_port = False
    _input_ports = [
        dict(name="pipeline_action", display_name="Pipeline Action"),
        dict(name="generator_name", display_name="Generator Name"),
        dict(name="prompt", display_name="Prompt"),
        dict(name="negative_prompt", display_name="Negative Prompt"),
        dict(name="second_prompt", display_name="Second Prompt"),
        dict(
            name="second_negative_prompt",
            display_name="Second Negative Prompt",
        ),
        dict(name="random_seed", display_name="Random Seed"),
        dict(name="model_path", display_name="Model Path"),
        dict(name="custom_path", display_name="Custom Path"),
        dict(name="scheduler", display_name="Scheduler"),
        dict(name="version", display_name="Version"),
        dict(name="use_compel", display_name="Use Compel"),
        dict(name="steps", display_name="Steps"),
        dict(name="ddim_eta", display_name="DDIM Eta"),
        dict(name="scale", display_name="Scale"),
        dict(name="seed", display_name="Seed"),
        dict(name="strength", display_name="Strength"),
        dict(name="n_samples", display_name="Number of Samples"),
        dict(name="clip_skip", display_name="Clip Skip"),
        dict(name="lora_scale", display_name="Lora Scale"),
        dict(name="image_width", display_name="Image Width"),
        dict(name="image_height", display_name="Image Height"),
        dict(name="image_preset", display_name="Image Preset"),
    ]
    _output_ports = [
        dict(name="image_request", display_name="Image Request"),
    ]
    _properties = [
        {
            "name": "pipeline_action",
            "value": "txt2img",
            "widget_type": NodePropWidgetEnum.QLINE_EDIT,
            "tab": "basic",
        },
        {
            "name": "generator_name",
            "value": "stablediffusion",
            "widget_type": NodePropWidgetEnum.QLINE_EDIT,
            "tab": "basic",
        },
        {
            "name": "prompt",
            "value": "",
            "widget_type": NodePropWidgetEnum.QTEXT_EDIT,
            "tab": "prompt",
        },
        {
            "name": "negative_prompt",
            "value": "",
            "widget_type": NodePropWidgetEnum.QTEXT_EDIT,
            "tab": "prompt",
        },
        {
            "name": "second_prompt",
            "value": "",
            "widget_type": NodePropWidgetEnum.QTEXT_EDIT,
            "tab": "prompt",
        },
        {
            "name": "second_negative_prompt",
            "value": "",
            "widget_type": NodePropWidgetEnum.QTEXT_EDIT,
            "tab": "prompt",
        },
        {
            "name": "model_path",
            "value": "",
            "widget_type": NodePropWidgetEnum.QLINE_EDIT,
            "tab": "model",
        },
        {
            "name": "custom_path",
            "value": "",
            "widget_type": NodePropWidgetEnum.QLINE_EDIT,
            "tab": "model",
        },
        {
            "name": "scheduler",
            "value": Scheduler.DPM_PP_2M_SDE_K.value,
            "items": [scheduler.value for scheduler in Scheduler],
            "widget_type": NodePropWidgetEnum.QCOMBO_BOX,
            "tab": "model",
        },
        {
            "name": "version",
            "value": StableDiffusionVersion.SDXL1_0.value,
            "items": [version.value for version in StableDiffusionVersion],
            "widget_type": NodePropWidgetEnum.QCOMBO_BOX,
            "tab": "model",
        },
        {
            "name": "random_seed",
            "value": True,
            "widget_type": NodePropWidgetEnum.QCHECK_BOX,
            "tab": "generation",
        },
        {
            "name": "use_compel",
            "value": True,
            "widget_type": NodePropWidgetEnum.QCHECK_BOX,
            "tab": "prompt",
        },
        {
            "name": "steps",
            "value": 20,
            "widget_type": NodePropWidgetEnum.INT,
            "range": (1, 150),
            "tab": "generation",
        },
        {
            "name": "seed",
            "value": 42,
            "widget_type": NodePropWidgetEnum.INT,
            "range": (0, 2147483647),
            "tab": "generation",
        },
        {
            "name": "n_samples",
            "value": 1,
            "widget_type": NodePropWidgetEnum.INT,
            "range": (1, 8),
            "tab": "generation",
        },
        {
            "name": "clip_skip",
            "value": 0,
            "widget_type": NodePropWidgetEnum.INT,
            "range": (0, 12),
            "tab": "advanced",
        },
        {
            "name": "image_width",
            "value": 512,
            "widget_type": NodePropWidgetEnum.INT,
            "range": (64, 2048),
            "tab": "generation",
        },
        {
            "name": "image_height",
            "value": 512,
            "widget_type": NodePropWidgetEnum.INT,
            "range": (64, 2048),
            "tab": "generation",
        },
        {
            "name": "ddim_eta",
            "value": 0.5,
            "widget_type": NodePropWidgetEnum.FLOAT,
            "range": (0.0, 1.0),
            "tab": "advanced",
        },
        {
            "name": "scale",
            "value": 7.5,
            "widget_type": NodePropWidgetEnum.FLOAT,
            "range": (1.0, 30.0),
            "tab": "generation",
        },
        {
            "name": "strength",
            "value": 0.5,
            "widget_type": NodePropWidgetEnum.FLOAT,
            "range": (0.0, 1.0),
            "tab": "generation",
        },
        {
            "name": "lora_scale",
            "value": 1.0,
            "widget_type": NodePropWidgetEnum.FLOAT,
            "range": (0.0, 2.0),
            "tab": "advanced",
        },
        {
            "name": "crops_coords_top_left",
            "value": (0, 0),
            "widget_type": NodePropWidgetEnum.VECTOR2,
            "tab": "advanced",
        },
        {
            "name": "original_size",
            "value": (512, 512),
            "widget_type": NodePropWidgetEnum.VECTOR2,
            "tab": "advanced",
        },
        {
            "name": "target_size",
            "value": (1024, 1024),
            "widget_type": NodePropWidgetEnum.VECTOR2,
            "tab": "advanced",
        },
        {
            "name": "negative_crops_coords_top_left",
            "value": (0, 0),
            "widget_type": NodePropWidgetEnum.VECTOR2,
            "tab": "advanced",
        },
        {
            "name": "negative_original_size",
            "value": (512, 512),
            "widget_type": NodePropWidgetEnum.VECTOR2,
            "tab": "advanced",
        },
        {
            "name": "negative_target_size",
            "value": (1024, 1024),
            "widget_type": NodePropWidgetEnum.VECTOR2,
            "tab": "advanced",
        },
        {
            "name": "quality_effects",
            "value": QualityEffects.STANDARD,
            "items": [effect.value for effect in QualityEffects],
            "widget_type": NodePropWidgetEnum.QCOMBO_BOX,
            "tab": "advanced",
        },
        {
            "name": "image_preset",
            "value": ImagePreset.NONE.name,
            "items": [preset.name for preset in ImagePreset],
            "widget_type": NodePropWidgetEnum.QCOMBO_BOX,
            "tab": "advanced",
        },
    ]

    def on_widget_button_clicked(self, prop_name, value):
        """
        Handle button clicks for node properties.
        """
        if prop_name == "custom_path_button":
            self.on_browse_button_clicked()

    def on_browse_button_clicked(self):
        """
        Open a file dialog to select a custom model path.
        """
        current_path = self.get_property("custom_path") or ""
        file_path, _ = QFileDialog.getOpenFileName(
            None,  # Parent widget (can be None for nodes)
            "Select custom model",
            current_path,
            "Model Files (*.safetensors *.ckpt *.pt *.bin)",
        )
        if file_path:
            self.set_property("custom_path", file_path)

    def execute(self, input_data: Dict):
        """
        Execute the node to create and output an ImageRequest object.

        Args:
            input_data: Dictionary containing input values from connected nodes.

        Returns:
            dict: A dictionary with the key 'image_request' containing the ImageRequest object.
        """
        # Get values from inputs or use defaults from widget properties
        pipeline_action = self._get_value(input_data, "pipeline_action", str)
        generator_name = self._get_value(input_data, "generator_name", str)
        prompt = self._get_value(input_data, "prompt", str)
        negative_prompt = self._get_value(input_data, "negative_prompt", str)
        second_prompt = self._get_value(input_data, "second_prompt", str)
        second_negative_prompt = self._get_value(
            input_data, "second_negative_prompt", str
        )
        random_seed = self._get_value(input_data, "random_seed", bool)
        model_path = self._get_value(input_data, "model_path", str)
        custom_path = self._get_value(input_data, "custom_path", str)
        scheduler = self._get_value(input_data, "scheduler", str)
        version = self._get_value(input_data, "version", str)
        use_compel = self._get_value(input_data, "use_compel", bool)
        steps = self._get_value(input_data, "steps", int)
        ddim_eta = self._get_value(input_data, "ddim_eta", float)
        scale = self._get_value(input_data, "scale", float)
        seed = self._get_value(input_data, "seed", int)
        strength = self._get_value(input_data, "strength", float)
        n_samples = self._get_value(input_data, "n_samples", int)
        clip_skip = self._get_value(input_data, "clip_skip", int)
        lora_scale = self._get_value(input_data, "lora_scale", float)
        image_width = self._get_value(input_data, "image_width", int)
        image_height = self._get_value(input_data, "image_height", int)

        # Get image preset as string and convert to enum
        image_preset_str = self._get_value(input_data, "image_preset", str)
        try:
            image_preset = ImagePreset[image_preset_str]
        except (KeyError, TypeError):
            image_preset = ImagePreset.NONE

        # Create ImageRequest object
        image_request = ImageRequest(
            pipeline_action=pipeline_action,
            generator_name=generator_name,
            prompt=prompt,
            negative_prompt=negative_prompt,
            second_prompt=second_prompt,
            second_negative_prompt=second_negative_prompt,
            random_seed=random_seed,
            model_path=model_path,
            custom_path=custom_path,
            scheduler=scheduler,
            version=version,
            use_compel=use_compel,
            steps=steps,
            ddim_eta=ddim_eta,
            scale=scale,
            seed=seed,
            strength=strength,
            n_samples=n_samples,
            clip_skip=clip_skip,
            lora_scale=lora_scale,
            width=image_width,
            height=image_height,
            image_preset=image_preset,
            crops_coords_top_left=self.generator_settings.crops_coords_top_left,
            negative_crops_coords_top_left=self.generator_settings.negative_crops_coords_top_left,
            target_size=self.generator_settings.target_size,
            original_size=self.generator_settings.original_size,
            negative_target_size=self.generator_settings.negative_target_size,
            negative_original_size=self.generator_settings.negative_original_size,
            quality_effects=QualityEffects(
                self.generator_settings.quality_effects
            ),
        )
        return {"image_request": image_request}

    def _get_value(self, input_data, name, expected_type):
        """
        Get a value from input data or fall back to the node property.

        Args:
            input_data: Dictionary containing input values.
            name: Name of the parameter.
            expected_type: Type to convert the value to.

        Returns:
            The value converted to the expected type.
        """
        if name in input_data and input_data[name] is not None:
            value = input_data[name]
            if expected_type == bool:
                return bool(value)
            elif expected_type == int:
                return int(value)
            elif expected_type == float:
                return float(value)
            elif expected_type == str:
                return str(value)
            return value
        else:
            # Get from node property
            value = self.get_property(name)
            if value is None:
                return None

            if expected_type == bool:
                return bool(value)
            elif expected_type == int:
                return int(value)
            elif expected_type == float:
                return float(value)
            elif expected_type == str:
                return str(value)
            return value
