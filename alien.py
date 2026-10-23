import os

import pygame
from pygame.sprite import Sprite

from utils import create_placeholder_image, resource_path


class Alien(Sprite):
    """Представляет одного пришельца во флоте."""

    def __init__(self, ai_game):
        super().__init__()
        self.screen = ai_game.screen
        self.settings = ai_game.settings

        self.image = self._load_image()
        self.rect = self.image.get_rect()

        # Базовая позиция — НИКОГДА не меняется
        self.base_x = float(self.rect.x)
        self.base_y = float(self.rect.y)

    def _load_image(self, default_size=(60, 60), default_color=(128, 128, 128)):
        """Загружает изображение пришельца или создает заглушку."""
        image_path = resource_path("dop_fails/images/alien.bmp")

        if not os.path.exists(image_path):
            return create_placeholder_image(default_size, default_color)

        try:
            image = pygame.image.load(image_path)
            colorkey = image.get_at((0, 0))
            image.set_colorkey(colorkey)
            return image.convert()
        except pygame.error:
            return create_placeholder_image(default_size, default_color)

    def set_fleet_position(self, offset_x: int, offset_y: int):
        """Устанавливает позицию на основе базовой + глобальных смещений флота."""
        self.rect.x = round(self.base_x) + offset_x
        self.rect.y = round(self.base_y) + offset_y

    def check_edges(self):
        """Не используется напрямую. Оставлено для совместимости."""
        screen_rect = self.screen.get_rect()
        if self.settings.fleet_direction > 0:
            return self.rect.right >= screen_rect.right
        return self.rect.left <= 0