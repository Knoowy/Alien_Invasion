import pygame
import random


class Star:
    """Одна звезда — точка, летящая вниз."""

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.reset(initial=True)

    def reset(self, initial=False):
        """Пересоздаёт звезду. initial=True — случайная позиция по Y."""
        self.x = random.randint(0, self.screen_width)
        if initial:
            self.y = random.randint(0, self.screen_height)
        else:
            self.y = -5

        self.size = random.choice([1, 1, 1, 2, 2, 3])
        self.speed = self.size * 0.5 + random.uniform(0.2, 0.8)
        self.brightness = random.randint(200, 255)

    def update(self, speed_multiplier=1.0):
        """Двигает звезду вниз с учётом множителя скорости."""
        self.y += self.speed * speed_multiplier
        if self.y > self.screen_height:
            self.reset()

    def draw(self, screen, speed_multiplier):
        color = (self.brightness, self.brightness, self.brightness)
         # Длина шлейфа пропорциональна скорости
         
        # Шлейф появляется ТОЛЬКО при ускорении (speed > 1.0)
        boost = max(0.0, speed_multiplier - 1.0)
        
        trail_length = int(self.speed * boost * 8)
        if trail_length <= 3:
            pygame.draw.circle(
            screen, color,
            (int(self.x), int(self.y)), self.size)
        else:
            # Линия (эффект гиперпрыжка)
            start = (int(self.x), int(self.y) - trail_length)
            end = (int(self.x), int(self.y))
            width = 1 if self.size == 1 else self.size - 1
            pygame.draw.line(screen, color, start, end, width)

class StarField:
    """Набор звёзд — целое звёздное небо."""

    def __init__(self, screen_width, screen_height, count=120):
        self.stars = [
            Star(screen_width, screen_height)
            for _ in range(count)
        ]
        self.speed_multiplier = 1.0   # множитель для гиперпрыжка

    def update(self):
        for star in self.stars:
            star.update(self.speed_multiplier)

    def draw(self, screen):
        for star in self.stars:
            star.draw(screen, self.speed_multiplier)
