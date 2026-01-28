import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from src.audio_processor import AudioProcessor


class TestAudioProcessor:

    @pytest.fixture
    def audio_processor(self):
        """Создание экземпляра AudioProcessor для тестов"""
        return AudioProcessor()

    @pytest.fixture
    def sample_audio_file(self):
        """Создание временного аудиофайла для тестов"""
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
            # Создаем фиктивный аудиофайл (в реальном тесте можно использовать реальный)
            f.write(b'fake audio content')
            yield f.name
        # Очистка после теста
        if os.path.exists(f.name):
            os.unlink(f.name)

    def test_audio_processor_initialization(self, audio_processor):
        """Тест инициализации AudioProcessor"""
        assert audio_processor.model_name == "htdemucs"
        assert os.path.exists(audio_processor.temp_dir)
        assert isinstance(audio_processor.temp_files, list)
        assert len(audio_processor.temp_files) == 0

    @patch('demucs.separate.main')
    @patch('pathlib.Path.glob')
    @pytest.mark.asyncio
    async def test_separate_stems_success(self, mock_glob, mock_demucs,
                                          audio_processor, sample_audio_file):
        """Тест успешного разделения стемов"""
        # Настройка mock объектов
        mock_stem_files = [
            MagicMock(stem='vocals', name='vocals.mp3'),
            MagicMock(stem='drums', name='drums.mp3'),
            MagicMock(stem='bass', name='bass.mp3'),
            MagicMock(stem='other', name='other.mp3')
        ]

        for mock_file in mock_stem_files:
            mock_file.__str__ = lambda self: f"/fake/path/{self.name}"

        mock_glob.return_value = mock_stem_files
        mock_demucs.return_value = None

        # Выполнение теста
        result = await audio_processor.separate_stems(sample_audio_file)

        # Проверки
        assert isinstance(result, dict)
        assert len(result) == 4
        assert 'vocals' in result
        assert 'drums' in result
        assert 'bass' in result
        assert 'other' in result

        # Проверяем, что demucs был вызван с правильными параметрами
        mock_demucs.assert_called_once()
        call_args = mock_demucs.call_args[0][0]
        assert "--mp3" in call_args
        assert "--mp3-bitrate" in call_args
        assert "320" in call_args
        assert "-n" in call_args
        assert "htdemucs" in call_args
        assert sample_audio_file in call_args

        # Проверяем, что входной файл добавлен в список для удаления
        assert sample_audio_file in audio_processor.temp_files

    @patch('demucs.separate.main')
    @pytest.mark.asyncio
    async def test_separate_stems_demucs_error(self, mock_demucs,
                                               audio_processor, sample_audio_file):
        """Тест обработки ошибки в Demucs"""
        # Настройка mock для генерации исключения
        mock_demucs.side_effect = Exception("Demucs processing error")

        # Проверяем, что исключение поднимается
        with pytest.raises(Exception) as exc_info:
            await audio_processor.separate_stems(sample_audio_file)

        assert "Demucs processing error" in str(exc_info.value)

    @patch('os.path.exists')
    @patch('os.remove')
    @patch('shutil.rmtree')
    def test_cleanup_temp_files(self, mock_rmtree, mock_remove, mock_exists,
                                audio_processor):
        """Тест очистки временных файлов"""
        # Подготовка данных для теста
        test_files = ['/fake/path/file1.mp3', '/fake/path/file2.mp3']
        audio_processor.temp_files = test_files.copy()
        mock_exists.return_value = True

        # Выполнение очистки
        audio_processor.cleanup_temp_files()

        # Проверки
        assert len(audio_processor.temp_files) == 0
        assert mock_remove.call_count == len(test_files)
        mock_rmtree.assert_called_once_with(audio_processor.temp_dir)

    @patch('os.path.exists')
    @patch('os.remove')
    def test_cleanup_temp_files_with_missing_files(self, mock_remove, mock_exists,
                                                   audio_processor):
        """Тест очистки когда некоторые файлы уже не существуют"""
        test_files = ['/fake/path/file1.mp3', '/fake/path/file2.mp3']
        audio_processor.temp_files = test_files.copy()

        # Первый файл существует, второй - нет
        mock_exists.side_effect = [True, False]

        audio_processor.cleanup_temp_files()

        # Проверяем, что remove вызван только для существующего файла
        assert mock_remove.call_count == 1
        assert len(audio_processor.temp_files) == 0

    @patch('os.remove')
    @patch('os.path.exists')
    def test_cleanup_temp_files_remove_error(self, mock_exists, mock_remove,
                                             audio_processor):
        """Тест обработки ошибки при удалении файла"""
        test_files = ['/fake/path/file1.mp3']
        audio_processor.temp_files = test_files.copy()
        mock_exists.return_value = True
        mock_remove.side_effect = OSError("Permission denied")

        # Не должно поднимать исключение, только логировать предупреждение
        audio_processor.cleanup_temp_files()

        assert len(audio_processor.temp_files) == 0
        mock_remove.assert_called_once()

    def test_destructor_calls_cleanup(self, audio_processor):
        """Тест того, что деструктор вызывает очистку"""
        with patch.object(audio_processor, 'cleanup_temp_files') as mock_cleanup:
            # Принудительно вызываем деструктор
            audio_processor.__del__()
            mock_cleanup.assert_called_once()


# Интеграционный тест (требует реального аудиофайла)
class TestAudioProcessorIntegration:

    @pytest.mark.slow
    @pytest.mark.skipif(not os.getenv('RUN_INTEGRATION_TESTS'),
                        reason="Integration tests disabled")
    def test_real_audio_processing(self):
        """Интеграционный тест с реальным аудиофайлом"""
        # Этот тест требует реального аудиофайла и занимает много времени
        # Запускается только при установке переменной окружения RUN_INTEGRATION_TESTS=1
        pass
