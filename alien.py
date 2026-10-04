import pygame
import os
from pygame.sprite import Sprite
from utils import resource_path, create_placeholder_image


class Alien(Sprite):
    """Представляет одного пришельца во флоте."""

    def __init__(self, ai_game):
        super().__init__()
        self.screen = ai_game.screen
        self.settings = ai_game.settings

        self.image = self._load_image()
        self.rect = self.image.get_rect()

        self.rect.x = self.rect.width
        self.rect.y = self.rect.height

        self.x = float(self.rect.x)
        self.y = float(self.rect.y)

    def _load_image(self, default_size=(60, 60), default_color=(128, 128, 128)):
        """Загружает изображение пришельца или создает заглушку."""
        image_path = resource_path('dop_fails/images/alien.bmp')

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

    def check_edges(self):
        """Возвращает True, если пришелец достиг края экрана."""
        screen_rect = self.screen.get_rect()
        return (self.rect.right >= screen_rect.right) or (self.rect.left <= 0)

    def update(self, dt):
        """Перемещает пришельца вправо или влево."""
        self.x += self.settings.alien_speed * self.settings.fleet_direction * dt
        self.rect.x = int(self.x)

    def drop(self):
        """Опускает пришельца вниз."""
        self.y += self.settings.fleet_drop_speed
        self.rect.y = int(self.y)