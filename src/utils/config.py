# src/utils/config.py
import os
import platform
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Config:
    """
    Configuration class to hold all environment variables and application settings.
    This centralizes configuration and makes it easily accessible throughout the application.
    """
    TELE_TOKEN: str
    MY_ID: str
    EMAIL: str
    TEL: str
    IS_RASPBERRY_PI: bool

    @classmethod
    def load_from_env(cls):
        """
        Loads configuration from environment variables.
        Raises ValueError if essential environment variables are not set.
        """
        tele_token = os.getenv('TELE_TOKEN')
        my_id = os.getenv("MY_ID")
        email = os.getenv("EMAIL")
        tel = os.getenv("TEL")

        if not all([tele_token, my_id, email, tel]):
            raise ValueError("Missing one or more essential environment variables: TELE_TOKEN, MY_ID, EMAIL, TEL")

        is_rpi = os.getenv('HEADLESS', 'False').lower() == 'true'
        logger.info(f"Running on Raspberry Pi: {is_rpi}")

        return cls(
            TELE_TOKEN=tele_token,
            MY_ID=my_id,
            EMAIL=email,
            TEL=tel,
            IS_RASPBERRY_PI=is_rpi
        )
