#!/usr/bin/env python3
import os
from typing import Tuple, Optional
import random
import time

import pygame
from pygame.locals import QUIT, KEYDOWN, KEYUP, K_ESCAPE, K_SPACE, K_RETURN, K_UP, K_DOWN, K_LEFT, K_RIGHT

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
    def __init__(self, *args, **kwargs):
        self.generated_image = None
        self.image_position = (0, 0)  # Default position for the image
        self.player_pos = [400, 300]  # Start in the middle of the screen
        self.player_speed = 5
        self.player_size = 30
        self.player_color = (255, 0, 0)
        self.last_image_request_time = 0
        self.move_dirs = {K_UP: False, K_DOWN: False, K_LEFT: False, K_RIGHT: False}
        self.show_help_text = True
        self.font = None
        
        super().__init__(*args, **kwargs)
    
    def _handle_llm_response(self, response: LLMResponse):
        print(f"LLM response: {response.message}")
        self.show_message = response.message
        self.show_message_time = time.time() + 5  # Display for 5 seconds
    
    def _handle_image_response(self, response: Optional[ImageResponse]):
        if response is None:
            self.api.logger.error("No message received from engine")
            return
        
        images = response.images
        if len(images) == 0:
            self.api.logger.debug("No images received from engine")
        elif response:
            # Store the image in memory instead of saving to disk
            self.generated_image = images[0].convert("RGBA")
            
            # Calculate center position for the image
            if self.screen and self.generated_image:
                img_width, img_height = self.generated_image.size
                screen_width, screen_height = self.screen.get_size()
                x = (screen_width - img_width) // 2
                y = (screen_height - img_height) // 2
                self.image_position = (x, y)
            
            self.api.logger.info("Image received and ready for display")
            
    def _start(self):
        """Initialize the game state"""
        pygame.font.init()
        self.font = pygame.font.SysFont('Arial', 18)
        self.show_message = "Welcome to the AI Runner Pygame example!"
        self.show_message_time = time.time() + 5  # Show welcome message for 5 seconds
    
    def handle_pygame_event(self, event):
        """Handle Pygame events"""
        if event.type == QUIT:
            self.running = False
        
        elif event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                self.running = False
            elif event.key == K_SPACE:
                print("*"*100)
                self.api.send_llm_request(
                    "Tell me a joke.", 
                    do_tts_reply=True
                )
            elif event.key == K_RETURN:
                # Prevent spamming image requests (limit to once every 2 seconds)
                current_time = time.time()
                if current_time - self.last_image_request_time > 2:
                    self.last_image_request_time = current_time
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
            
            # Track movement keys
            elif event.key in self.move_dirs:
                self.move_dirs[event.key] = True
            
            # Toggle help text
            elif event.key == pygame.K_h:
                self.show_help_text = not self.show_help_text
                
        elif event.type == KEYUP:
            # Stop movement when keys are released
            if event.key in self.move_dirs:
                self.move_dirs[event.key] = False
    
    def process_events(self):
        """Process all pending Pygame events"""
        for event in pygame.event.get():
            self.handle_pygame_event(event)
    
    def update(self):
        """Update game state"""
        # Update player position based on movement keys
        if self.move_dirs[K_UP]:
            self.player_pos[1] -= self.player_speed
        if self.move_dirs[K_DOWN]:
            self.player_pos[1] += self.player_speed
        if self.move_dirs[K_LEFT]:
            self.player_pos[0] -= self.player_speed
        if self.move_dirs[K_RIGHT]:
            self.player_pos[0] += self.player_speed
        
        # Keep player in bounds
        self.player_pos[0] = max(self.player_size//2, min(self.width - self.player_size//2, self.player_pos[0]))
        self.player_pos[1] = max(self.player_size//2, min(self.height - self.player_size//2, self.player_pos[1]))
    
    def render(self):
        """Render the game state to the screen"""
        # Clear the screen
        self.screen.fill(self.screen_color)
        
        # Draw the generated image if it exists
        if self.generated_image:
            try:
                # Convert PIL Image to Pygame surface
                img_data = self.generated_image.tobytes()
                img_size = self.generated_image.size
                img_mode = self.generated_image.mode
                
                pygame_img = pygame.image.fromstring(img_data, img_size, img_mode)
                self.screen.blit(pygame_img, self.image_position)
            except Exception as e:
                self.api.logger.error(f"Error displaying image: {e}")
        
        # Draw the player
        pygame.draw.circle(self.screen, self.player_color, 
                           (int(self.player_pos[0]), int(self.player_pos[1])), 
                           self.player_size//2)
        
        # Draw message if active
        current_time = time.time()
        if hasattr(self, 'show_message') and hasattr(self, 'show_message_time') and current_time < self.show_message_time:
            message_surf = self.font.render(self.show_message, True, (255, 255, 255))
            message_rect = message_surf.get_rect(center=(self.width//2, 50))
            # Draw background for text
            pygame.draw.rect(self.screen, (0, 0, 0), 
                             pygame.Rect(message_rect.left - 5, message_rect.top - 5,
                                        message_rect.width + 10, message_rect.height + 10))
            self.screen.blit(message_surf, message_rect)
        
        # Draw help text
        if self.show_help_text and self.font:
            help_texts = [
                "Controls:",
                "Arrow keys: Move red circle",
                "Space: Request a joke",
                "Enter: Generate an image",
                "H: Toggle help text",
                "Esc: Quit"
            ]
            
            for i, text in enumerate(help_texts):
                help_surf = self.font.render(text, True, (255, 255, 255))
                self.screen.blit(help_surf, (10, self.height - (len(help_texts) - i) * 25))
    
    def run(self):
        """
        Initialize the game loop. The actual update loop is handled by the PygameWidget.
        """
        self.api.logger.info("Initializing pygame game loop")
        self.running = True
    
    def quit(self):
        """Clean up when the game is quitting"""
        self.api.logger.info("Quitting pygame")
        self.running = False


if __name__ == "__main__":
    airunner_api = API(
        main_window_class=PygameWindow,
        window_class_params={
            "width": 800,
            "height": 600,
            "game_class": ExampleGame,
            "local_agent_class": PygameAgent,
            "fps": 60
        }
    )

    airunner_api.quit()
    pygame.quit()