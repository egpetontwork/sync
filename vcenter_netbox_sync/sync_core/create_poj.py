import os

def create_project_structure():
    """Создает структуру папок и файлов для проекта CORE_SYNC"""
    
    # Основные директории
    directories = [
        "core_sync",
        "core_sync/implementations",
        "core_sync/implementations/adapters",
        "core_sync/strategies",
        "core_sync/utils",
        "tests",
        "tests/unit",
        "tests/integration",
        "docs"
    ]
    
    # Создаем директории
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Создана директория: {directory}")
    
    # Создаем файлы
    files = {
        "core_sync/__init__.py": "# Package initialization\n",
        "core_sync/interfaces.py": "# Абстрактные классы и интерфейсы\n",
        "core_sync/entities.py": "# Модели данных\n",
        "core_sync/implementations/__init__.py": "# Implementations package\n",
        "core_sync/implementations/state_manager.py": "# Реализация StateManager\n",
        "core_sync/implementations/sync_engine.py": "# Реализация SyncEngine\n",
        "core_sync/implementations/adapters/__init__.py": "# Adapters package\n",
        "core_sync/implementations/adapters/base.py": "# Базовый адаптер\n",
        "core_sync/implementations/adapters/vsphere.py": "# Адаптер для vSphere\n",
        "core_sync/implementations/adapters/netbox.py": "# Адаптер для Netbox\n",
        "core_sync/strategies/__init__.py": "# Strategies package\n",
        "core_sync/strategies/base.py": "# Базовая стратегия\n",
        "core_sync/strategies/conservative.py": "# Консервативная стратегия\n",
        "core_sync/strategies/aggressive.py": "# Агрессивная стратегия\n",
        "core_sync/utils/__init__.py": "# Utils package\n",
        "core_sync/utils/logging.py": "# Утилиты логирования\n",
        "core_sync/utils/retry.py": "# Утилиты повторных попыток\n",
        "core_sync/config.py": "# Конфигурация приложения\n",
        "core_sync/prefect_flow.py": "# Prefect flow\n",
        "requirements.txt": "# Зависимости проекта\n",
        "pyproject.toml": "# Конфигурация проекта\n",
        ".env.example": "# Пример файла окружения\n",
        "README.md": "# Документация проекта\n"
    }
    
    # Создаем файлы
    for file_path, content in files.items():
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Создан файл: {file_path}")

if __name__ == "__main__":
    create_project_structure()
    print("Структура проекта успешно создана!")