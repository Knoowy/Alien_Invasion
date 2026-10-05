import json
import os
import sys
from pathlib import Path


def resource_path(relative_path: str) -> str:
    """Получить абсолютный путь к ресурсу (работает в EXE и в исходниках)."""
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def app_path() -> str:
    """Возвращает путь к папке, где находится EXE (или .py)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_data_path() -> str:
    """
    Возвращает путь к папке для сохранения данных игры.
    - На Windows: %APPDATA%/AlienInvasion
    - На Linux/macOS: ~/.local/share/AlienInvasion
    """
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        data_dir = os.path.join(base, "AlienInvasion")
    else:
        base = os.path.expanduser("~/.local/share")
        data_dir = os.path.join(base, "AlienInvasion")

    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def load_config() -> dict:
    """Загружает конфигурацию игры из JSON."""
    try:
        path = Path(get_data_path()) / "config.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def save_config(config: dict) -> None:
    """Сохраняет конфигурацию игры в JSON."""
    try:
        path = Path(get_data_path()) / "config.json"
        path.write_text(
            json.dumps(config, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass


def load_font(size: int, font_relative_path: str = "dop_fails/fonts/font.ttf"):
    """
    Загружает шрифт по относительному пути. Если файл не найден/битый —
    возвращает стандартный шрифт Pygame.

    Импорт pygame делаем локально, чтобы utils можно было использовать
    в скриптах сборки без инициализации pygame.
    """
    import pygame

    try:
        return pygame.font.Font(resource_path(font_relative_path), size)
    except (FileNotFoundError, pygame.error, OSError):
        return pygame.font.Font(None, size)


def create_placeholder_image(
    size: tuple[int, int],
    color: tuple[int, int, int] = (128, 128, 128),
    text: str = "No image",
):
    """Создаёт Surface-заглушку с текстом.

    Используется, когда ресурс-картинка не найдена.
    Импорт pygame — локальный, чтобы utils оставался лёгким.
    """
    import pygame

    width, height = size
    placeholder = pygame.Surface(size)
    placeholder.fill(color)

    font = pygame.font.Font(None, 20)
    text_surf = font.render(text, True, (255, 255, 255))
    text_rect = text_surf.get_rect(center=(width // 2, height // 2))
    placeholder.blit(text_surf, text_rect)
    return placeholder
