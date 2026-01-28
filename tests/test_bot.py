import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.bot import MusicStemsBot


@pytest.fixture(autouse=True)
def fake_token_env(monkeypatch):
    """Подставляем фиктивный токен, чтобы Bot успешно создался."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "TEST_TOKEN")


@pytest.fixture
def bot_instance():
    return MusicStemsBot()


@pytest.mark.asyncio
async def test_start_handler(bot_instance):
    """Проверяем, что /start отправляет правильный текст."""
    message = AsyncMock()
    await bot_instance.start_handler(message)

    message.answer.assert_awaited_once()
    args, kwargs = message.answer.await_args
    assert "Отправь мне аудиофайл" in (args[0] if args else kwargs.get("text", ""))


@pytest.mark.asyncio
async def test_audio_handler_success(bot_instance, tmp_path):
    """
    Успешный сценарий:
    - файл скачивается
    - AudioProcessor.separate_stems вызывается
    - отправляются все стемы и финальное сообщение
    - cleanup_temp_files вызывается
    """
    message = AsyncMock()
    message.audio.file_id = "FILE_ID"

    # Подменяем методы Bot
    bot_instance.bot.get_file = AsyncMock(return_value=MagicMock(file_path="remote/path.mp3"))

    async def fake_download(remote, local):
        # создаём пустой файл, чтобы имитировать скачивание
        open(local, "wb").close()

    bot_instance.bot.download_file = AsyncMock(side_effect=fake_download)

    # Мокаем AudioProcessor внутри audio_handler
    fake_paths = {
        "vocals": str(tmp_path / "vocals.wav"),
        "drums": str(tmp_path / "drums.wav"),
    }
    for p in fake_paths.values():
        open(p, "wb").close()

    with patch("your_package.bot.AudioProcessor") as AP:  # путь к классу в модуле с ботом
        ap_instance = AP.return_value
        ap_instance.separate_stems = AsyncMock(return_value=fake_paths)
        ap_instance.cleanup_temp_files = MagicMock()

        await bot_instance.audio_handler(message)

        # 1) сообщение про начало обработки
        message.answer.assert_any_await(
            "Обрабатываю аудио... "
            "Это может занять несколько минут."
        )

        # 2) вызовы к Telegram API
        bot_instance.bot.get_file.assert_awaited_once()
        bot_instance.bot.download_file.assert_awaited_once()

        # 3) вызов разделения на стемы
        ap_instance.separate_stems.assert_awaited_once()

        # 4) отправка аудио по количеству стемов
        # answer_audio вызывался len(fake_paths) раз
        assert message.answer_audio.await_count == len(fake_paths)

        # 5) финальное сообщение
        message.answer.assert_any_await("Готово! Все стемы отправлены.")

        # 6) очистка временных файлов
        ap_instance.cleanup_temp_files.assert_called_once()


@pytest.mark.asyncio
async def test_audio_handler_error(bot_instance):
    """
    При исключении:
    - логируется ошибка
    - пользователю отправляется сообщение об ошибке
    - cleanup_temp_files всё равно вызывается
    """
    message = AsyncMock()
    message.audio.file_id = "FILE_ID"

    bot_instance.bot.get_file = AsyncMock(side_effect=RuntimeError("download error"))

    with patch("your_package.bot.AudioProcessor") as AP:
        ap_instance = AP.return_value
        ap_instance.separate_stems = AsyncMock()
        ap_instance.cleanup_temp_files = MagicMock()

        await bot_instance.audio_handler(message)

        # Было сообщение про обработку
        message.answer.assert_any_await(
            "Обрабатываю аудио... "
            "Это может занять несколько минут."
        )
        # Было сообщение об ошибке
        message.answer.assert_any_await("Произошла ошибка при обработке аудио.")

        # cleanup_temp_files всё равно вызван
        ap_instance.cleanup_temp_files.assert_called_once()


@pytest.mark.asyncio
async def test_setup_webhook_calls_set_webhook(bot_instance):
    """Проверяем, что setup_webhook вызывает bot.set_webhook с нужным URL."""
    bot_instance.bot.set_webhook = AsyncMock()
    url = "https://example.com/webhook"

    await bot_instance.setup_webhook(url)

    bot_instance.bot.set_webhook.assert_awaited_once()
    _, kwargs = bot_instance.bot.set_webhook.await_args
    assert kwargs["url"] == url
    assert kwargs["allowed_updates"] == ["message"]


def test_create_app_returns_aiohttp_app(bot_instance):
    """Простейшая проверка, что aiohttp приложение создаётся."""
    app = bot_instance.create_app()
    # есть хотя бы маршрут health-check
    paths = {r.resource.canonical for r in app.router.routes()}
    assert "/health" in paths
