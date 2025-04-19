from typing import Dict

from NodeGraphQt.constants import NodePropWidgetEnum

from airunner.gui.widgets.nodegraph.nodes.base_workflow_node import (
    BaseWorkflowNode,
)
from airunner.handlers.stablediffusion.image_request import ImageRequest
from airunner.enums import ImagePreset


class ImageRequestNode(BaseWorkflowNode):
    """
    A node that outputs an ImageRequest object with configurable parameters.

    This node provides input ports for all ImageRequest parameters and outputs
    a properly constructed ImageRequest object for stable diffusion image generation.
    """

    NODE_NAME = "Image Request"
    __identifier__ = "airunner.workflow.nodes"  # Ensure consistent identifier

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

        # String parameters using built-in string widget
        self.create_property(
            "pipeline_action",
            "txt2img",
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            tab="basic",
        )

        self.create_property(
            "generator_name",
            "stablediffusion",
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            tab="basic",
        )

        self.create_property(
            "prompt",
            "",
            widget_type=NodePropWidgetEnum.QTEXT_EDIT.value,
            tab="prompt",
        )

        self.create_property(
            "negative_prompt",
            "",
            widget_type=NodePropWidgetEnum.QTEXT_EDIT.value,
            tab="prompt",
        )

        self.create_property(
            "second_prompt",
            "",
            widget_type=NodePropWidgetEnum.QTEXT_EDIT.value,
            tab="prompt",
        )

        self.create_property(
            "second_negative_prompt",
            "",
            widget_type=NodePropWidgetEnum.QTEXT_EDIT.value,
            tab="prompt",
        )

        self.create_property(
            "model_path",
            "",
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            tab="model",
        )

        self.create_property(
            "scheduler",
            "DDIM",
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            tab="model",
        )

        self.create_property(
            "version",
            "SD 1.5",
            widget_type=NodePropWidgetEnum.QLINE_EDIT.value,
            tab="model",
        )

        # Boolean parameters using built-in checkbox widget
        self.create_property(
            "random_seed",
            True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="generation",
        )

        self.create_property(
            "use_compel",
            True,
            widget_type=NodePropWidgetEnum.QCHECK_BOX.value,
            tab="prompt",
        )

        # Integer parameters using built-in integer widget
        self.create_property(
            "steps",
            20,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(1, 150),
            tab="generation",
        )

        self.create_property(
            "seed",
            42,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(0, 2147483647),
            tab="generation",
        )

        self.create_property(
            "n_samples",
            1,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(1, 8),
            tab="generation",
        )

        self.create_property(
            "clip_skip",
            0,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(0, 12),
            tab="advanced",
        )

        self.create_property(
            "image_width",
            512,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(64, 2048),
            tab="generation",
        )

        self.create_property(
            "image_height",
            512,
            widget_type=NodePropWidgetEnum.INT.value,
            range=(64, 2048),
            tab="generation",
        )

        # Float parameters using built-in float widget
        self.create_property(
            "ddim_eta",
            0.5,
            widget_type=NodePropWidgetEnum.FLOAT.value,
            range=(0.0, 1.0),
            tab="advanced",
        )

        self.create_property(
            "scale",
            7.5,
            widget_type=NodePropWidgetEnum.FLOAT.value,
            range=(1.0, 30.0),
            tab="generation",
        )

        self.create_property(
            "strength",
            0.5,
            widget_type=NodePropWidgetEnum.FLOAT.value,
            range=(0.0, 1.0),
            tab="generation",
        )

        self.create_property(
            "lora_scale",
            1.0,
            widget_type=NodePropWidgetEnum.FLOAT.value,
            range=(0.0, 2.0),
            tab="advanced",
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
