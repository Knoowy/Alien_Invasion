import os
import sys
import time

# Скрываем приветствие Pygame
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"


import logging

import pygame

from alien import Alien
from bullet import Bullet
from button import Button
from game_stats import GameStats
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


class AlienInvasion:
    """Управляет игровыми ресурсами и поведением."""

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

        self.stats = GameStats(self)
        self.ship = Ship(self)
        self.bullets = pygame.sprite.Group()
        self.aliens = pygame.sprite.Group()

        # Звёздное небо
        self.starfield = StarField(
            self.screen_rect.width, self.screen_rect.height, count=200
        )

        # Создаем Scoreboard с внедрением зависимостей
        self.sb = Scoreboard(
            screen=self.screen,
            screen_rect=self.screen_rect,
            settings=self.settings,
            stats=self.stats,
            ship_factory=lambda: Ship(self),
        )
        self.play_button = Button(self, "Play")
        self._init_sounds()
        self._init_text_rendering()
        self._preload_instructions()
        self._init_color_sliders()

        self.game_active = False
        self.pause = False
        self.fon_music_active = False
        self._mouse_visible = False

        # Гиперпрыжок при старте игры
        self.transition = False
        self.transition_start_time = 0
        self.TRANSITION_DURATION = 1.0  # секунд
        self._transition_callback = None

        # Fade-in игры после гиперпрыжка
        self.fade_in = False
        self.fade_in_start_time = 0
        self.FADE_IN_DURATION = 1.0  # секунд

        # Затемнение: 0 = прозрачно, 255 = чёрный экран
        self._overlay_alpha = 0

        # Кэшированный overlay — создаётся один раз
        self._overlay_surface = pygame.Surface(self.screen_rect.size)
        self._overlay_surface.fill((0, 0, 0))

        # Таймер респавна после потери корабля (в секундах)
        self.respawn_timer = 0.0
        self.RESPAWN_DURATION = 0.5

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

                # Если окно потеряло фокус - ставим на паузу
                if not pygame.display.get_active():
                    self.pause = True

                # Обработка таймера респавна
                if self.respawn_timer > 0:
                    self.respawn_timer -= dt
                    if self.respawn_timer < 0:
                        self.respawn_timer = 0.0
                elif self.game_active and not self.pause and not self.transition:
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

    def _transition(self):
        """Переход-гиперпрыжок: разгон → пик → торможение + затемнение."""
        if not self.transition:
            self.starfield.speed_multiplier = 1.0
            return

        elapsed = time.time() - self.transition_start_time
        progress = min(elapsed / self.TRANSITION_DURATION, 1.0)

        # Фаза 1: РАЗГОН (0.0 → 0.35) — 1.0 → 8.0
        if progress < 0.35:
            phase = progress / 0.35
            self.starfield.speed_multiplier = 1.0 + phase * 7.0
            self._overlay_alpha = 0

        # Фаза 2: ПИК (0.35 → 0.65) — держим 8.0
        elif progress < 0.65:
            self.starfield.speed_multiplier = 8.0
            self._overlay_alpha = 0

        # Фаза 3: ТОРМОЖЕНИЕ + ЗАТЕМНЕНИЕ (0.65 → 1.0)
        else:
            phase = (progress - 0.65) / 0.35
            ease = (1.0 - phase) ** 2
            self.starfield.speed_multiplier = 1.0 + ease * 7.0
            self._overlay_alpha = int(255 * phase)

        # Переход завершён
        if progress >= 1.0:
            self._finish_transition()

    def _start_transition(self, callback=None):
        """Запускает эффект гиперпрыжка.

        callback — функция без аргументов, вызывается по завершении эффекта.
        Если callback is None — просто продолжается игра.
        """
        self.transition = True
        self.transition_start_time = time.time()
        self._transition_callback = callback

    def _finish_transition(self):
        """Завершает переход: сбрасывает флаги, вызывает callback, запускает fade-in."""
        self.transition = False
        self.starfield.speed_multiplier = 1.0
        self._overlay_alpha = 255

        callback = self._transition_callback
        self._transition_callback = None
        if callback is not None:
            callback()

        self.fade_in = True
        self.fade_in_start_time = time.time()

    def _fade_in(self):
        """Fade-in игры: overlay alpha 255 → 0."""
        if self.fade_in:
            elapsed = time.time() - self.fade_in_start_time
            progress = min(elapsed / self.FADE_IN_DURATION, 1.0)

            # Alpha уменьшается от 255 до 0
            self._overlay_alpha = int(255 * (1.0 - progress))

            if progress >= 1.0:
                self.fade_in = False
                self._overlay_alpha = 0

    def _draw_overlay(self):
        """Рисует затемняющий overlay, если alpha > 0."""
        if self._overlay_alpha > 0:
            self._overlay_surface.set_alpha(self._overlay_alpha)
            self.screen.blit(self._overlay_surface, (0, 0))

    def _setup_display(self):
        """Настраивает дисплей в полноэкранном или оконном режиме."""
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
                logger.info(f"Установлено разрешение: {width}x{height}")
            except (pygame.error, ValueError) as e2:
                logger.critical(f"Критическая ошибка: не удалось создать окно: {e2}")
                pygame.quit()
                sys.exit(1)

        self.screen_rect = self.screen.get_rect()

    def _set_window_icon(self):
        """Устанавливает иконку для окна."""
        icon_path = resource_path("dop_fails/images/ai_bmp.bmp")
        try:
            icon = pygame.image.load(icon_path)
            pygame.display.set_icon(icon)
        except (FileNotFoundError, pygame.error) as e:
            logger.warning(f"Не удалось загрузить иконку для окна: {e}")

    def _update_settings_for_display(self):
        """Обновляет настройки под текущее разрешение экрана."""
        self.settings.screen_width = self.screen_rect.width
        self.settings.screen_height = self.screen_rect.height

    def _init_text_rendering(self):
        """Инициализирует настройки рендеринга текста."""
        self.font = load_font(FONT_SIZE_LARGE)
        self.text_cache = {}

    def _init_sounds(self):
        """Загружает все звуковые эффекты."""
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

    def _play_sound(self, sound):
        """Безопасно воспроизводит звук.

        sound может быть None (если ресурс не загрузился) —
        в этом случае ничего не делает."""

        if sound is None:
            return
        try:
            sound.play()
        except pygame.error as e:
            logger.warning(f"Ошибка воспроизведения звука: {e}")

    def _preload_instructions(self):
        """Предварительно рендерит инструкции для производительности."""
        y_position = self.play_button.rect.y - 100
        for i, text in enumerate(INSTRUCTIONS):
            text_image = self.font.render(text, True, TEXT_COLOR)
            text_rect = text_image.get_rect()
            text_rect.centerx = int(self.screen_rect.centerx * 0.5)
            text_rect.top = y_position
            self.text_cache[i] = {
                "image": text_image,
                "rect": text_rect,
            }
            y_position += 50

    def _init_color_sliders(self):
        """Создаёт 3 ползунка RGB в правом нижнем углу экрана."""
        # Размеры панели
        panel_w = 480
        panel_h = 240
        panel_x = self.screen_rect.centerx - int(panel_w // 2)
        panel_y = self.screen_rect.bottom - panel_h - 40

        self.color_panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

        # Отступ слева — под подпись "R: 255"
        label_offset = 100
        # Правый отступ — 40
        slider_w = panel_w - label_offset - 40

        # Текущие значения RGB
        r, g, b = self.settings.bg_color

        # Создаём ползунки с вертикальным отступом 60px
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

    def _update_bg_from_sliders(self):
        """Мгновенно обновляет цвет фона по значениям ползунков."""
        new_color = (
            self.color_sliders[0].value,
            self.color_sliders[1].value,
            self.color_sliders[2].value,
        )
        self.settings.set_bg_color(new_color)

    def _handle_slider_events(self, event) -> bool:
        """Обрабатывает события ползунков. True — если событие поглощено."""
        changed = False
        for slider in self.color_sliders:
            if slider.handle_event(event):
                changed = True

        if changed:
            self._update_bg_from_sliders()
            return True
        return False

    def _draw_color_panel(self):
        """Рисует минималистичную полупрозрачную панель."""
        rect = self.color_panel_rect

        # 1. Мягкая тень
        for i in range(10, 0, -1):
            shadow = pygame.Surface(
                (rect.width + i * 2, rect.height + i * 2), pygame.SRCALPHA
            )
            pygame.draw.rect(
                shadow,
                (0, 0, 0, 8),  # очень слабая тень
                shadow.get_rect(),
                border_radius=20 + i,
            )
            self.screen.blit(shadow, (rect.x - i, rect.y - i + 4))

        # 2. Основная подложка — полупрозрачная белая
        panel_surface = pygame.Surface(rect.size, pygame.SRCALPHA)

        pygame.draw.rect(
            panel_surface,
            (255, 255, 255, 25),  # белый, почти прозрачный (25 из 255)
            panel_surface.get_rect(),
            border_radius=16,
        )

        self.screen.blit(panel_surface, rect.topleft)

        # 3. Тонкая светлая рамка
        border_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            border_surface,
            (255, 255, 255, 90),  # полупрозрачный белый
            border_surface.get_rect(),
            1,  # толщина 1 пиксель
            border_radius=16,
        )
        self.screen.blit(border_surface, rect.topleft)

        # 4. Заголовок (светлый, хорошо читается на тёмном фоне)
        title = self.font.render("Background color", True, (255, 255, 255))
        title_rect = title.get_rect(center=(rect.centerx, rect.y + 30))
        self.screen.blit(title, title_rect)

        sep_surface = pygame.Surface((rect.width - 40, 1), pygame.SRCALPHA)
        sep_surface.fill((255, 255, 255, 60))
        self.screen.blit(sep_surface, (rect.x + 20, rect.y + 55))

        # 6. Ползунки
        for slider in self.color_sliders:
            slider.draw(self.screen)

    def _check_events(self):
        """Обрабатывает нажатия клавиш и события мыши."""
        # Ползунки активны только в меню или на паузе
        sliders_active = (not self.game_active) or self.pause

        for event in pygame.event.get():
            # Сначала — события ползунков (если активны)
            if sliders_active and self._handle_slider_events(event):
                continue

            if event.type == pygame.QUIT:
                logger.info("Закрытие игры")
                self._quit_game()
            elif event.type == pygame.KEYDOWN:
                self._check_keydown_events(event)
            elif event.type == pygame.KEYUP:
                self._check_keyup_events(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                self._check_play_button(mouse_pos)
                # Стрельба только при активной игре и не на паузе
                if (
                    event.button == 1
                    and self.game_active
                    and not self.pause
                    and self.respawn_timer <= 0
                ):
                    self._fire_bullet()

    def _quit_game(self) -> None:
        """Корректно завершает игру и сохраняет настройки."""
        try:
            self.settings.save()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Не удалось сохранить настройки при выходе: {e}")
        pygame.quit()
        sys.exit()

    def _toggle_background_music(self, active):
        """Включает/выключает фоновую музыку."""
        self.fon_music_active = active
        if not self.audio_enabled:
            return
        if self.fon_music is not None:
            try:
                if active:
                    self.fon_music.play(-1)
                else:
                    self.fon_music.stop()
            except pygame.error as e:
                logger.warning(f"Ошибка при управлении фоновой музыкой: {e}")

    def _check_play_button(self, mouse_pos):
        """Запускает новую игру при клике на кнопку Play."""
        button_clicked = self.play_button.rect.collidepoint(mouse_pos)
        if button_clicked and not self.game_active and not self.transition:
            self._start_transition(self._reset_game)

    def _reset_game(self):
        """Сбрасывает все настройки и статистику для новой игры."""
        try:
            self.settings.initialize_dynamic_settings()
            self.stats.reset_stats()
            self.sb.reset()

            self.game_active = True
            self.pause = False
            self.bullets.empty()
            self.aliens.empty()

            self._create_fleet()
            self.ship.center_ship()

        except Exception:
            logger.exception("Ошибка при перезапуске игры")

    def _check_keydown_events(self, event):
        """Реагирует на нажатие клавиш."""
        if event.key == pygame.K_ESCAPE:
            logger.info("Закрытие игры")
            self._quit_game()
        elif event.key in (pygame.K_d, pygame.K_RIGHT):
            if not self.pause:
                self.ship.moving_right = True
        elif event.key in (pygame.K_a, pygame.K_LEFT):
            if not self.pause:
                self.ship.moving_left = True

        # ПРОПУСК ГИПЕРПРЫЖКА ПО ПРОБЕЛУ
        elif event.key == pygame.K_SPACE and self.transition:
            self._finish_transition()

        elif event.key == pygame.K_SPACE and self.respawn_timer <= 0:
            if self.game_active and not self.pause:
                self._fire_bullet()
        elif event.key == pygame.K_m:
            self._toggle_background_music(not self.fon_music_active)
        elif event.key == pygame.K_r and not self.transition:
            self._restart_game()
        elif event.key == pygame.K_p and self.game_active:
            self.pause = not self.pause

    def _restart_game(self):
        """Перезапускает игру (возврат в меню)."""
        self.game_active = False
        self.bullets.empty()
        self.aliens.empty()
        self.sb.reset()

        # Сбрасываем затемнение, если оно было
        self.fade_in = False
        self._overlay_alpha = 0

        self.respawn_timer = 0.0
        self.pause = False

        # Сбрасываем незавершённый переход (если игрок нажал R во время гиперпрыжка)
        self.transition = False
        self._transition_callback = None

    def _update_mouse(self):
        """Управляет видимостью курсора.
        Курсор появляется в одной и той же точке — по центру справа."""

        should_be_visible = (not self.game_active and not self.transition) or self.pause

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

    def _check_keyup_events(self, event):
        """Реагирует на отпускание клавиш."""
        if event.key in (pygame.K_d, pygame.K_RIGHT):
            self.ship.moving_right = False
        elif event.key in (pygame.K_a, pygame.K_LEFT):
            self.ship.moving_left = False

    def _fire_bullet(self):
        """Создает новую пулю и добавляет ее в группу."""
        if len(self.bullets) < int(self.settings.bullets_allowed):
            new_bullet = Bullet(self)
            self.bullets.add(new_bullet)
            self._play_sound(self.fire_music)

    def _update_bullets(self, dt):
        """Обновляет позиции пуль и удаляет старые."""
        self.bullets.update(dt)

        for bullet in self.bullets.copy():
            if bullet.rect.bottom <= 0:
                self.bullets.remove(bullet)

        self._check_bullet_alien_collisions()

    def _update_aliens(self, dt):
        """Обновляет позиции флота пришельцев."""
        self._check_fleet_edges()
        self.aliens.update(dt)

        if pygame.sprite.spritecollideany(self.ship, self.aliens):
            self._ship_hit()

        self._check_aliens_bottom()

    def _check_bullet_alien_collisions(self):
        """Обрабатывает столкновения пуль с пришельцами."""
        collisions = pygame.sprite.groupcollide(self.bullets, self.aliens, True, True)

        if collisions:
            for aliens in collisions.values():
                self.stats.score += self.settings.alien_points * len(aliens)
            self.sb.check_record()

        if not self.aliens:
            self._handle_level_up()

    def _handle_level_up(self):
        """Обрабатывает переход на следующий уровень."""
        try:
            self.settings.fleet_direction = 1
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
        """Обрабатывает попадание по кораблю."""
        if self.stats.ships_left > 0:
            self.stats.ships_left -= 1

            self.bullets.empty()
            self.aliens.empty()

            self._create_fleet()
            self._play_sound(self.create_alien_music)

            self.ship.center_ship()
            self.respawn_timer = self.RESPAWN_DURATION

        else:
            self._restart_game()
            self._play_sound(self.over_music)

    def _check_aliens_bottom(self):
        """Проверяет, достигли ли пришельцы нижней границы экрана."""
        for alien in self.aliens.sprites():
            if alien.rect.bottom >= self.screen_rect.height:
                self._ship_hit()
                break

    def _create_fleet(self) -> bool:
        """Создает флот пришельцев."""
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

            # Защита: если флот не создался — не зацикливаем level-up
            if not self.aliens:
                logger.error("Флот пуст — возврат в меню")
                self._restart_game()
                return False
            return True

        except Exception:  # noqa: BLE001 — защита от любых сбоев
            logger.error("Ошибка при создании флота")
            return False

    def _create_alien(self, x_position, y_position):
        """Создает одного пришельца и размещает его во флоте."""
        new_alien = Alien(self)
        new_alien.x = float(x_position)
        new_alien.y = float(y_position)
        new_alien.rect.x = int(x_position)
        new_alien.rect.y = int(y_position)
        self.aliens.add(new_alien)

    def _check_fleet_edges(self):
        """Реагирует, если пришельцы достигли края экрана."""
        for alien in self.aliens.sprites():
            if alien.check_edges():
                self._change_fleet_direction()
                break

    def _change_fleet_direction(self):
        """Опускает флот и меняет направление движения."""
        for alien in self.aliens.sprites():
            alien.drop()
        self.settings.fleet_direction *= -1

    def _update_screen(self):
        """Обновляет изображения на экране."""
        # Фон — актуальным цветом (меняется моментально)
        self.screen.fill(self.settings.bg_color)

        # Звёзды — поверх фона, под остальными элементами
        self.starfield.draw(self.screen)

        if self.game_active and not self.transition:

            # Отрисовка игрового поля — всегда
            for bullet in self.bullets.sprites():
                bullet.draw_bullet()
            self.ship.blit_me()
            self.aliens.draw(self.screen)
            self.sb.draw()

            if self.pause:
                # Полупрозрачный оверлей + текст
                pause_surface = pygame.Surface(self.screen_rect.size, pygame.SRCALPHA)
                pause_surface.fill((0, 0, 0, 150))
                self.screen.blit(pause_surface, (0, 0))

                pause_text = self.font.render("Press 'p' to continue", True, TEXT_COLOR)
                pause_rect = pause_text.get_rect()
                pause_rect.center = self.screen_rect.center
                self.screen.blit(pause_text, pause_rect)

                # Ползунки на паузе
                self._draw_color_panel()

        if not self.game_active and not self.transition:
            for key in self.text_cache:
                text_data = self.text_cache[key]
                self.screen.blit(text_data["image"], text_data["rect"])
            self.play_button.draw_button()

            # Ползунки в меню
            self._draw_color_panel()

        self._draw_overlay()
        pygame.display.flip()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    ai = AlienInvasion()
    ai.run_game()
