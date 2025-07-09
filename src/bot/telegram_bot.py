# src/bot/telegram_bot.py
import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from src.utils.config import Config
from src.gaiola.scraper import GaiolaScraper
from src.bot import handlers # Import handlers module

logger = logging.getLogger(__name__)

class TelegramBot:
    """
    Encapsulates the Telegram bot's setup and lifecycle.
    Manages the Application, handlers, and interaction with the GaiolaScraper.
    """
    def __init__(self, config: Config, scraper: GaiolaScraper):
        """
        Initializes the TelegramBot with configuration and a GaiolaScraper instance.
        Args:
            config (Config): The application configuration object.
            scraper (GaiolaScraper): An instance of the GaiolaScraper to interact with.
        """
        self.config = config
        self.scraper = scraper
        self.application = Application.builder().token(self.config.TELE_TOKEN).build()
        self._add_handlers()

    def _add_handlers(self):
        """
        Adds all command and callback query handlers to the Telegram Application.
        The scraper and config objects are stored in bot_data for handlers to access.
        """
        self.application.bot_data['scraper'] = self.scraper
        self.application.bot_data['config'] = self.config

        # Command Handlers
        self.application.add_handler(CommandHandler("start", handlers.start))
        self.application.add_handler(CommandHandler("showdates", handlers.show_dates))
        self.application.add_handler(CommandHandler("deletejobs", handlers.delete_jobs))
        self.application.add_handler(CommandHandler("showcurrentjobs", handlers.show_current_jobs))
        self.application.add_handler(CommandHandler("deletebooking", handlers.delete_booking))

        # Callback Query Handlers
        self.application.add_handler(CallbackQueryHandler(handlers.select_person, pattern="^select_person_"))
        self.application.add_handler(CallbackQueryHandler(handlers.select_shift, pattern="^select_shift_"))
        self.application.add_handler(CallbackQueryHandler(handlers.select_date, pattern="^select_date_"))
        self.application.add_handler(CallbackQueryHandler(handlers.select_person_to_delete, pattern="^select_person_to_delete_"))
        
        logger.info("All Telegram handlers added.")

    def run(self) -> None:
        """
        Starts the Telegram bot polling for updates.
        """
        logger.info("Telegram bot is starting polling...")
        self.application.run_polling()

