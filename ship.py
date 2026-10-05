import os

import pygame
from pygame.sprite import Sprite

from utils import create_placeholder_image, resource_path


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

    def _load_image(self, default_size=(60, 60), default_color=(128, 128, 128)):
        """Загружает изображение корабля или создает заглушку."""
        image_path = resource_path("dop_fails/images/ship.bmp")

        if not os.path.exists(image_path):
            return create_placeholder_image(default_size, default_color)

        try:
            image = pygame.image.load(image_path)

            # Убираем белый фон
            colorkey = image.get_at((0, 0))
            image.set_colorkey(colorkey)

            return image.convert()
        except pygame.error:
            return create_placeholder_image(default_size, default_color)

    def center_ship(self):
        """Центрирует корабль на экране."""
        self.rect.midbottom = self.screen_rect.midbottom
        self.x = float(self.rect.x)

    def update(self, dt):
        """Обновляет позицию корабля."""
        if self.moving_right and self.rect.right < self.screen_rect.right:
            self.x += self.settings.ship_speed * dt
        if self.moving_left and self.rect.left > 0:
            self.x -= self.settings.ship_speed * dt

        self.rect.x = int(self.x)

    def blit_me(self):
        """Отрисовывает корабль."""
        self.screen.blit(self.image, self.rect)
