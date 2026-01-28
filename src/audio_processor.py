import os
import tempfile
import shutil
import logging
from pathlib import Path
import demucs.separate

logger = logging.getLogger(__name__)


class AudioProcessor:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.model_name = "htdemucs"  # Быстрая модель
        self.temp_files = []  # Список для отслеживания временных файлов

    async def separate_stems(self, input_path: str) -> dict:
        """Разделяет аудио на стемы"""
        try:
            # Добавляем входной файл в список для удаления
            self.temp_files.append(input_path)

            output_dir = Path(self.temp_dir) / "separated"

            # Запуск Demucs
            demucs.separate.main([
                "--mp3",
                "--mp3-bitrate", "320",
                "-n", self.model_name,
                "-o", str(output_dir),
                input_path
            ])

            # Поиск созданных файлов
            stems_dir = output_dir / self.model_name / Path(input_path).stem
            stems = {}

            for stem_file in stems_dir.glob("*.mp3"):
                stem_name = stem_file.stem
                stems[stem_name] = str(stem_file)
                # Добавляем созданные стемы в список для удаления
                self.temp_files.append(str(stem_file))

            return stems

        except Exception as e:
            logger.error(f"Error in separate_stems: {e}")
            # В случае ошибки также очищаем файлы
            self.cleanup_temp_files()
            raise

    def cleanup_temp_files(self):
        """Очистка всех временных файлов"""
        # Удаляем отдельные файлы
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Removed temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to remove file {file_path}: {e}")

        # Очищаем список
        self.temp_files.clear()

        # Удаляем временную директорию
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.debug(f"Removed temp directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to remove temp directory {self.temp_dir}: {e}")

    def __del__(self):
        """Деструктор для гарантированной очистки"""
        self.cleanup_temp_files()
