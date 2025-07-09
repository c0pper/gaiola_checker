# src/utils/helpers.py
import os
import json
import logging

logger = logging.getLogger(__name__)

# Ensure the 'bookings' directory exists
BOOKINGS_DIR = "bookings"
if not os.path.exists(BOOKINGS_DIR):
    os.makedirs(BOOKINGS_DIR)
    logger.info(f"Created directory: {BOOKINGS_DIR}")

def save_to_json(name: str, code: str):
    """
    Saves booking information (name and code) to a JSON file.
    Args:
        name (str): The name associated with the booking.
        code (str): The booking code.
    """
    data = {
        "name": name,
        "code": code
    }
    filename = f"{name.lower().replace(' ', '_')}_{code}.json"
    filepath = os.path.join(BOOKINGS_DIR, filename)

    try:
        with open(filepath, 'w') as json_file:
            json.dump(data, json_file, indent=4)
        logger.info(f"Booking saved to {filepath}")
    except IOError as e:
        logger.error(f"Error saving booking to JSON file {filepath}: {e}")

def find_code_by_name(name: str) -> str | None:
    """
    Finds a booking code by a given name from the saved JSON files.
    Args:
        name (str): The name to search for.
    Returns:
        str | None: The booking code if found, otherwise None.
    """
    filename_prefix = name.lower().replace(' ', '_') + "_"
    
    try:
        for filename in os.listdir(BOOKINGS_DIR):
            if filename.startswith(filename_prefix) and filename.endswith(".json"):
                filepath = os.path.join(BOOKINGS_DIR, filename)
                with open(filepath, 'r') as json_file:
                    data = json.load(json_file)
                    if data.get("name").lower() == name.lower(): # Case-insensitive check
                        return data.get("code")
        logger.info(f"No booking file found for name: {name}")
        return None
    except FileNotFoundError:
        logger.warning(f"Bookings directory '{BOOKINGS_DIR}' not found.")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from file {filename}: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while finding code by name: {e}")
        return None

def delete_booking_file(name: str, code: str) -> bool:
    """
    Deletes a specific booking JSON file.
    Args:
        name (str): The name associated with the booking.
        code (str): The booking code.
    Returns:
        bool: True if the file was successfully deleted, False otherwise.
    """
    filename = f"{name.lower().replace(' ', '_')}_{code}.json"
    filepath = os.path.join(BOOKINGS_DIR, filename)

    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Deleted booking file: {filepath}")
            return True
        else:
            logger.warning(f"Booking file not found for deletion: {filepath}")
            return False
    except OSError as e:
        logger.error(f"Error deleting booking file {filepath}: {e}")
        return False

