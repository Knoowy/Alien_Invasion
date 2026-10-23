import os
import sys
import time
from enum import Enum, auto

# Скрываем приветствие Pygame
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import logging

import pygame

from alien import Alien
from bullet import Bullet
from button import Button
from scoreboard import Scoreboard
from settings import Settings
from ship import Ship
from slider import Slider
from starfield import StarField
from style import (
    FLEET_ROWS_BELOW,
    FLEET_TOP_OFFSET,
    FONT_SIZE_LARGE,
    INSTRUCTIONS,
    TEXT_COLOR,
)
from utils import load_font, resource_path

logger = logging.getLogger(__name__)


class GameState(Enum):
    """Возможные состояния игры."""

    MENU = auto()
    PLAYING = auto()
    PAUSED = auto()
    TRANSITION = auto()


class AlienInvasion:
    """Управляет игровыми ресурсами и поведением."""

    # region 1. ИНИЦИАЛИЗАЦИЯ
    def __init__(self):
        pygame.init()

        self.audio_enabled = True
        try:
            pygame.mixer.init()
        except pygame.error as e:
            logger.warning(f"Аудио недоступно: {e}")
            self.audio_enabled = False

        logger.info("Инициализация игры")

        self._setup_display()
        self._set_window_icon()

        self.clock = pygame.time.Clock()
        self.settings = Settings()
        self._update_settings_for_display()

        pygame.display.set_caption("Alien Invasion")

        self.score = 0
        self.ships_left = self.settings.ship_limit

        self.ship = Ship(self)
        self.bullets = pygame.sprite.Group()
        self.aliens = pygame.sprite.Group()

        # Глобальные смещения флота (для детерминированного движения)
        self._fleet_offset_x = 0.0
        self._fleet_offset_y = 0

        # Звёздное небо
        self.starfield = StarField(
            self.screen_rect.width, self.screen_rect.height, count=200
        )

        self.sb = Scoreboard(
            screen=self.screen,
            screen_rect=self.screen_rect,
            settings=self.settings,
            game=self,
            ship_factory=lambda: Ship(self),
        )
        self.play_button = Button(self, "Play")

        self._init_sounds()
        self._init_text_rendering()
        self._preload_instructions()
        self._init_color_sliders()

        # ─── Стейт-машина ────────────────────────────────────────
        self.state = GameState.MENU

        self.fon_music_active = False
        self._mouse_visible = False

        # Гиперпрыжок (временный эффект внутри TRANSITION)
        self.transition_start_time = 0
        self.TRANSITION_DURATION = 1.0
        self._transition_callback = None

        # Fade-in (временный эффект)
        self.fade_in = False
        self.fade_in_start_time = 0
        self.FADE_IN_DURATION = 1.0

        self._overlay_alpha = 0
        self._overlay_surface = pygame.Surface(self.screen_rect.size)
        self._overlay_surface.fill((0, 0, 0))

        # Таймер респавна
        self.respawn_timer = 0.0
        self.RESPAWN_DURATION = 0.5

    def _setup_display(self):
        try:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        except pygame.error as e:
            logger.warning(f"Не удалось установить полноэкранный режим: {e}")
            try:
                display_info = pygame.display.Info()
                width, height = display_info.current_w, display_info.current_h
                if width == 0 or height == 0:
                    raise ValueError("Не удалось получить информацию о дисплее")
                self.screen = pygame.display.set_mode((width, height))
            except (pygame.error, ValueError) as e2:
                logger.critical(f"Критическая ошибка: не удалось создать окно: {e2}")
                pygame.quit()
                sys.exit(1)
        self.screen_rect = self.screen.get_rect()

    def _set_window_icon(self):
        icon_path = resource_path("dop_fails/images/ai_bmp.bmp")
        try:
            icon = pygame.image.load(icon_path)
            pygame.display.set_icon(icon)
        except (FileNotFoundError, pygame.error) as e:
            logger.warning(f"Не удалось загрузить иконку для окна: {e}")

    def _update_settings_for_display(self):
        self.settings.screen_width = self.screen_rect.width
        self.settings.screen_height = self.screen_rect.height

    def _init_text_rendering(self):
        """Инициализирует настройки рендеринга текста."""
        self.font = load_font(FONT_SIZE_LARGE)
        self.text_cache = {}

    def _preload_instructions(self):
        y_position = self.play_button.rect.y - 100
        for i, text in enumerate(INSTRUCTIONS):
            text_image = self.font.render(text, True, TEXT_COLOR)
            text_rect = text_image.get_rect()
            text_rect.centerx = int(self.screen_rect.centerx * 0.5)
            text_rect.top = y_position
            self.text_cache[i] = {"image": text_image, "rect": text_rect}
            y_position += 50

    def _init_color_sliders(self):
        panel_w, panel_h = 480, 240
        panel_x = self.screen_rect.centerx - int(panel_w // 2)
        panel_y = self.screen_rect.bottom - panel_h - 40
        self.color_panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

        label_offset = 100
        slider_w = panel_w - label_offset - 40
        r, g, b = self.settings.bg_color

        self.color_sliders = [
            Slider(
                panel_x + label_offset,
                panel_y + 80,
                slider_w,
                0,
                255,
                r,
                "R",
                (220, 60, 60),
            ),
            Slider(
                panel_x + label_offset,
                panel_y + 140,
                slider_w,
                0,
                255,
                g,
                "G",
                (60, 220, 60),
            ),
            Slider(
                panel_x + label_offset,
                panel_y + 200,
                slider_w,
                0,
                255,
                b,
                "B",
                (70, 110, 230),
            ),
        ]

    # endregion

    # region 2. ГЛАВНЫЙ ЦИКЛ И ВЫХОД
    def run_game(self) -> None:
        """Запускает главный игровой цикл."""
        logger.info("Запуск игры")
        self._toggle_background_music(True)

        error_count = 0
        MAX_ERRORS = 30

        while True:
            try:
                dt = min(self.clock.tick(120) / 1000.0, 0.05)

                self._check_events()

                # Если окно потеряло фокус — ставим на паузу (только в игре)
                if not pygame.display.get_active() and self.state == GameState.PLAYING:
                    self._change_state(GameState.PAUSED)

                # Обновление в зависимости от состояния
                if self.state == GameState.PLAYING:
                    if self.respawn_timer > 0:
                        self.respawn_timer -= dt
                        if self.respawn_timer < 0:
                            self.respawn_timer = 0.0
                    else:
                        self.ship.update(dt)
                        self._update_bullets(dt)
                        self._update_aliens(dt)

                self._update_mouse()
                self.starfield.update(dt)

                self._transition()
                self._fade_in()

                self._update_screen()

                error_count = 0

            except pygame.error:
                error_count += 1
                logger.exception(f"Ошибка Pygame ({error_count}/{MAX_ERRORS})")
                if error_count >= MAX_ERRORS:
                    logger.critical("Слишком много ошибок Pygame — выход")
                    self._quit_game()
                time.sleep(0.05)

            except Exception:
                error_count += 1
                logger.exception(f"Неожиданная ошибка ({error_count}/{MAX_ERRORS})")
                if error_count >= MAX_ERRORS:
                    logger.critical("Слишком много ошибок подряд — выход")
                    self._quit_game()
                time.sleep(0.05)

    def _quit_game(self) -> None:
        try:
            self.settings.save()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Не удалось сохранить настройки при выходе: {e}")
        logger.info("Закрытие игры")
        pygame.quit()
        sys.exit()

    # endregion

    # region 3. СТЕЙТ-МАШИНА И ПЕРЕХОДЫ
    def _change_state(self, new_state: GameState):
        """Безопасно меняет состояние игры."""
        logger.debug(f"Смена состояния: {self.state.name} -> {new_state.name}")

        if self.state == GameState.PLAYING and new_state != GameState.PLAYING:
            self.ship.moving_left = False
            self.ship.moving_right = False

        self.state = new_state

    def _start_transition(self, callback=None):
        """Запускает эффект гиперпрыжка."""
        self._change_state(GameState.TRANSITION)
        self.transition_start_time = time.time()
        self._transition_callback = callback

    def _finish_transition(self):
        """Завершает переход: вызывает callback, запускает fade-in."""
        self.starfield.speed_multiplier = 1.0
        self._overlay_alpha = 255

        callback = self._transition_callback
        self._transition_callback = None
        if callback is not None:
            callback()

        self._change_state(GameState.PLAYING)

        self.fade_in = True
        self.fade_in_start_time = time.time()

    def _transition(self):
        """Анимация гиперпрыжка."""
        if self.state != GameState.TRANSITION:
            self.starfield.speed_multiplier = 1.0
            return

        elapsed = time.time() - self.transition_start_time
        progress = min(elapsed / self.TRANSITION_DURATION, 1.0)

        if progress < 0.35:
            phase = progress / 0.35
            self.starfield.speed_multiplier = 1.0 + phase * 7.0
            self._overlay_alpha = 0
        elif progress < 0.65:
            self.starfield.speed_multiplier = 8.0
            self._overlay_alpha = 0
        else:
            phase = (progress - 0.65) / 0.35
            ease = (1.0 - phase) ** 2
            self.starfield.speed_multiplier = 1.0 + ease * 7.0
            self._overlay_alpha = int(255 * phase)

        if progress >= 1.0:
            self._finish_transition()

    def _fade_in(self):
        """Fade-in игры: overlay alpha 255 → 0."""
        if self.fade_in:
            elapsed = time.time() - self.fade_in_start_time
            progress = min(elapsed / self.FADE_IN_DURATION, 1.0)
            self._overlay_alpha = int(255 * (1.0 - progress))
            if progress >= 1.0:
                self.fade_in = False
                self._overlay_alpha = 0

    def _reset_game(self):
        """Сбрасывает всё для новой игры (вызывается из TRANSITION)."""
        try:
            self.settings.initialize_dynamic_settings()
            self.score = 0
            self.ships_left = self.settings.ship_limit
            self.sb.reset()
            self.bullets.empty()
            self.aliens.empty()

            # Сброс глобальных смещений флота
            self._fleet_offset_x = 0.0
            self._fleet_offset_y = 0

            self._create_fleet()
            self.ship.center_ship()
        except Exception:
            logger.exception("Ошибка при перезапуске игры")

    def _restart_to_menu(self):
        """Возврат в главное меню."""
        self._change_state(GameState.MENU)
        self.bullets.empty()
        self.aliens.empty()
        self.sb.reset()
        self.fade_in = False
        self._overlay_alpha = 0
        self.respawn_timer = 0.0

    # endregion

    # region 4. СОБЫТИЯ И ВВОД (UI + КЛАВИАТУРА)
    def _check_events(self):
        """Обрабатывает события в зависимости от состояния."""
        sliders_active = self.state in (GameState.MENU, GameState.PAUSED)

        for event in pygame.event.get():
            if sliders_active and self._handle_slider_events(event):
                continue

            if event.type == pygame.QUIT:
                self._quit_game()
            elif event.type == pygame.KEYDOWN:
                self._check_keydown_events(event)
            elif event.type == pygame.KEYUP:
                self._check_keyup_events(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if self.state == GameState.MENU:
                    self._check_play_button(pygame.mouse.get_pos())
                elif (
                    self.state == GameState.PLAYING
                    and event.button == 1
                    and self.respawn_timer <= 0
                ):
                    self._fire_bullet()

    def _check_keydown_events(self, event):
        """Реагирует на нажатие клавиш (глобально и по состояниям)."""
        if event.key == pygame.K_ESCAPE:
            self._quit_game()
        elif event.key == pygame.K_m:
            self._toggle_background_music(not self.fon_music_active)

        if self.state == GameState.PLAYING:
            if event.key in (pygame.K_d, pygame.K_RIGHT):
                self.ship.moving_right = True
            elif event.key in (pygame.K_a, pygame.K_LEFT):
                self.ship.moving_left = True
            elif event.key == pygame.K_SPACE and self.respawn_timer <= 0:
                self._fire_bullet()
            elif event.key == pygame.K_p:
                self._change_state(GameState.PAUSED)
            elif event.key == pygame.K_r:
                self._restart_to_menu()

        elif self.state == GameState.PAUSED:
            if event.key == pygame.K_p:
                self._change_state(GameState.PLAYING)
            elif event.key == pygame.K_r:
                self._restart_to_menu()

        elif self.state == GameState.TRANSITION:
            if event.key == pygame.K_SPACE:
                if (
                    self._transition_callback is not None
                    or self.state == GameState.TRANSITION
                ):
                    self._finish_transition()
            elif event.key == pygame.K_r:
                self._restart_to_menu()

    def _check_keyup_events(self, event):
        """Отпускание клавиш."""
        if self.state == GameState.PLAYING:
            if event.key in (pygame.K_d, pygame.K_RIGHT):
                self.ship.moving_right = False
            elif event.key in (pygame.K_a, pygame.K_LEFT):
                self.ship.moving_left = False

    def _check_play_button(self, mouse_pos):
        if self.play_button.rect.collidepoint(mouse_pos):
            self._start_transition(self._reset_game)

    def _update_mouse(self):
        """Курсор виден только в меню и на паузе."""
        should_be_visible = self.state in (GameState.MENU, GameState.PAUSED)
        if should_be_visible != self._mouse_visible:
            try:
                pygame.mouse.set_visible(should_be_visible)
                if should_be_visible:
                    pygame.mouse.set_pos(
                        int(self.screen_rect.right * 0.6),
                        int(self.screen_rect.bottom * 0.5),
                    )
                self._mouse_visible = should_be_visible
            except pygame.error as e:
                logger.warning(f"Не удалось изменить видимость курсора: {e}")

    def _handle_slider_events(self, event) -> bool:
        changed = False
        for slider in self.color_sliders:
            if slider.handle_event(event):
                changed = True
        if changed:
            self._update_bg_from_sliders()
            return True
        return False

    def _update_bg_from_sliders(self):
        """Мгновенно обновляет цвет фона по значениям ползунков."""
        new_color = (
            self.color_sliders[0].value,
            self.color_sliders[1].value,
            self.color_sliders[2].value,
        )
        self.settings.set_bg_color(new_color)

    # endregion

    # region 5. АУДИО
    def _init_sounds(self):
        self.fon_music = None
        self.create_alien_music = None
        self.over_music = None
        self.fire_music = None

        if not self.audio_enabled:
            return

        try:
            self.fon_music = pygame.mixer.Sound(
                resource_path("dop_fails/music/play_menu.mp3")
            )
            self.fon_music.set_volume(0.05)
        except (FileNotFoundError, pygame.error) as e:
            logger.warning(f"Не удалось загрузить фоновую музыку: {e}")

        try:
            self.create_alien_music = pygame.mixer.Sound(
                resource_path("dop_fails/music/create_alien_music.mp3")
            )
            self.over_music = pygame.mixer.Sound(
                resource_path("dop_fails/music/game_over.mp3")
            )
            self.fire_music = pygame.mixer.Sound(
                resource_path("dop_fails/music/fire.mp3")
            )
            self.over_music.set_volume(0.5)
            self.fire_music.set_volume(0.2)
        except (FileNotFoundError, pygame.error) as e:
            logger.warning(f"Не удалось загрузить звуковые эффекты: {e}")

    def _toggle_background_music(self, active):
        self.fon_music_active = active
        if not self.audio_enabled or self.fon_music is None:
            return
        try:
            if active:
                self.fon_music.play(-1)
            else:
                self.fon_music.stop()
        except pygame.error as e:
            logger.warning(f"Ошибка при управлении фоновой музыкой: {e}")

    def _play_sound(self, sound):
        if sound is None:
            return
        try:
            sound.play()
        except pygame.error as e:
            logger.warning(f"Ошибка воспроизведения звука: {e}")

    # endregion

    # region 6. ИГРОВАЯ ЛОГИКА (ИГРОК И БОЙ)
    def _fire_bullet(self):
        if len(self.bullets) < int(self.settings.bullets_allowed):
            new_bullet = Bullet(self)
            self.bullets.add(new_bullet)
            self._play_sound(self.fire_music)

    def _update_bullets(self, dt):
        self.bullets.update(dt)
        for bullet in self.bullets.copy():
            if bullet.rect.bottom <= 0:
                self.bullets.remove(bullet)
        self._check_bullet_alien_collisions()

    def _handle_level_up(self):
        try:
            self.settings.fleet_direction = 1
            self._fleet_offset_x = 0.0
            self._fleet_offset_y = 0
            if not self._create_fleet():
                return
            self.bullets.empty()
            self.settings.increase_speed()
            self.settings.level += 1
            self._play_sound(self.create_alien_music)
            self._start_transition()
        except Exception:
            logger.exception("Ошибка при переходе на новый уровень")

    def _ship_hit(self):
        if self.ships_left > 0:
            self.ships_left -= 1
            self.bullets.empty()
            self.aliens.empty()

            self._fleet_offset_x = 0.0
            self._fleet_offset_y = 0

            self._create_fleet()
            self._play_sound(self.create_alien_music)
            self.ship.center_ship()
            self.respawn_timer = self.RESPAWN_DURATION
        else:
            self._restart_to_menu()
            self._play_sound(self.over_music)

    # endregion

    # region 7. УПРАВЛЕНИЕ ФЛОТОМ (ПРИШЕЛЬЦЫ)
    def _create_fleet(self) -> bool:
        try:
            alien = Alien(self)
            alien_width, alien_height = alien.rect.size
            current_x = alien_width
            current_y = alien_height + FLEET_TOP_OFFSET

            while current_y < (
                self.screen_rect.height - FLEET_ROWS_BELOW * alien_height
            ):
                while current_x < (self.screen_rect.width - 2 * alien_width):
                    self._create_alien(current_x, current_y)
                    current_x += (
                        alien_width + alien_width * self.settings.distance_multiplier
                    )
                current_x = alien_width
                current_y += (
                    alien_height + alien_height * self.settings.distance_multiplier
                )

            if not self.aliens:
                logger.error("Флот пуст — возврат в меню")
                self._restart_to_menu()
                return False
            return True
        except Exception:  # noqa: BLE001
            logger.exception("Ошибка при создании флота")
            return False

    def _create_alien(self, x_position, y_position):
        new_alien = Alien(self)
        new_alien.base_x = float(x_position)
        new_alien.base_y = float(y_position)
        new_alien.rect.x = int(x_position)
        new_alien.rect.y = int(y_position)
        self.aliens.add(new_alien)

    def _update_aliens(self, dt):
        """Обновляет позиции флота. Движение детерминировано через общий offset."""
        self._check_fleet_edges()

        # Двигаем единый offset флота (float, без потери точности)
        self._fleet_offset_x += (
            self.settings.alien_speed * self.settings.fleet_direction * dt
        )

        # Применяем позиции ко всем пришельцам
        self._apply_fleet_positions()

        if pygame.sprite.spritecollideany(self.ship, self.aliens):
            self._ship_hit()

        self._check_aliens_bottom()

    def _apply_fleet_positions(self):
        """Применяет глобальные смещения ко всем пришельцам.

        Строй идеально ровный: ошибка округления одна на весь флот,
        а не накапливается у каждого спрайта.
        """
        offset_x = round(self._fleet_offset_x)
        for alien in self.aliens:
            alien.set_fleet_position(offset_x, self._fleet_offset_y)

    def _check_aliens_bottom(self):
        """Проверяет, не дошли ли пришельцы до низа. По bounding box."""
        if not self.aliens:
            return
        max_bottom = max(a.rect.bottom for a in self.aliens)
        if max_bottom >= self.screen_rect.height:
            self._ship_hit()

    def _check_bullet_alien_collisions(self):
        collisions = pygame.sprite.groupcollide(self.bullets, self.aliens, True, True)
        if collisions:
            for aliens in collisions.values():
                self.score += self.settings.alien_points * len(aliens)
            self.sb.check_record()
        if not self.aliens:
            self._handle_level_up()

    def _check_fleet_edges(self):
        """Проверяет границы флота по общему bounding box.

        O(n) один раз за кадр, а не O(n) внутри вложенного цикла.
        """
        if not self.aliens:
            return

        offset_x = round(self._fleet_offset_x)
        left = min(a.base_x for a in self.aliens) + offset_x
        right = max(a.base_x + a.rect.width for a in self.aliens) + offset_x

        if self.settings.fleet_direction > 0 and right >= self.screen_rect.right:
            self._change_fleet_direction()
        elif self.settings.fleet_direction < 0 and left <= 0:
            self._change_fleet_direction()

    def _change_fleet_direction(self):
        """Опускает флот на фикс. шаг и меняет направление."""
        self._fleet_offset_y += self.settings.fleet_drop_speed
        self.settings.fleet_direction *= -1

    # endregion

    # region 8. ОТРИСОВКА (РЕНДЕРИНГ)
    def _update_screen(self):
        """Отрисовывает экран в зависимости от состояния."""
        self.screen.fill(self.settings.bg_color)
        self.starfield.draw(self.screen)

        if self.state in (GameState.PLAYING, GameState.PAUSED):
            for bullet in self.bullets.sprites():
                bullet.draw_bullet()
            self.ship.blit_me()
            self.aliens.draw(self.screen)
            self.sb.draw()

            if self.state == GameState.PAUSED:
                pause_surface = pygame.Surface(self.screen_rect.size, pygame.SRCALPHA)
                pause_surface.fill((0, 0, 0, 150))
                self.screen.blit(pause_surface, (0, 0))

                pause_text = self.font.render("Press 'p' to continue", True, TEXT_COLOR)
                pause_rect = pause_text.get_rect(center=self.screen_rect.center)
                self.screen.blit(pause_text, pause_rect)
                self._draw_color_panel()

        elif self.state == GameState.MENU:
            for key in self.text_cache:
                text_data = self.text_cache[key]
                self.screen.blit(text_data["image"], text_data["rect"])
            self.play_button.draw_button()
            self._draw_color_panel()

        self._draw_overlay()
        pygame.display.flip()

    def _draw_overlay(self):
        if self._overlay_alpha > 0:
            self._overlay_surface.set_alpha(self._overlay_alpha)
            self.screen.blit(self._overlay_surface, (0, 0))

    def _draw_color_panel(self):
        rect = self.color_panel_rect
        for i in range(10, 0, -1):
            shadow = pygame.Surface(
                (rect.width + i * 2, rect.height + i * 2), pygame.SRCALPHA
            )
            pygame.draw.rect(
                shadow, (0, 0, 0, 8), shadow.get_rect(), border_radius=20 + i
            )
            self.screen.blit(shadow, (rect.x - i, rect.y - i + 4))

        panel_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            panel_surface,
            (255, 255, 255, 25),
            panel_surface.get_rect(),
            border_radius=16,
        )
        self.screen.blit(panel_surface, rect.topleft)

        border_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            border_surface,
            (255, 255, 255, 90),
            border_surface.get_rect(),
            1,
            border_radius=16,
        )
        self.screen.blit(border_surface, rect.topleft)

        title = self.font.render("Background color", True, (255, 255, 255))
        title_rect = title.get_rect(center=(rect.centerx, rect.y + 30))
        self.screen.blit(title, title_rect)

        sep_surface = pygame.Surface((rect.width - 40, 1), pygame.SRCALPHA)
        sep_surface.fill((255, 255, 255, 60))
        self.screen.blit(sep_surface, (rect.x + 20, rect.y + 55))

        for slider in self.color_sliders:
            slider.draw(self.screen)

    # endregion


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    ai = AlienInvasion()
    ai.run_game()