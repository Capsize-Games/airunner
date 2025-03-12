import pygame
import numpy as np
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL.GL import *


class GameExample:
    """Encapsulates Pygame game logic"""

    def __init__(self, width=640, height=480):
        pygame.init()
        self.width = width
        self.height = height
        self.surface = pygame.Surface((self.width, self.height))

    def update(self):
        """Update game state and draw to Pygame surface"""
        self.surface.fill((30, 30, 30))  # Dark gray background
        pygame.draw.circle(self.surface, (255, 0, 0), (self.width // 2, self.height // 2), 50)

    def get_surface(self):
        """Return the current Pygame surface"""
        return self.surface


class PygameOpenGLWidget(QOpenGLWidget):
    """QOpenGLWidget that integrates with Pygame rendering"""

    def __init__(self, width=640, height=480, parent=None):
        super().__init__(parent)
        self.width = width
        self.height = height
        self.game = GameExample(self.width, self.height)  # Create a Pygame instance
        self.texture_id = None  # OpenGL texture

        self.startTimer(16)  # ~60 FPS

    def initializeGL(self):
        """Initialize OpenGL settings"""
        glEnable(GL_TEXTURE_2D)
        glClearColor(0, 0, 0, 1)  # Black background

        # Generate OpenGL texture
        self.texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)

        # Texture settings
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    def paintGL(self):
        """Render Pygame surface to OpenGL texture"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Update game logic
        self.game.update()
        pygame_surface = self.game.get_surface()

        # Convert Pygame surface to NumPy array
        pygame_image = pygame.surfarray.array3d(pygame_surface)
        pygame_image = np.rot90(pygame_image, 3)  # Rotate for OpenGL alignment
        pygame_image = np.flip(pygame_image, axis=1)  # Flip horizontally

        # Bind and update OpenGL texture
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, self.width, self.height, 0, GL_RGB, GL_UNSIGNED_BYTE, pygame_image)

        # Draw a full-screen quad with the texture
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(-1, -1)
        glTexCoord2f(1, 0); glVertex2f(1, -1)
        glTexCoord2f(1, 1); glVertex2f(1, 1)
        glTexCoord2f(0, 1); glVertex2f(-1, 1)
        glEnd()

        glFlush()