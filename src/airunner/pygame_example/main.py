#!/usr/bin/env python3
from typing import Tuple, Optional, Dict

import pygame
from pygame.locals import QUIT, KEYDOWN, K_ESCAPE, K_SPACE

from airunner.api import API
from airunner.windows.pygame_window import PygameWindow
from airunner.windows.pygame_window import PygameManager
from airunner.enums import SignalCode
from airunner.handlers.llm.llm_response import LLMResponse
from airunner.handlers.llm.llm_request import LLMRequest

from airunner.pygame_example.pygame_agent import PygameAgent


class ExampleGame(PygameManager):
    """
    This simple example class demonstrates how to create a Pygame window
    using airunner, make an LLM request, and handle the response from the model
    """
    def _handle_llm_response(self, response: LLMResponse):
        print(response.message)

    def _start(self):
        self.set_screen_color()
    
    def _process_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == KEYDOWN and event.key == K_ESCAPE:
                self.running = False
            elif event.type == KEYDOWN and event.key == K_SPACE:
                self.api.send_llm_request("Tell me a joke.")
    
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