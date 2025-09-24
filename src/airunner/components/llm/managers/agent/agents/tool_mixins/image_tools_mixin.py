import json
from typing import Annotated, Optional
import os
from llama_index.core.tools import FunctionTool
from airunner.enums import GeneratorSection, ImagePreset
from airunner.components.llm.managers.agent.agents.tool_mixins.tool_singleton_mixin import (
    ToolSingletonMixin,
)


class ImageToolsMixin(ToolSingletonMixin):
    """Mixin for image-related tools."""

    def __init__(self):
        self._generate_image_tool = None
        self._set_working_width_and_height = None

    @property
    def set_working_width_and_height(self):
        if not hasattr(self, "_set_working_width_and_height"):

            width_label = f"The width of the image. Currently: {self.application_settings.working_width}. "
            height_label = f"The height of the image. Currently: {self.application_settings.working_height}. "

            def set_working_width_and_height(
                width: Annotated[
                    Optional[int],
                    (
                        f"{width_label}"
                        "Min: 64, max: 2048. Must be a multiple of 64."
                    ),
                ],
                height: Annotated[
                    Optional[int],
                    (
                        f"{height_label}. "
                        "Min: 64, max: 2048. Must be a multiple of 64."
                    ),
                ],
            ) -> str:
                if width is not None:
                    self.update_application_settings(working_width=width)
                if height is not None:
                    self.update_application_settings(working_height=height)
                return f"Working width and height set to {width}x{height}."

            self._set_working_width_and_height = FunctionTool.from_defaults(
                set_working_width_and_height, return_direct=True
            )
        return self._set_working_width_and_height

    @property
    def generate_image_tool(self):
        if not hasattr(self, "_generate_image_tool"):
            image_preset_options = [item.value for item in ImagePreset]

            def generate_image(
                prompt: Annotated[
                    str,
                    (
                        "Describe the subject of the image along with the "
                        "composition, lighting, lens type and other "
                        "descriptors that will bring the image to life."
                    ),
                ],
                second_prompt: Annotated[
                    str,
                    (
                        "Describe the scene, the background, the colors, "
                        "the mood and other descriptors that will enhance "
                        "the image."
                    ),
                ],
                image_type: Annotated[
                    ImagePreset,
                    (
                        "The style preset for the image. "
                        f"Allowed values: {image_preset_options}."
                    ),
                ],
                width: Annotated[
                    int,
                    (
                        "The width of the image. "
                        "Min: 64, max: 2048. Must be a multiple of 64."
                    ),
                ],
                height: Annotated[
                    int,
                    (
                        "The height of the image. "
                        "Min: 64, max: 2048. Must be a multiple of 64."
                    ),
                ],
            ) -> str:
                if width % 64 != 0:
                    width = (width // 64) * 64
                if height % 64 != 0:
                    height = (height // 64) * 64
                # Normalize preset to string value
                try:
                    preset_val = (
                        image_type.value
                        if isinstance(image_type, ImagePreset)
                        else str(image_type)
                    )
                except Exception:
                    preset_val = ImagePreset.ILLUSTRATION.value
                # Emit the signal to continue the UI pipeline
                self.api.art.llm_image_generated(
                    prompt, second_prompt, preset_val, width, height
                )
                return json.dumps(
                    {
                        "prompt": prompt,
                        "second_prompt": second_prompt,
                        "preset": preset_val,
                        "width": width,
                        "height": height,
                    }
                )

            # Make the description very explicit for the LLM
            self._generate_image_tool = FunctionTool.from_defaults(
                generate_image,
                name="generate_image_tool",
                description="Generate an image based on a prompt, style, and settings. Use this tool to create or draw any kind of image, artwork, or visual content. Do NOT use the search tool for image generation.",
                return_direct=True,
            )
        return self._generate_image_tool

    @property
    def clear_canvas_tool(self):
        def clear_canvas() -> str:
            self.api.art.canvas.clear()
            return "Canvas cleared."

        return self._get_or_create_singleton(
            "_clear_canvas_tool",
            FunctionTool.from_defaults,
            clear_canvas,
            return_direct=True,
        )

    @property
    def open_image_from_path_tool(self):
        def open_image_from_path(
            image_path: Annotated[
                str,
                ("The path to the image file. Must be a valid file path."),
            ],
        ) -> str:
            if not os.path.isfile(image_path):
                return f"Unable to open image: {image_path} does not exist."
            self.api.art.canvas.image_from_path(image_path)
            return "Opening image..."

        return self._get_or_create_singleton(
            "_open_image_from_path_tool",
            FunctionTool.from_defaults,
            open_image_from_path,
            return_direct=True,
        )
