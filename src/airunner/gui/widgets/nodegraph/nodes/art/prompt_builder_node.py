import random
from typing import Dict

from airunner.gui.widgets.nodegraph.nodes.art.base_art_node import (
    BaseArtNode,
)


class PromptBuilderNode(BaseArtNode):
    """
    A node that outputs a Lora configuration as a dictionary.

    This node provides input ports for all Lora model parameters and outputs
    a dictionary with the Lora configuration.
    """

    NODE_NAME = "Prompt Builder"
    has_exec_in_port: bool = False
    has_exec_out_port: bool = False
    _output_ports = [
        dict(name="prompt", display_name="Prompt"),
    ]

    def execute(self, input_data: Dict):
        return {
            "prompt": self.random_prompt(),
            "_exec_triggered": self.EXEC_OUT_PORT_NAME,
        }

    def random_prompt(self):
        artist = random.choice(["Van Gogh", "Picasso", "Da Vinci"])
        style = random.choice(["realistic", "fantasy", "abstract", "anime"])
        subject = random.choice(["cat", "dog", "landscape"])
        background = random.choice(["white", "black", "blue"])
        setting = random.choice(["studio", "outdoor", "indoor"])
        lighting = random.choice(["soft", "hard", "natural"])
        camera_angle = random.choice(["wide", "close-up", "medium"])
        color_palette = random.choice(["vibrant", "pastel", "monochrome"])
        mood = random.choice(["happy", "sad", "mysterious"])
        composition = random.choice(["symmetrical", "asymmetrical", "dynamic"])
        art_style = random.choice(["impressionism", "cubism", "surrealism"])
        medium = random.choice(["oil painting", "watercolor", "digital"])
        prompt = f"{artist} {style} {subject} {background} {setting} {lighting} {camera_angle} {color_palette} {mood} {composition} {art_style} {medium}"
        return prompt
