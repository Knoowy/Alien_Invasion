import sys
import os
from time import sleep

# Скрываем приветствие Pygame
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"


import pygame
import pygame.font
import logging

from settings import Settings
from game_stats import GameStats
from scoreboard import Scoreboard
from button import Button
from ship import Ship
from bullet import Bullet
from alien import Alien
from utils import resource_path


class AlienInvasion:
    """Управляет игровыми ресурсами и поведением."""

    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        logging.basicConfig(level=logging.INFO)
        logging.info("Инициализация игры")

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

        # Создаем Scoreboard с внедрением зависимостей
        self.sb = Scoreboard(
            screen=self.screen,
            screen_rect=self.screen_rect,
            settings=self.settings,
            stats=self.stats,
            ship_factory=lambda: Ship(self)
        )
        self.play_button = Button(self, "Play")
        self._init_sounds()
        self._init_text_rendering()
        self._preload_instructions()

        self.game_active = False
        self.pause = False
        self.fon_music_active = False

    def run_game(self):
        """Запускает главный игровой цикл."""
        logging.info("Запуск игры")
        self._toggle_background_music(True)

        while True:
            try:
                self._check_events()

                # Если окно потеряло фокус - ставим на паузу
                if not pygame.display.get_active():
                    self.pause = True

                if self.game_active and not self.pause:
                    self.ship.update()
                    self._update_bullets()
                    self._update_aliens()

                self._update_screen()
                self.clock.tick(240)
            except pygame.error as e:
                logging.error(f"Ошибка Pygame: {e}")
                continue
            except Exception as e:
                logging.error(f"Неожиданная ошибка: {e}")
                continue

    def _setup_display(self):
        """Настраивает дисплей в полноэкранном или оконном режиме."""
        try:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        except pygame.error as e:
            logging.warning(f"Не удалось установить полноэкранный режим: {e}")

            try:
                display_info = pygame.display.Info()
                width, height = display_info.current_w, display_info.current_h

                if width == 0 or height == 0:
                    raise ValueError("Не удалось получить информацию о дисплее")

                self.screen = pygame.display.set_mode((width, height))
                logging.info(f"Установлено разрешение: {width}x{height}")
            except (pygame.error, ValueError) as e2:
                logging.critical(f"Критическая ошибка: не удалось создать окно: {e2}")
                pygame.quit()
                sys.exit(1)

        self.screen_rect = self.screen.get_rect()

    def _set_window_icon(self):
        """Устанавливает иконку для окна."""
        icon_path = resource_path('dop_fails/images/ai_bmp.bmp')
        try:
            icon = pygame.image.load(icon_path)
            pygame.display.set_icon(icon)
        except (FileNotFoundError, pygame.error) as e:
            logging.warning(f"Не удалось загрузить иконку для окна: {e}")

    def _update_settings_for_display(self):
        """Обновляет настройки под текущее разрешение экрана."""
        self.settings.screen_width = self.screen_rect.width
        self.settings.screen_height = self.screen_rect.height

    def _init_text_rendering(self):
        """Инициализирует настройки рендеринга текста."""
        self.font = pygame.font.SysFont(None, 48)
        self.text_cache = {}
        self.button_color = (10, 10, 70)

    def _init_sounds(self):
        """Загружает все звуковые эффекты."""
        self.fon_music = None
        self.create_alien_music = None
        self.over_music = None
        self.fire_music = None

        try:
            self.fon_music = pygame.mixer.Sound(resource_path("dop_fails/music/play_menu.mp3"))
            self.fon_music.set_volume(0.05)
        except (FileNotFoundError, pygame.error) as e:
            logging.warning(f"Не удалось загрузить фоновую музыку: {e}")

        try:
            self.create_alien_music = pygame.mixer.Sound(resource_path("dop_fails/music/create_alien_music.mp3"))
            self.over_music = pygame.mixer.Sound(resource_path("dop_fails/music/game_over.mp3"))
            self.fire_music = pygame.mixer.Sound(resource_path("dop_fails/music/fire.mp3"))
            self.over_music.set_volume(0.5)
            self.fire_music.set_volume(0.2)
        except (FileNotFoundError, pygame.error) as e:
            logging.warning(f"Не удалось загрузить звуковые эффекты: {e}")

    def _preload_instructions(self):
        """Предварительно рендерит инструкции для производительности."""
        instructions = {
            'ad': "A / D or arrows - left / right",
            'fire': "Space or Lbm - fire",
            'pause': "P - pause",
            'escape': "Escape - quit",
            'music': "M - music",
            'restart': "R - restart"
        }

        y_position = self.play_button.rect.y - 100
        for key, text in instructions.items():
            text_image = self.font.render(text, True, self.sb.TEXT_COLOR, self.button_color)
            text_rect = text_image.get_rect()
            text_rect.centerx = int(self.screen_rect.centerx * 0.5)
            text_rect.top = y_position
            self.text_cache[key] = {
                'image': text_image,
                'rect': text_rect
            }
            y_position += 50

    def _check_events(self):
        """Обрабатывает нажатия клавиш и события мыши."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                logging.info("Закрытие игры")
                self._quit_game()
            elif event.type == pygame.KEYDOWN:
                self._check_keydown_events(event)
            elif event.type == pygame.KEYUP:
                self._check_keyup_events(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                self._check_play_button(mouse_pos)
                # Стрельба только при активной игре и не на паузе
                if event.button == 1 and self.game_active and not self.pause:
                    self._fire_bullet()

    @staticmethod
    def _quit_game():
        """Корректно завершает игру."""
        pygame.quit()
        sys.exit()

    def _toggle_background_music(self, active):
        """Включает/выключает фоновую музыку."""
        self.fon_music_active = active
        if self.fon_music is not None:
            try:
                if active:
                    self.fon_music.play(-1)
                else:
                    self.fon_music.stop()
            except pygame.error as e:
                logging.warning(f"Ошибка при управлении фоновой музыкой: {e}")

    def _check_play_button(self, mouse_pos):
        """Запускает новую игру при клике на кнопку Play."""
        button_clicked = self.play_button.rect.collidepoint(mouse_pos)
        if button_clicked and not self.game_active:
            self._reset_game()

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

            try:
                pygame.mouse.set_visible(False)
            except pygame.error as e:
                logging.warning(f"Не удалось скрыть курсор: {e}")
        except Exception as e:
            logging.error(f"Ошибка при перезапуске игры: {e}")

    def _check_keydown_events(self, event):
        """Реагирует на нажатие клавиш."""
        if event.key == pygame.K_ESCAPE:
            logging.info("Закрытие игры")
            self._quit_game()
        elif event.key in (pygame.K_d, pygame.K_RIGHT):
            if not self.pause:
                self.ship.moving_right = True
        elif event.key in (pygame.K_a, pygame.K_LEFT):
            if not self.pause:
                self.ship.moving_left = True
        elif event.key == pygame.K_SPACE:
            if self.game_active and not self.pause:
                self._fire_bullet()
        elif event.key == pygame.K_m:
            self._toggle_background_music(not self.fon_music_active)
        elif event.key == pygame.K_r:
            self._restart_game()
        elif event.key == pygame.K_p and self.game_active:
            self.pause = not self.pause

    def _restart_game(self):
        """Перезапускает игру (возврат в меню)."""
        self.game_active = False
        self.bullets.empty()
        self.aliens.empty()
        try:
            pygame.mouse.set_visible(True)
            pygame.mouse.set_pos(
                int(self.screen_rect.right * 0.6),
                int(self.screen_rect.bottom * 0.5)
            )
        except pygame.error:
            pass

        self.sb.reset()

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
            if self.fire_music is not None:
                try:
                    self.fire_music.play()
                except pygame.error as e:
                    logging.warning(f"Ошибка при воспроизведении звука выстрела: {e}")

    def _update_bullets(self):
        """Обновляет позиции пуль и удаляет старые."""
        self.bullets.update()

        for bullet in self.bullets.copy():
            if bullet.rect.bottom <= 0:
                self.bullets.remove(bullet)

        self._check_bullet_alien_collisions()

    def _check_bullet_alien_collisions(self):
        """Обрабатывает столкновения пуль с пришельцами."""
        collisions = pygame.sprite.groupcollide(
            self.bullets, self.aliens, True, True
        )

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
            self._create_fleet()
            self.bullets.empty()
            self.settings.increase_speed()
            self.settings.level += 1

            if self.create_alien_music is not None:
                try:
                    self.create_alien_music.play()
                except pygame.error as e:
                    logging.warning(f"Ошибка при воспроизведении звука: {e}")
        except Exception as e:
            logging.error(f"Ошибка при переходе на новый уровень: {e}")

    def _ship_hit(self):
        """Обрабатывает попадание по кораблю."""
        if self.stats.ships_left > 0:
            self.stats.ships_left -= 1

            self.bullets.empty()
            self.aliens.empty()

            self._create_fleet()
            if self.create_alien_music is not None:
                try:
                    self.create_alien_music.play()
                except pygame.error as e:
                    logging.warning(f"Ошибка при воспроизведении звука: {e}")

            self.ship.center_ship()
            sleep(0.5)
        else:
            self._restart_game()
            if self.over_music is not None:
                try:
                    self.over_music.play()
                except pygame.error as e:
                    logging.warning(f"Ошибка при воспроизведении звука: {e}")

    def _update_aliens(self):
        """Обновляет позиции флота пришельцев."""
        self._check_fleet_edges()
        self.aliens.update()

        if pygame.sprite.spritecollideany(self.ship, self.aliens):
            self._ship_hit()

        self._check_aliens_bottom()

    def _check_aliens_bottom(self):
        """Проверяет, достигли ли пришельцы нижней границы экрана."""
        for alien in self.aliens.sprites():
            if alien.rect.bottom >= self.screen_rect.height:
                self._ship_hit()
                break

    def _create_fleet(self):
        """Создает флот пришельцев."""
        try:
            alien = Alien(self)
            alien_width, alien_height = alien.rect.size

            current_x = alien_width
            current_y = alien_height + self.sb.FLEET_TOP_OFFSET

            rows_below = 6

            while current_y < (self.screen_rect.height - rows_below * alien_height):
                while current_x < (self.screen_rect.width - 2 * alien_width):
                    self._create_alien(current_x, current_y)
                    current_x += alien_width + alien_width * self.settings.distance_multiplier

                current_x = alien_width
                current_y += alien_height + alien_height * self.settings.distance_multiplier
        except Exception as e:
            logging.error(f"Ошибка при создании флота: {e}")

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
        self.screen.fill(self.settings.bg_color)

        if self.game_active:
            if not self.pause:
                for bullet in self.bullets.sprites():
                    bullet.draw_bullet()
                self.ship.blit_me()
                self.aliens.draw(self.screen)

            self.sb.draw()

            if self.pause:
                pause_text = self.sb.font.render(
                    "Press 'p' to continue",
                    True,
                    self.sb.TEXT_COLOR,
                    self.settings.bg_color
                )
                pause_rect = pause_text.get_rect()
                pause_rect.center = self.screen_rect.center
                self.screen.blit(pause_text, pause_rect)

        if not self.game_active:
            for key in self.text_cache:
                text_data = self.text_cache[key]
                self.screen.blit(text_data['image'], text_data['rect'])
            self.play_button.draw_button()

        pygame.display.flip()


if __name__ == '__main__':
    ai = AlienInvasion()
    ai.run_game()