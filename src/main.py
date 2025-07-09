# src/main.py
import logging
from dotenv import load_dotenv

from src.utils.config import Config
from src.gaiola.scraper import GaiolaScraper
from src.bot.telegram_bot import TelegramBot

def main():
    """
    Main entry point for the Gaiola booking bot application.
    Loads configuration, initializes the scraper and the Telegram bot, and starts the bot.
    """
    # Load environment variables from .env file
    load_dotenv()

    # Configure logging for the entire application
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
    )
    # Suppress verbose logging from httpx (used by python-telegram-bot)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logger = logging.getLogger(__name__)

    logger.info("Application starting...")

    try:
        # Load configuration from environment variables
        config = Config.load_from_env()
        logger.info("Configuration loaded successfully.")

        # Initialize the Gaiola web scraper
        # This will also initialize the Selenium WebDriver and open the booking page
        scraper = GaiolaScraper(config)
        logger.info("GaiolaScraper initialized.")

        # Initialize and run the Telegram bot
        telegram_bot = TelegramBot(config, scraper)
        logger.info("TelegramBot initialized. Starting polling...")
        telegram_bot.run()

    except ValueError as ve:
        logger.critical(f"Configuration error: {ve}. Please check your .env file.")
    except Exception as e:
        logger.critical(f"An unhandled error occurred during application startup: {e}", exc_info=True)

if __name__ == "__main__":
    main()

