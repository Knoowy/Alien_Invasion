import json
import os
from pathlib import Path
import sys


def resource_path(relative_path):
    """Получить абсолютный путь к ресурсу (работает в EXE и в исходниках)."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def app_path():
    """Возвращает путь к папке, где находится EXE (или .py)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.abspath(".")


def get_data_path():
    """
    Возвращает путь к папке для сохранения данных игры.
    - На Windows: %APPDATA%/AlienInvasion
    - На Linux/macOS: ~/.local/share/AlienInvasion
    """
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
        data_dir = os.path.join(base, 'AlienInvasion')
    else:
        base = os.path.expanduser('~/.local/share')
        data_dir = os.path.join(base, 'AlienInvasion')

    os.makedirs(data_dir, exist_ok=True)
    return data_dir

def load_config() -> dict:
    """Загружает конфигурацию игры из JSON."""
    try:
        path = Path(get_data_path()) / 'config.json'
        if path.exists():
            return json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        pass
    return {}

def save_config(config: dict) -> None:
    """Сохраняет конфигурацию игры в JSON."""
    try:
        path = Path(get_data_path()) / 'config.json'
        path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding='utf-8')
    except OSError:
        pass