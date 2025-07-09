# src/gaiola/models.py
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

@dataclass
class Day:
    """
    Dataclass to represent an available day on the Gaiola booking website.
    It stores date information, the associated button element, and availability counts.
    """
    date: str
    button: any # Selenium WebElement for the date button
    day_number: int
    day_name: str
    new_disp_morning: int = 0
    prev_disp_morning: int = 0
    new_disp_noon: int = 0
    prev_disp_noon: int = 0

    def __repr__(self) -> str:
        """
        String representation for debugging and logging.
        """
        return (f"{self.date} - prev_disp_morning: {self.prev_disp_morning}, "
                f"new_disp_morning: {self.new_disp_morning}, "
                f"prev_disp_noon: {self.prev_disp_noon}, "
                f"new_disp_noon: {self.new_disp_noon}")

class Turno(Enum):
    """
    Enum to represent the booking shifts (Mattino/Pomeriggio).
    """
    MATTINO = "Mattino"
    POMERIGGIO = "Pomeriggio"

