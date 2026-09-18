# build.py
"""
Скрипт для сборки игры Alien Invasion в один EXE-файл.
Использует PyInstaller.
"""

import os
import shutil
import subprocess
import sys

from utils import get_data_path


def clean_build():
    """Удаляет временные папки и файлы сборки."""
    # Удаляем папку с данными игры (рекорд)
    data_dir = get_data_path()
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
        print(f"🗑️  Удалена папка с данными: {data_dir}")

    targets = ['build', 'dist', '__pycache__', 'AlienInvasion.spec']
    for target in targets:
        if os.path.exists(target):
            if os.path.isdir(target):
                shutil.rmtree(target)
            else:
                os.remove(target)
            print(f"🗑️  Удалено: {target}")


def cleanup_after_build(exe_name='AlienInvasion'):
    """Удаляет всё лишнее и переносит EXE в корень проекта."""
    print("\n🧹 Очистка временных файлов...")

    # Удаляем build/
    if os.path.exists('build'):
        shutil.rmtree('build')
        print("🗑️  Удалена папка: build")

    # Удаляем .spec
    spec_file = f'{exe_name}.spec'
    if os.path.exists(spec_file):
        os.remove(spec_file)
        print(f"🗑️  Удалён файл: {spec_file}")

    # Удаляем __pycache__
    if os.path.exists('__pycache__'):
        shutil.rmtree('__pycache__')
        print("🗑️  Удалена папка: __pycache__")

    # Определяем расширение под текущую ОС
    ext = '.exe' if sys.platform == 'win32' else ''

    # Перемещаем EXE из dist/ в корень проекта
    exe_src = os.path.join('dist', f'{exe_name}{ext}')
    exe_dst = f'{exe_name}{ext}'

    if os.path.exists(exe_src):
        # Если в корне уже есть старый EXE — удаляем
        if os.path.exists(exe_dst):
            os.remove(exe_dst)
        shutil.move(exe_src, exe_dst)
        print(f"📦 EXE перенесён в: {exe_dst}")

    # Удаляем папку dist (она уже пуста)
    if os.path.exists('dist') and not os.listdir('dist'):
        os.rmdir('dist')
        print("🗑️  Удалена папка: dist")


def build():
    """Собирает приложение с помощью PyInstaller."""
    print("🚀 Начинаем сборку Alien Invasion...")
    print("=" * 50)

    # Проверяем наличие PyInstaller
    try:
        import PyInstaller
    except ImportError:
        print("❌ PyInstaller не установлен.")
        print("👉 Установите: python -m pip install pyinstaller")
        sys.exit(1)

    # Очищаем старые сборки
    clean_build()

    # Проверяем наличие иконки
    icon_path = 'dop_fails/images/ai_ico.ico'
    if not os.path.exists(icon_path):
        print(f"⚠️  Иконка не найдена: {icon_path}")
        print("   Сборка продолжится без иконки.")
        icon_arg = []
    else:
        icon_arg = ['--icon', icon_path]

    # Проверяем наличие ресурсов
    if not os.path.exists('dop_fails'):
        print("⚠️  Папка dop_fails не найдена!")
        print("   Убедитесь, что все ресурсы на месте.")

    # Формируем команду
    cmd = [
        'pyinstaller',
        '--onefile',               # Один EXE файл
        '--windowed',              # Без консоли (GUI)
        '--name', 'AlienInvasion', # Имя приложения
        '--add-data', 'dop_fails;dop_fails',  # Копируем ресурсы
        '--hidden-import', 'pygame',          # Явные импорты
        '--hidden-import', 'pygame.mixer',
        *icon_arg,
        'alien_invasion.py'
    ]

    print("\n🔧 Команда сборки:")
    print(' '.join(cmd))
    print("\n⏳ Сборка может занять несколько минут...\n")

    # Запускаем PyInstaller
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        if result.returncode == 0:
            # Очищаем и переносим EXE
            cleanup_after_build()

            ext = '.exe' if sys.platform == 'win32' else ''
            print("\n✅ Сборка завершена успешно!")
            print(f"📁 EXE-файл: AlienInvasion{ext}")
            print("\n🎮 Запустите игру двойным кликом по файлу.")
        else:
            print("\n❌ Ошибка сборки. Проверьте вывод выше.")
            sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n⏹️  Сборка прервана пользователем.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    build()