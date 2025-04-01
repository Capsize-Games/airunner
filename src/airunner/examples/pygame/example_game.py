#!/usr/bin/env python3
from typing import Optional
import random
import time

import pygame
from pygame.locals import QUIT, KEYDOWN, KEYUP, K_ESCAPE, K_SPACE, K_RETURN, K_UP, K_DOWN, K_LEFT, K_RIGHT

from airunner.api import API
from airunner.gui.windows.pygame_window import PygameWindow
from airunner.gui.windows.pygame_window import PygameAdapter
from airunner.handlers.llm.llm_response import LLMResponse
from airunner.handlers.stablediffusion.image_request import ImageRequest
from airunner.handlers.stablediffusion.image_response import ImageResponse
from airunner.examples.pygame.pygame_agent import PygameAgent
from airunner.settings import (
    AIRUNNER_ART_MODEL_VERSION,
    AIRUNNER_ART_MODEL_PATH,
    AIRUNNER_ART_SCHEDULER,
    AIRUNNER_MAX_SEED,
)


class ExampleGame(PygameAdapter):
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
        self.full_message = ""  # Store the complete message text
        self.font = None
        
        # Flag to avoid double event processing
        self.processed_events = set()
        
        super().__init__(*args, **kwargs)
    
    def _handle_llm_response(self, response: LLMResponse):
        """
        Handle streamed LLM responses by appending to a cumulative message
        """
        # Append to the full message instead of replacing
        if hasattr(self, 'full_message'):
            self.full_message += response.message
        else:
            self.full_message = response.message
            
        # Set the message to display
        self.show_message = self.full_message
        self.show_message_time = time.time() + 10  # Display for 10 seconds
    
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
        self.full_message = "Welcome to the AI Runner Pygame example!"
        self.show_message = self.full_message
        self.show_message_time = time.time() + 5  # Show welcome message for 5 seconds
    
    def handle_pygame_event(self, event):
        """
        Handle a single Pygame event without relying on the event queue.
        This helps avoid double-processing events.
        """
        # Create a unique identifier for this event to avoid duplicates
        event_id = (event.type, getattr(event, 'key', None), time.time())
        
        # If we've already processed this event, skip it
        if event_id in self.processed_events:
            return
            
        self.processed_events.add(event_id)
        # Keep the processed_events set from growing too large
        if len(self.processed_events) > 100:
            self.processed_events.clear()
        
        if event.type == QUIT:
            self.running = False
        
        elif event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                self.api.logger.info("ESC key pressed, quitting")
                self.running = False
                self.quit()  # Explicitly call quit to ensure clean shutdown
                
            elif event.key == K_SPACE:
                # Reset the full message when requesting a new joke
                self.full_message = ""
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
                
        elif event.type == KEYUP:
            # Stop movement when keys are released
            if event.key in self.move_dirs:
                self.move_dirs[event.key] = False
    
    def process_events(self):
        """Process all pending Pygame events"""
        # We now rely on handle_pygame_event being called directly from PygameWidget
        # This is important: we don't call pygame.event.get() here to avoid duplicate events
        pass
    
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
            # Split the message into lines if it's too long
            max_width = self.width - 40
            words = self.show_message.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = current_line + " " + word if current_line else word
                # Check if adding this word would make the line too long
                if self.font.size(test_line)[0] <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
            
            # Draw a text background
            if lines:
                total_height = len(lines) * self.font.get_height()
                max_line_width = max(self.font.size(line)[0] for line in lines)
                bg_rect = pygame.Rect(
                    (self.width - max_line_width) // 2 - 10,
                    50 - 5,
                    max_line_width + 20,
                    total_height + 10
                )
                pygame.draw.rect(self.screen, (0, 0, 0), bg_rect)
                
                # Draw each line
                for i, line in enumerate(lines):
                    line_surf = self.font.render(line, True, (255, 255, 255))
                    line_rect = line_surf.get_rect(center=(self.width//2, 50 + i * self.font.get_height()))
                    self.screen.blit(line_surf, line_rect)
        
        # Draw controls text at the bottom of the screen
        controls_text = "Controls: Arrow keys = Move red circle | Space = Request a joke | Enter = Generate an image | Esc = Quit"
        controls_surf = self.font.render(controls_text, True, (200, 200, 200))
        controls_rect = controls_surf.get_rect(midbottom=(self.width//2, self.height - 10))
        self.screen.blit(controls_surf, controls_rect)
    
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