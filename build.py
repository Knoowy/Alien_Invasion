"""Сборка Alien Invasion в один исполняемый файл через PyInstaller."""

import os
import shutil
import subprocess
import sys

from utils import get_data_path


# ──────────────────────────────────────────────────────────────────
# Константы
# ──────────────────────────────────────────────────────────────────
EXE_NAME = 'AlienInvasion'
EXE_EXT = '.exe' if sys.platform == 'win32' else ''
ICON_PATH = 'dop_fails/images/ai_ico.ico'
SPEC_FILE = f'{EXE_NAME}.spec'


# ──────────────────────────────────────────────────────────────────
# Очистка
# ──────────────────────────────────────────────────────────────────
def _safe_rmtree(path: str) -> None:
    """Удаляет папку с понятным сообщением об ошибке."""
    try:
        shutil.rmtree(path)
    except OSError as e:
        print(f"⚠️  Не удалось удалить {path}: {e}")
        print("   Возможно, файл залочен другим процессом (игра, проводник).")


def _safe_remove(path: str) -> None:
    """Удаляет файл с понятным сообщением об ошибке."""
    try:
        os.remove(path)
    except OSError as e:
        print(f"⚠️  Не удалось удалить {path}: {e}")


def clean_build() -> None:
    """Удаляет данные игры и временные артефакты сборки."""

    # 1. Данные игры
    data_dir = get_data_path()
    if os.path.exists(data_dir):
        _safe_rmtree(data_dir)
        print(f"🗑️  Удалены данные игры: {data_dir}")

    # 2. Артефакты сборки
    targets = ['build', 'dist', '__pycache__', SPEC_FILE]
    for target in targets:
        if os.path.exists(target):
            if os.path.isdir(target):
                _safe_rmtree(target)
            else:
                _safe_remove(target)
            print(f"🗑️  Удалено: {target}")


def cleanup_after_build() -> None:
    """Убирает временные файлы и переносит готовый билд в корень проекта."""
    print("\n🧹 Очистка временных файлов...")

    for target in ('build', '__pycache__'):
        if os.path.exists(target):
            _safe_rmtree(target)
            print(f"🗑️  Удалена папка: {target}")

    if os.path.exists(SPEC_FILE):
        _safe_remove(SPEC_FILE)
        print(f"🗑️  Удалён файл: {SPEC_FILE}")

    exe_src = os.path.join('dist', f'{EXE_NAME}{EXE_EXT}')
    exe_dst = f'{EXE_NAME}{EXE_EXT}'

    if os.path.exists(exe_src):
        if os.path.exists(exe_dst):
            _safe_remove(exe_dst)
        shutil.move(exe_src, exe_dst)
        print(f"📦 Готовый файл: {exe_dst}")

    # Папка dist уже пуста? — удаляем
    if os.path.exists('dist') and not os.listdir('dist'):
        _safe_rmtree('dist')
        print("🗑️  Удалена папка: dist")


# ──────────────────────────────────────────────────────────────────
# Основная сборка
# ──────────────────────────────────────────────────────────────────
def build() -> None:
    """Собирает приложение через PyInstaller."""
    # Все пути считаем от папки скрипта, а не от CWD пользователя
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print("🚀 Начинаем сборку Alien Invasion...")
    print("=" * 50)

    # Проверяем, что PyInstaller доступен в текущем Python
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("❌ PyInstaller не установлен.")
        print("👉 Установите: python -m pip install pyinstaller")
        sys.exit(1)

    # Всегда чистим данные игры + артефакты
    clean_build()

    # Иконка (только Windows)
    icon_arg = []
    if sys.platform == 'win32':
        if os.path.exists(ICON_PATH):
            icon_arg = ['--icon', ICON_PATH]
        else:
            print(f"⚠️  Иконка не найдена: {ICON_PATH} — собираю без иконки.")
    else:
        print("ℹ️  Иконка для одного файла поддерживается только на Windows.")

    if not os.path.exists('dop_fails'):
        print("⚠️  Папка dop_fails не найдена — ресурсы не попадут в сборку!")

    if not os.path.exists('alien_invasion.py'):
        print("❌ Не найден alien_invasion.py — нечего собирать.")
        sys.exit(1)

    # Разделитель для --add-data: ';' на Windows, ':' на остальных
    sep = ';' if sys.platform == 'win32' else ':'

    cmd = [
        sys.executable, '-m', 'PyInstaller',   # тот же Python, что запустил build.py
        '--onefile',
        '--windowed',
        '--name', EXE_NAME,
        '--add-data', f'dop_fails{sep}dop_fails',
        '--log-level', 'WARN',   # ← только WARNING и ERROR
        '--noconfirm', 
        *icon_arg,
        'alien_invasion.py',
        ]

    print("\n🔧 Команда сборки:")
    print(' '.join(cmd))
    print("\n⏳ Сборка может занять несколько минут...\n")

    # Подавляем приветствие pygame в подпроцессах PyInstaller
    env = os.environ.copy()
    env['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

    try:
        result = subprocess.run(cmd, env=env)
    except FileNotFoundError:
        print("\n❌ Не удалось запустить PyInstaller.")
        print(f"   Команда: {sys.executable} -m PyInstaller")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Сборка прервана пользователем.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка при запуске: {e}")
        sys.exit(1)

    if result.returncode == 0:
        cleanup_after_build()
        print("\n✅ Сборка завершена успешно!")
        print(f"📁 Готовый файл: {EXE_NAME}{EXE_EXT}")
        print("\n🎮 Запустите игру двойным кликом по файлу.")
    else:
        print(f"\n❌ Ошибка сборки (код {result.returncode}). Проверьте вывод выше.")
        print("   Папка build/ и .spec оставлены для диагностики.")
        sys.exit(result.returncode)


if __name__ == '__main__':
    build()