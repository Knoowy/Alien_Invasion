import pygame
import os
from pygame.sprite import Sprite
from utils import resource_path

class Ship(Sprite):
    """Управляет кораблем игрока."""

    def __init__(self, ai_game):
        super().__init__()
        self.screen = ai_game.screen
        self.settings = ai_game.settings
        self.screen_rect = ai_game.screen.get_rect()

        self.image = self._load_image()
        self.rect = self.image.get_rect()

        self.x = float(self.rect.x)

        self.moving_right = False
        self.moving_left = False

    def _load_image(self, default_size=(60, 54), default_color=(128, 128, 128)):
        """Загружает изображение корабля или создает заглушку."""
        image_path = resource_path('dop_fails/images/ship.bmp')

        if not os.path.exists(image_path):
            return self._create_placeholder(default_size, default_color)

        try:
            image = pygame.image.load(image_path)
            if image.get_flags() & pygame.SRCALPHA:
                return image.convert_alpha()
            return image.convert()
        except pygame.error:
            return self._create_placeholder(default_size, default_color)

    def _create_placeholder(self, size, color):
        """Создает изображение-заглушку."""
        width, height = size
        placeholder = pygame.Surface(size)
        placeholder.fill(color)
        font = pygame.font.Font(None, 20)
        text = font.render("No image", True, (255, 255, 255))
        text_rect = text.get_rect(center=(width // 2, height // 2))
        placeholder.blit(text, text_rect)
        return placeholder

    def center_ship(self):
        """Центрирует корабль на экране."""
        self.rect.midbottom = self.screen_rect.midbottom
        self.x = float(self.rect.x)

    def update(self):
        """Обновляет позицию корабля."""
        if self.moving_right and self.rect.right < self.screen_rect.right:
            self.x += self.settings.ship_speed
        if self.moving_left and self.rect.left > 0:
            self.x -= self.settings.ship_speed

        self.rect.x = int(self.x)

    def blit_me(self):
        """Отрисовывает корабль."""
        self.screen.blit(self.image, self.rect)