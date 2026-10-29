import math
import os

import pygame
from pygame.sprite import Sprite

from utils import create_placeholder_image, resource_path

# AI NOT CHECK
class Boss(Sprite):
    """Босс — большой враг с HP, фазами и атаками (луч, бомбы, пули)."""

    HP_BAR_WIDTH = 500
    HP_BAR_HEIGHT = 18

    def __init__(self, ai_game):
        super().__init__()
        self.screen = ai_game.screen
        self.screen_rect = ai_game.screen.get_rect()
        self.settings = ai_game.settings

        self.original_image = self._load_image()
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect()

        self.center_x = self.screen_rect.centerx
        self.base_y = self.screen_rect.top + 250
        self.rect.centerx = self.center_x
        self.rect.centery = self.base_y

        self.time = 0.0

        # Характеристики (уже посчитаны в Settings из уровня)
        self.max_hp = self.settings.boss_hp
        self.hp = self.max_hp

        # Движение — только горизонтальное
        self.move_speed = self.settings.boss_move_speed
        self.amplitude_x = (self.screen_rect.width - self.rect.width) / 2
        # amplitude_y = 0: босс не двигается по вертикали

        # Таймеры атак
        self.shoot_timer = self.settings.boss_shoot_intervals[1]
        self.beam_timer = self.settings.boss_beam_cooldowns[1]
        self.bombing_timer = self.settings.boss_bombing_cooldowns[1]

        self.spawn_timer = 0.0
        self.spawn_duration = self.settings.BOSS_SPAWN_DURATION

        self.phase = 1
        self.phase_flash_timer = 0.0

    def _load_image(self):
        boss_path = resource_path("dop_fails/images/boss.bmp")
        if os.path.exists(boss_path):
            try:
                image = pygame.image.load(boss_path)
                colorkey = image.get_at((0, 0))
                image.set_colorkey(colorkey)
                return image.convert_alpha()
            except pygame.error:
                pass

        alien_path = resource_path("dop_fails/images/alien.bmp")
        if os.path.exists(alien_path):
            try:
                image = pygame.image.load(alien_path)
                scaled = pygame.transform.scale(image, (180, 180))
                colorkey = scaled.get_at((0, 0))
                scaled.set_colorkey(colorkey)
                return scaled.convert_alpha()
            except pygame.error:
                pass

        return create_placeholder_image((180, 180), (180, 60, 180), "BOSS")

    def update(self, dt):
        self.spawn_timer = min(self.spawn_timer + dt, self.spawn_duration)

        if self.phase_flash_timer > 0:
            self.phase_flash_timer -= dt

        hp_ratio = self.hp / self.max_hp
        new_phase = 1 if hp_ratio > 0.66 else 2 if hp_ratio > 0.33 else 3

        if new_phase > self.phase:
            self.phase = new_phase
            self.phase_flash_timer = 0.5
            #Ускорение по горизонтали
            self.move_speed *= 1.1

        if self.is_spawning():
            self.rect.centerx = self.center_x
            return

        # Движение только по горизонтали (синусоида по X)
        self.time += dt * self.move_speed
        if self.time > 2 * math.pi:
            self.time -= 2 * math.pi

        offset_x = math.sin(self.time) * self.amplitude_x
        self.rect.centerx = round(self.center_x + offset_x)

    def is_spawning(self) -> bool:
        return self.spawn_timer < self.spawn_duration

    def get_spawn_progress(self) -> float:
        if self.spawn_duration <= 0:
            return 1.0
        return min(1.0, self.spawn_timer / self.spawn_duration)

    def take_damage(self) -> bool:
        self.hp -= 1
        return self.hp <= 0

    def shoot(self, ai_game):
        """Создаёт обычные пули. Все красные, паттерн зависит от фазы."""
        bullets = []
        bx, by = self.rect.midbottom
        red = (255, 80, 80)

        if self.phase == 1:
            bullets.append(BossBullet(ai_game, bx, by, color=red))
        elif self.phase == 2:
            for angle in (-20, 0, 20):
                rad = math.radians(angle)
                bullets.append(
                    BossBullet(ai_game, bx, by, math.sin(rad), math.cos(rad), color=red)
                )
        else:
            ship = ai_game.ship
            dx = ship.rect.centerx - bx
            dy = ship.rect.centery - by
            dist = math.hypot(dx, dy)
            if dist > 0:
                bullets.append(
                    BossBullet(ai_game, bx, by, dx / dist, dy / dist, color=red)
                )
            for angle in (-15, 15):
                rad = math.radians(angle)
                bullets.append(
                    BossBullet(ai_game, bx, by, math.sin(rad), math.cos(rad), color=red)
                )

        return bullets

    def blit_me(self):
        """Рисует босса с эффектом материализации и вспышкой фазы."""
        if self.is_spawning():
            progress = self.get_spawn_progress()
            ease = 1 - (1 - progress) ** 3

            portal_radius = int(self.rect.width * 0.8 * ease)
            portal_alpha = int(150 * (1 - progress))
            if portal_radius > 0 and portal_alpha > 0:
                portal_surface = pygame.Surface(
                    (portal_radius * 2, portal_radius * 2), pygame.SRCALPHA
                )
                pygame.draw.circle(
                    portal_surface,
                    (255, 50, 50, portal_alpha),
                    (portal_radius, portal_radius),
                    portal_radius,
                    5,
                )
                self.screen.blit(
                    portal_surface, portal_surface.get_rect(center=self.rect.center)
                )

            scale = 0.3 + 0.7 * ease
            new_w = int(self.original_image.get_width() * scale)
            new_h = int(self.original_image.get_height() * scale)

            if new_w > 0 and new_h > 0:
                scaled_image = pygame.transform.smoothscale(
                    self.original_image, (new_w, new_h)
                )
                scaled_image.set_alpha(int(255 * progress))
                self.screen.blit(
                    scaled_image, scaled_image.get_rect(center=self.rect.center)
                )
            return

        image_to_draw = self.original_image

        if self.phase_flash_timer > 0:
            flash_image = self.original_image.copy()
            flash_image.fill((255, 100, 100, 255), special_flags=pygame.BLEND_RGBA_MULT)
            if int(self.phase_flash_timer * 20) % 2 == 0:
                image_to_draw = flash_image

        self.screen.blit(image_to_draw, self.rect)

    def draw_hp_bar(self, screen, screen_width):
        bar_width = self.HP_BAR_WIDTH
        bar_height = self.HP_BAR_HEIGHT
        bar_x = (screen_width - bar_width) // 2
        bar_y = 100

        pygame.draw.rect(
            screen, (40, 40, 40), (bar_x, bar_y, bar_width, bar_height), border_radius=5
        )

        spawn_progress = self.get_spawn_progress()
        ratio = max(0.0, (self.hp / self.max_hp) * spawn_progress)
        fill_width = int(bar_width * ratio)

        if fill_width > 0:
            if self.phase == 1:
                color = (60, 200, 60)
            elif self.phase == 2:
                color = (220, 180, 40)
            else:
                color = (220, 60, 60)
            pygame.draw.rect(
                screen, color, (bar_x, bar_y, fill_width, bar_height), border_radius=5
            )

        for mark in (0.33, 0.66):
            mark_x = bar_x + int(bar_width * mark)
            pygame.draw.line(
                screen,
                (255, 255, 255),
                (mark_x, bar_y),
                (mark_x, bar_y + bar_height),
                2,
            )

        pygame.draw.rect(
            screen,
            (200, 200, 200),
            (bar_x, bar_y, bar_width, bar_height),
            2,
            border_radius=5,
        )


