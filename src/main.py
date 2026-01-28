import asyncio
import os
import logging

from aiohttp.web_runner import AppRunner, TCPSite
from dotenv import load_dotenv
from src.bot import MusicStemsBot

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


async def main():
    """Главная функция запуска бота"""
    bot_instance = MusicStemsBot()

    # Получение переменных окружения
    use_polling = os.getenv('USE_POLLING', 'false').lower() == 'true'
    webhook_url = os.getenv('WEBHOOK_URL')

    # Определение режима работы
    if webhook_url:
        if use_polling:
            logger.warning(
                "Обнаружены переменные USE_POLLING=true и WEBHOOK_URL. "
                "Приоритет отдается webhook режиму, polling будет проигнорирован."
            )

        logger.info("Запуск бота в режиме webhook")
        await start_webhook_mode(bot_instance, webhook_url)

    elif use_polling:
        logger.info("Запуск бота в режиме polling")
        await start_polling_mode(bot_instance)

    else:
        logger.error(
            "Не указан режим работы бота. "
            "Установите USE_POLLING=true или укажите WEBHOOK_URL"
        )
        return


async def start_polling_mode(bot_instance: MusicStemsBot):
    """Запуск бота в режиме polling"""
    try:
        logger.info("Бот запущен в режиме polling. Нажмите Ctrl+C для остановки.")
        await bot_instance.start_polling()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки. Завершение работы...")
    except Exception as e:
        logger.error(f"Ошибка в режиме polling: {e}")
        raise


async def start_webhook_mode(bot_instance: MusicStemsBot, webhook_url: str):
    """Запуск бота в режиме webhook"""
    try:
        # Формирование полного URL для webhook
        full_webhook_url = f"{webhook_url}/webhook"

        # Настройка webhook
        await bot_instance.setup_webhook(full_webhook_url)
        logger.info(f"Webhook настроен на URL: {full_webhook_url}")

        # Создание приложения
        app = bot_instance.create_app()
        port = int(os.getenv('PORT', 8000))

        # Создание runner'а вместо web.run_app()
        runner = AppRunner(app)
        await runner.setup()

        site = TCPSite(runner, host="0.0.0.0", port=port)
        await site.start()

        logger.info(f"Веб-сервер запущен на порту {port}")

        # Бесконечный цикл для поддержания работы сервера
        try:
            while True:
                await asyncio.sleep(3600)  # Спим по часу
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки...")
        finally:
            await runner.cleanup()

    except Exception as e:
        logger.error(f"Ошибка в режиме webhook: {e}")
        raise


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Приложение остановлено пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
