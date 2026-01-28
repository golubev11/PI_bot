import os
import logging
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


@contextmanager
def temp_file_manager(*file_paths):
    """Контекстный менеджер для автоматического удаления временных файлов"""
    try:
        yield
    finally:
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Cleaned up temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up {file_path}: {e}")


def cleanup_old_temp_files(temp_dir: str, max_age_hours: int = 24):
    """Очистка старых временных файлов (для периодического вызова)"""
    import time
    current_time = time.time()

    for file_path in Path(temp_dir).rglob("*"):
        if file_path.is_file():
            file_age = current_time - file_path.stat().st_mtime
            if file_age > (max_age_hours * 3600):  # Конвертируем часы в секунды
                try:
                    file_path.unlink()
                    logger.info(f"Removed old temp file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove old file {file_path}: {e}")