# ═══════════════════════════════════════════════════════════════════
# АТАКА 1: ЛУЧ СТРОГО ВНИЗ С ТЕЛЕГРАФОМ
# ═══════════════════════════════════════════════════════════════════
class BeamAttack:
    """Мощный луч, бьющий СТРОГО ВНИЗ от босса. Направление фиксировано."""

    def __init__(self, ai_game, boss):
        self.screen = ai_game.screen
        self.settings = ai_game.settings
        self.boss = boss

        # Направление всегда вниз
        self.dx = 0.0
        self.dy = 1.0

        self.telegraph_time = self.settings.BOSS_BEAM_TELEGRAPH
        self.fire_time = 0
        self.state = "telegraph"

    @property
    def origin(self):
        """Луч всегда исходит из текущей позиции босса."""
        return (self.boss.rect.centerx, self.boss.rect.bottom)

    def update(self, dt):
        if self.state == "telegraph":
            self.telegraph_time -= dt
            if self.telegraph_time <= 0:
                self.state = "firing"
                self.fire_time = self.settings.BOSS_BEAM_DURATION
        elif self.state == "firing":
            self.fire_time -= dt
            if self.fire_time <= 0:
                self.state = "done"

    def _get_end_point(self):
        screen_h = self.screen.get_height()
        return (self.origin[0], self.origin[1] + screen_h * 2)

    def draw(self):
        if self.state == "done":
            return

        screen_w = self.screen.get_width()
        screen_h = self.screen.get_height()
        end_x, end_y = self._get_end_point()
        origin = self.origin

        if self.state == "telegraph":
            progress = 1 - (self.telegraph_time / self.settings.BOSS_BEAM_TELEGRAPH)
            pulse = 0.5 + 0.5 * abs(math.sin(pygame.time.get_ticks() * 0.015))

            # Широкая аура
            glow = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            pygame.draw.line(glow, (255, 30, 30, 50), origin, (end_x, end_y), 40)
            pygame.draw.line(glow, (255, 60, 60, 90), origin, (end_x, end_y), 20)
            self.screen.blit(glow, (0, 0))

            # Растущая линия
            current_end_y = origin[1] + (end_y - origin[1]) * progress
            bright = int(200 + 55 * pulse)
            pygame.draw.line(
                self.screen, (bright, 30, 30), origin, (origin[0], current_end_y), 6
            )
            pygame.draw.line(
                self.screen, (bright, 150, 150), origin, (origin[0], current_end_y), 2
            )

            # Бегущие точки
            tick = pygame.time.get_ticks() * 0.005
            for i in range(10):
                t = ((tick + i / 10) % 1.0) * progress
                dot_y = origin[1] + (end_y - origin[1]) * t
                pygame.draw.circle(
                    self.screen, (255, 200, 200), (origin[0], int(dot_y)), 4
                )

            # Мерцающий круг у основания
            base_pulse = int(15 + 10 * pulse)
            pygame.draw.circle(self.screen, (255, 100, 100), origin, base_pulse, 2)

        elif self.state == "firing":
            progress = 1 - (self.fire_time / self.settings.BOSS_BEAM_DURATION)
            width = int(self.settings.BOSS_BEAM_WIDTH * (1 - progress * 0.3))

            # Аура
            glow = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            pygame.draw.line(
                glow, (255, 50, 50, 120), origin, (end_x, end_y), width + 30
            )
            pygame.draw.line(
                glow, (255, 150, 150, 180), origin, (end_x, end_y), width + 10
            )
            self.screen.blit(glow, (0, 0))

            # Луч
            pygame.draw.line(self.screen, (255, 80, 80), origin, (end_x, end_y), width)
            pygame.draw.line(
                self.screen, (255, 255, 255), origin, (end_x, end_y), max(2, width // 3)
            )

            # Вспышка у основания
            flash_radius = int(30 * (1 - progress))
            if flash_radius > 0:
                flash = pygame.Surface(
                    (flash_radius * 2, flash_radius * 2), pygame.SRCALPHA
                )
                pygame.draw.circle(
                    flash,
                    (255, 255, 200, 200),
                    (flash_radius, flash_radius),
                    flash_radius,
                )
                self.screen.blit(
                    flash, (origin[0] - flash_radius, origin[1] - flash_radius)
                )

    def check_hit(self, ship_rect) -> bool:
        if self.state != "firing":
            return False

        origin = self.origin
        # Луч вертикальный → проверяем попадание по X
        half_width = self.settings.BOSS_BEAM_WIDTH / 2
        ship_center_x = ship_rect.centerx
        # Расстояние по X от оси луча до центра корабля
        dx = abs(ship_center_x - origin[0])
        # Корабль ниже босса (по Y)
        return dx < (half_width + ship_rect.width / 2) and ship_rect.centery > origin[1]


# ═══════════════════════════════════════════════════════════════════
# АТАКА 2: КОВРОВАЯ БОМБАРДИРОВКА
# ═══════════════════════════════════════════════════════════════════
class BombMarker:
    """Маркер бомбардировки — растёт, затем взрывается, нанося урон в зоне."""

    EXPLOSION_DURATION = 0.4

    def __init__(self, ai_game, x, y):
        self.screen = ai_game.screen
        self.settings = ai_game.settings
        self.x = x
        self.y = y
        self.radius = self.settings.BOSS_BOMBING_RADIUS

        self.timer = self.settings.BOSS_BOMBING_TELEGRAPH
        self.duration = self.settings.BOSS_BOMBING_TELEGRAPH

        self.exploded = False
        self.explosion_timer = 0.0

    def update(self, dt):
        if not self.exploded:
            self.timer -= dt
            if self.timer <= 0:
                self.exploded = True
                self.explosion_timer = self.EXPLOSION_DURATION
        else:
            self.explosion_timer -= dt

    def is_alive(self) -> bool:
        return not self.exploded or self.explosion_timer > 0

    def check_hit(self, ship_rect) -> bool:
        if not self.exploded:
            return False
        closest_x = max(ship_rect.left, min(self.x, ship_rect.right))
        closest_y = max(ship_rect.top, min(self.y, ship_rect.bottom))
        dist = math.hypot(self.x - closest_x, self.y - closest_y)
        return dist < self.radius

    def draw(self):
        if not self.exploded:
            progress = 1 - (self.timer / self.duration)
            inner_radius = int(self.radius * progress)
            pulse = 0.5 + 0.5 * abs(math.sin(pygame.time.get_ticks() * 0.012))

            border_color = (255, int(80 + 100 * pulse), int(80 + 100 * pulse))
            pygame.draw.circle(
                self.screen, border_color, (self.x, self.y), self.radius, 3
            )

            if inner_radius > 0:
                fill = pygame.Surface(
                    (inner_radius * 2, inner_radius * 2), pygame.SRCALPHA
                )
                pygame.draw.circle(
                    fill, (255, 60, 60, 90), (inner_radius, inner_radius), inner_radius
                )
                self.screen.blit(fill, (self.x - inner_radius, self.y - inner_radius))

            core = int(6 + 6 * pulse)
            pygame.draw.circle(self.screen, (255, 200, 200), (self.x, self.y), core)
        else:
            progress = 1 - (self.explosion_timer / self.EXPLOSION_DURATION)
            current_radius = int(self.radius * (0.6 + 0.6 * progress))
            alpha = int(255 * (1 - progress))

            explosion = pygame.Surface(
                (current_radius * 2, current_radius * 2), pygame.SRCALPHA
            )
            pygame.draw.circle(
                explosion,
                (255, 230, 150, alpha),
                (current_radius, current_radius),
                current_radius,
            )
            pygame.draw.circle(
                explosion,
                (255, 150, 50, alpha),
                (current_radius, current_radius),
                int(current_radius * 0.75),
            )
            pygame.draw.circle(
                explosion,
                (255, 80, 30, alpha),
                (current_radius, current_radius),
                int(current_radius * 0.5),
            )
            pygame.draw.circle(
                explosion,
                (255, 255, 255, alpha),
                (current_radius, current_radius),
                int(current_radius * 0.2),
            )

            self.screen.blit(
                explosion, (self.x - current_radius, self.y - current_radius)
            )


# ═══════════════════════════════════════════════════════════════════
# ОБЫЧНЫЕ ПУЛИ БОССА (лазеры, БЕЗ белого ядра)
# ═══════════════════════════════════════════════════════════════════
class BossBullet(Sprite):
    """Пуля босса — красный вытянутый лазер без белого ядра."""

    def __init__(self, ai_game, x, y, vx=0, vy=1, color=(255, 80, 80)):
        super().__init__()
        self.screen = ai_game.screen

        length = math.hypot(vx, vy)
        if length == 0:
            vx, vy = 0, 1
            length = 1

        self.speed = ai_game.settings.BOSS_BULLET_SPEED
        self.vx = (vx / length) * self.speed
        self.vy = (vy / length) * self.speed

        base_w, base_h = 24, 6
        base_surface = pygame.Surface((base_w, base_h), pygame.SRCALPHA)

        # Красный лазер — только основной цвет, без белого ядра
        pygame.draw.rect(
            base_surface, (*color, 220), (0, 0, base_w, base_h), border_radius=3
        )

        angle = math.degrees(math.atan2(-vy, vx))
        self.image = pygame.transform.rotate(base_surface, angle)
        self.rect = self.image.get_rect(center=(x, y))

        self.x = float(self.rect.centerx)
        self.y = float(self.rect.centery)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rect.centerx = round(self.x)
        self.rect.centery = round(self.y)

    def draw(self):
        self.screen.blit(self.image, self.rect)