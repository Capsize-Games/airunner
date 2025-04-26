from typing import Dict
from PySide6.QtWidgets import QFileDialog

from NodeGraphQt.constants import NodePropWidgetEnum

from airunner.gui.widgets.nodegraph.nodes.art.base_art_node import (
    BaseArtNode,
)
from airunner.handlers.stablediffusion.image_request import ImageRequest
from airunner.enums import ImagePreset, Scheduler, StableDiffusionVersion


class ImageRequestNode(BaseArtNode):
    """
    A node that outputs an ImageRequest object with configurable parameters.

    This node provides input ports for all ImageRequest parameters and outputs
    a properly constructed ImageRequest object for stable diffusion image generation.
    """

    NODE_NAME = "Image Request"
    has_exec_in_port = False
    has_exec_out_port = False

    def __init__(self):
        super().__init__()

        # Add inputs for ImageRequest parameters
        self.add_input("pipeline_action", display_name=True)
        self.add_input("generator_name", display_name=True)
        self.add_input("prompt", display_name=True)
        self.add_input("negative_prompt", display_name=True)
        self.add_input("second_prompt", display_name=True)
        self.add_input("second_negative_prompt", display_name=True)
        self.add_input("random_seed", display_name=True)
        self.add_input("model_path", display_name=True)
        self.add_input("custom_path", display_name=True)
        self.add_input("scheduler", display_name=True)
        self.add_input("version", display_name=True)
        self.add_input("use_compel", display_name=True)
        self.add_input("steps", display_name=True)
        self.add_input("ddim_eta", display_name=True)
        self.add_input("scale", display_name=True)
        self.add_input("seed", display_name=True)
        self.add_input("strength", display_name=True)
        self.add_input("n_samples", display_name=True)
        self.add_input("clip_skip", display_name=True)
        self.add_input("lora_scale", display_name=True)
        self.add_input("image_width", display_name=True)
        self.add_input("image_height", display_name=True)
        self.add_input("image_preset", display_name=True)

        # Add output port for the ImageRequest object
        self.add_output("image_request")
        scheduler_values = [scheduler.value for scheduler in Scheduler]
        props = [
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
                "name": "custom_path_button",
                "value": "Browse",
                "widget_type": NodePropWidgetEnum.BUTTON,
                "tab": "model",
            },
            {
                "name": "scheduler",
                "value": Scheduler.DPM_PP_2M_SDE_K.value,
                "items": scheduler_values,
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
        ]

        for prop in props:
            self.create_property(
                prop["name"],
                prop["value"],
                widget_type=prop["widget_type"].value,
                tab=prop["tab"],
                range=prop.get("range"),
                items=prop.get("items"),
            )

        # Enum parameter using built-in combo box
        preset_values = [preset.name for preset in ImagePreset]
        self.create_property(
            "image_preset",
            ImagePreset.NONE.name,
            items=preset_values,
            widget_type=NodePropWidgetEnum.QCOMBO_BOX.value,
            tab="generation",
        )

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
