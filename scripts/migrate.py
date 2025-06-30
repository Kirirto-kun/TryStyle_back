#!/usr/bin/env python3
"""
Скрипт для управления миграциями базы данных.
Использование:
    python scripts/migrate.py upgrade  - применить все миграции
    python scripts/migrate.py revision "Описание изменений"  - создать новую миграцию
    python scripts/migrate.py downgrade  - откатить последнюю миграцию
    python scripts/migrate.py current  - показать текущую версию БД
    python scripts/migrate.py history  - показать историю миграций
"""

import sys
import os
import subprocess
from pathlib import Path

# Добавляем корневую директорию проекта в Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_alembic_command(command: list):
    """Запускает команду alembic с активированным виртуальным окружением"""
    try:
        # Проверяем, есть ли виртуальное окружение
        venv_path = project_root / "venv"
        
        if venv_path.exists():
            # Определяем путь к Python в виртуальном окружении
            if os.name == 'nt':  # Windows
                python_path = venv_path / "Scripts" / "python.exe"
                alembic_path = venv_path / "Scripts" / "alembic.exe"
            else:  # Unix/Linux/macOS
                python_path = venv_path / "bin" / "python"
                alembic_path = venv_path / "bin" / "alembic"
            
            # Если alembic доступен в venv, используем его
            if alembic_path.exists():
                command[0] = str(alembic_path)
            else:
                # Иначе запускаем через python -m alembic
                command = [str(python_path), "-m"] + command
        
        # Выполняем команду
        result = subprocess.run(
            command,
            cwd=project_root,
            capture_output=False
        )
        
        return result.returncode
    except Exception as e:
        print(f"Ошибка выполнения команды: {e}")
        return 1

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    action = sys.argv[1].lower()
    
    if action == "upgrade":
        print("🔄 Применяем миграции...")
        exit_code = run_alembic_command(["alembic", "upgrade", "head"])
        if exit_code == 0:
            print("✅ Миграции успешно применены!")
        else:
            print("❌ Ошибка при применении миграций")
        sys.exit(exit_code)
    
    elif action == "revision":
        if len(sys.argv) < 3:
            print("❌ Укажите описание для миграции")
            print("Пример: python scripts/migrate.py revision 'Добавить таблицу продуктов'")
            sys.exit(1)
        
        message = sys.argv[2]
        print(f"📝 Создаём новую миграцию: {message}")
        exit_code = run_alembic_command(["alembic", "revision", "--autogenerate", "-m", message])
        if exit_code == 0:
            print("✅ Миграция создана!")
        else:
            print("❌ Ошибка при создании миграции")
        sys.exit(exit_code)
    
    elif action == "downgrade":
        print("⬇️ Откатываем последнюю миграцию...")
        exit_code = run_alembic_command(["alembic", "downgrade", "-1"])
        if exit_code == 0:
            print("✅ Миграция откачена!")
        else:
            print("❌ Ошибка при откате миграции")
        sys.exit(exit_code)
    
    elif action == "current":
        print("📍 Текущая версия базы данных:")
        run_alembic_command(["alembic", "current"])
    
    elif action == "history":
        print("📚 История миграций:")
        run_alembic_command(["alembic", "history"])
    
    else:
        print(f"❌ Неизвестная команда: {action}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main() 