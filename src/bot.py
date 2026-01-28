import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from dotenv import load_dotenv
from .audio_processor import AudioProcessor

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MusicStemsBot:
    def __init__(self):
        self.bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
        self.dp = Dispatcher()
        self.audio_processor = AudioProcessor()
        self._setup_handlers()

    def _setup_handlers(self):
        self.dp.message.register(self.start_handler, Command("start"))
        self.dp.message.register(self.audio_handler, F.audio)

    async def start_handler(self, message: types.Message):
        await message.answer(
            "Привет! Отправь мне аудиофайл, и я разделю "
            "его на стемы (вокал, барабаны, бас, остальное)"
        )

    async def audio_handler(self, message: types.Message):
        audio_processor = None
        try:
            await message.answer(
                "Обрабатываю аудио... "
                "Это может занять несколько минут."
            )

            audio_processor = AudioProcessor()

            # Скачивание файла
            file_info = await self.bot.get_file(message.audio.file_id)
            input_path = f"temp_{message.audio.file_id}.mp3"
            await self.bot.download_file(file_info.file_path, input_path)

            # Обработка через Demucs
            stems_paths = await audio_processor.separate_stems(input_path)

            # Отправка результатов
            for stem_name, stem_path in stems_paths.items():
                audio_file = types.FSInputFile(stem_path, filename=f"{stem_name}.wav")
                await message.answer_audio(audio_file)

            await message.answer("Готово! Все стемы отправлены.")

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            await message.answer("Произошла ошибка при обработке аудио.")

        finally:
            # Гарантированная очистка временных файлов
            if audio_processor:
                audio_processor.cleanup_temp_files()

    async def start_polling(self):
        await self.dp.start_polling(self.bot)

    async def setup_webhook(self, webhook_url: str):
        """Настройка webhook"""
        await self.bot.set_webhook(
            url=webhook_url,
            allowed_updates=["message"]
        )

    def create_app(self):
        """Создание aiohttp приложения"""
        app = web.Application()

        # Настройка webhook handler
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=self.dp,
            bot=self.bot
        )
        webhook_requests_handler.register(app, path="/webhook")

        # Health check endpoint
        async def health_check(request):
            return web.json_response({"status": "ok"}, status=200)

        app.router.add_get("/health", health_check)

        # Настройка приложения
        setup_application(app, self.dp, bot=self.bot)

        return app
