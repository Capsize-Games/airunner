#!/usr/bin/env python3
import os
from typing import Tuple, Optional
import random

import pygame
from pygame.locals import QUIT, KEYDOWN, K_ESCAPE, K_SPACE, K_RETURN

from airunner.api import API
from airunner.windows.pygame_window import PygameWindow
from airunner.windows.pygame_window import PygameManager
from airunner.handlers.llm.llm_response import LLMResponse
from airunner.handlers.stablediffusion.image_request import ImageRequest
from airunner.handlers.stablediffusion.image_response import ImageResponse
from airunner.pygame_example.pygame_agent import PygameAgent
from airunner.settings import (
    AIRUNNER_ART_MODEL_VERSION,
    AIRUNNER_ART_MODEL_PATH,
    AIRUNNER_ART_SCHEDULER,
    AIRUNNER_MAX_SEED,
)


class ExampleGame(PygameManager):
    """
    This simple example class demonstrates how to create a Pygame window
    using airunner, make an LLM request, and handle the response from the model
    """
    def _handle_llm_response(self, response: LLMResponse):
        print(response.message)
    
    def _handle_image_response(self, response: Optional[ImageResponse]):
        if response is None:
            self.api.logger.error("No message received from engine")
            return
        images = response.images
        if len(images) == 0:
            self.api.logger.debug("No images received from engine")
        elif response:
            image = images[0].convert("RGBA")
            image.save(os.path.expanduser("~/Desktop/output.png"))

    def _start(self):
        self.set_screen_color()
    
    def _process_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == KEYDOWN and event.key == K_ESCAPE:
                self.running = False
            elif event.type == KEYDOWN and event.key == K_SPACE:
                self.api.send_llm_request(
                    "Tell me a joke.", 
                    do_tts_reply=True
                )
            elif event.type == KEYDOWN and event.key == K_RETURN:
                self.api.send_image_request(
                    ImageRequest(
                        generator_name="stablediffusion",
                        prompt="A beautiful landscape",
                        negative_prompt="ugly, blurry",
                        model_path=AIRUNNER_ART_MODEL_PATH,
                        scheduler=AIRUNNER_ART_SCHEDULER,
                        version=AIRUNNER_ART_MODEL_VERSION,
                        use_compel=True,
                        width=512,
                        height=512,
                        steps=20,
                        seed=random.randint(-AIRUNNER_MAX_SEED, AIRUNNER_MAX_SEED),
                        strength=0.5,
                        n_samples=1,
                        scale=7.5,
                    )
                )
    
    def run(self):
        self.api.logger.info("Running pygame")
        self.running = True
        n = 0
        while self.running:
            try:
                self._process_events()
                pygame.time.delay(100)
            except Exception as e:
                self.api.logger.error(f"Error in run loop: {e}")
                self.running = False  # Ensure the loop breaks on error
    
    def set_screen_color(self, color: Optional[Tuple] = None):
        """
        Set the screen color for the Pygame window.
        """
        color = color or self.screen_color
        self.screen.fill(color)
    
    def quit(self):
        self.api.logger.info("Quitting pygame")
        self.running = False
        pygame.quit()


if __name__ == "__main__":
    airunner_api = API(
        main_window_class=PygameWindow,
        window_class_params={
            "width": 800,
            "height": 600,
            "game_class": ExampleGame,
            "local_agent_class": PygameAgent
        }
    )

    airunner_api.quit()
    pygame.quit()