# src/gaiola/scraper.py
import logging
from datetime import datetime, timedelta, date
import os
import random
from time import sleep

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from telegram.ext import ContextTypes

from src.gaiola.models import Day, Turno
from src.utils.config import Config
from src.data.people_data import Person # Import Person for type hinting

logger = logging.getLogger(__name__)

class GaiolaScraper:
    """
    Manages all interactions with the Gaiola booking website using Selenium.
    Encapsulates WebDriver setup, navigation, data scraping, and booking logic.
    """
    def __init__(self, config: Config):
        """
        Initializes the GaiolaScraper with configuration and sets up the WebDriver.
        Args:
            config (Config): The application configuration object.
        """
        self.config = config
        self.custom_user_agent = os.getenv('CUSTOM_USER_AGENT', 'Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0')
        self.driver = self._get_driver()
        self.last_iteration_day = None
        self.days: list[Day] = []
        self.open_bookings_page()
        # Initial population of days list
        while not self.days:
            logger.info("Initial creation of days list...")
            sleep(1) # Give page some time to load
            self.days = self.get_days_list()
        logger.info(f"Initial relevant possible days list: {[d.date for d in self.days]}")

    def _get_driver(self):
        """
        Initializes and returns the Selenium WebDriver based on the platform.
        Uses headless mode for Raspberry Pi.
        """
        options = Options()
        if self.config.IS_RASPBERRY_PI:
            options.headless = True  # Run in headless mode for RPi

        prefs = {
            # Disable automation indicators
            "dom.webdriver.enabled": False,
            "useAutomationExtension": False,
            
            # Disable navigator.webdriver property
            "dom.webdriver.enabled": False,
            
            # Disable images and CSS for faster loading (optional)
            # "permissions.default.image": 2,
            # "permissions.default.stylesheet": 2,
            
            # Disable notifications
            "dom.push.enabled": False,
            "dom.push.userAgentID": "",
            
            # Disable geolocation
            "geo.enabled": False,
            
            # Disable WebRTC
            "media.peerconnection.enabled": False,
            
            # Set language
            "intl.accept_languages": "en-US,en;q=0.9",
            
            # Disable automation flags
            "marionette": False,
            "dom.disable_beforeunload": True,
        }
    
        # Apply preferences
        for key, value in prefs.items():
            try:
                options.set_preference(key, value)
            except Exception as e:
                logger.warning(f"Could not set preference {key}: {e}")

        # Set custom User-Agent
        options.set_preference("general.useragent.override", self.custom_user_agent)
        logger.info(f"Setting User-Agent to: {self.custom_user_agent}")
        
        if self.config.IS_RASPBERRY_PI:
            selenium_host = os.getenv('SELENIUM_REMOTE_HOST', 'localhost')
            selenium_url = f"http://{selenium_host}:4444"

            driver = webdriver.Remote(
                command_executor=selenium_url,
                options=options
            )
        else:
            service = Service(executable_path='/usr/local/bin/geckodriver') if self.config.IS_RASPBERRY_PI else None
            driver = webdriver.Firefox(options=options, service=service)
        
        # Execute JavaScript to remove webdriver property
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Add some randomness to viewport size
        if not self.config.IS_RASPBERRY_PI:
            width = random.randint(1200, 1920)
            height = random.randint(800, 1080)
            driver.set_window_size(width, height)
        
        return driver


    def human_like_delay(self, min_delay=0.5, max_delay=2.0):
        """Generate human-like random delays"""
        delay = random.uniform(min_delay, max_delay)
        sleep(delay)

    def human_like_scroll(self, element=None):
        """Simulate human-like scrolling"""
        if element:
            # Scroll to element with random offset
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                element
            )
        else:
            # Random scroll
            scroll_amount = random.randint(100, 500)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        
        self.human_like_delay(0.5, 1.5)

    def human_like_mouse_movement(self, element):
        """Simulate human-like mouse movement to element"""
        actions = ActionChains(self.driver)
        
        # Move to a random point near the element first
        actions.move_to_element_with_offset(element, 
                                        random.randint(-10, 10), 
                                        random.randint(-10, 10))
        actions.perform()
        self.human_like_delay(0.1, 0.3)
        
        # Then move to the actual element
        actions.move_to_element(element)
        actions.perform()
        self.human_like_delay(0.2, 0.5)

    def wait_for_element(self, by, value, timeout=10):
        """Wait for element with timeout"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            logger.warning(f"Element not found within {timeout} seconds: {value}")
            return None

    def safe_click(self, element, use_js=False):
        """Safely click an element with human-like behavior"""
        try:
            # Scroll to element
            self.human_like_scroll(element)
            
            # Wait a bit
            self.human_like_delay(0.5, 1.0)
            
            # Move mouse to element
            self.human_like_mouse_movement(element)
            
            # Wait for element to be clickable
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(element))
            
            if use_js:
                # Use JavaScript click as fallback
                self.driver.execute_script("arguments[0].click();", element)
            else:
                # Try normal click first
                element.click()
            
            # Wait after click
            self.human_like_delay(1.0, 2.0)
            return True
            
        except Exception as e:
            logger.error(f"Error clicking element: {e}")
            if not use_js:
                # Retry with JavaScript click
                return self.safe_click(element, use_js=True)
            return False

    def open_bookings_page(self):
        """
        Navigates to the Gaiola booking page and handles initial pop-ups/windows.
        """
        try:
            # Navigate to the main page first
            logger.info("Navigating to main page...")
            self.driver.get("https://www.areamarinaprotettagaiola.it/prenotazione/")
            
            # Wait for page to load
            self.human_like_delay(2, 4)
            
            # Handle cookies banner
            try:
                cookies_button = self.wait_for_element(By.CSS_SELECTOR, '[data-hook="consent-banner-close-button"]', 5) 
                if cookies_button:
                    logger.info("Closing cookies banner...")
                    self.safe_click(cookies_button)
            except Exception as e:
                logger.info(f"No cookie banner found: {e}")
            
            # Wait and do some human-like browsing behavior
            self.human_like_delay(2, 4)
            
            # Random scroll to simulate reading
            for _ in range(random.randint(1, 3)):
                self.human_like_scroll()
                self.human_like_delay(1, 2)
            
            # Find and click the "PRENOTA QUI" button
            prenota_selectors = [
                ".StylableButton2545352419__root",
                "[data-testid='linkElement']",
                "a[href*='booking']",
                "button:contains('PRENOTA')",
                ".booking-button"
            ]
            
            prenota_button = None
            for selector in prenota_selectors:
                try:
                    prenota_button = self.wait_for_element(By.CSS_SELECTOR, selector, 5)
                    if prenota_button:
                        logger.info(f"Found PRENOTA button with selector: {selector}")
                        break
                except Exception:
                    continue
            
            if not prenota_button:
                logger.error("Could not find PRENOTA QUI button")
                return False
            
            # Scroll to button area and wait
            self.human_like_scroll(prenota_button)
            self.human_like_delay(1, 3)
            
            # Click the button
            logger.info("Clicking PRENOTA QUI button...")
            if not self.safe_click(prenota_button):
                logger.error("Failed to click PRENOTA button")
                return False
            
            # Handle window switching if new window opens
            original_window = self.driver.current_window_handle
            self.human_like_delay(2, 4)  # Wait for potential new window
            
            # Check if new window opened
            if len(self.driver.window_handles) > 1:
                for window_handle in self.driver.window_handles:
                    if window_handle != original_window:
                        self.driver.switch_to.window(window_handle)
                        logger.info("Switched to new window")
                        break
            
            # Wait for new page to load
            self.human_like_delay(2, 4)
            
            logger.info(f"Current URL after navigation: {self.driver.current_url}")
            
            # Check if we got redirected to an access denied page
            if "accesso" in self.driver.current_url.lower() and "non consentito" in self.driver.current_url.lower(): 
                logger.error("Got redirected to access denied page")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in open_bookings_page_enhanced: {e}")
            return False

    def get_days_list(self) -> list[Day]:
        """
        Scrapes the available day buttons from the page and returns a list of Day objects.
        Filters out 'btn-danger' (unavailable) buttons.
        """
        try:
            bottoni_data = self.driver.find_elements(By.CLASS_NAME, "bottoni_data_904")
            # Filter out buttons that are marked as unavailable (btn-danger)
            bottoni_data_validi = [btn for btn in bottoni_data if 'btn-danger' not in btn.get_attribute('class').split(' ')]
            
            days_list = []
            for idx, btn in enumerate(bottoni_data_validi):
                try:
                    # Attempt to parse the date to ensure it's valid before creating a Day object
                    date_obj = datetime.strptime(btn.text, "%d/%m/%Y")
                    days_list.append(Day(btn.text, btn, idx, date_obj.strftime("%A")))
                except ValueError:
                    logger.info(f"Skipping invalid date button with text: {btn.text}")
            return days_list
        except Exception as e:
            logger.error(f"Error getting days list: {e}")
            return []

    def has_day_changed(self, current_day: date) -> bool:
        """
        Checks if the current day is different from the last recorded iteration day.
        Args:
            current_day (date): The current date.
        Returns:
            bool: True if the day has changed, False otherwise.
        """
        return current_day != self.last_iteration_day

    def get_dates_of_current_week(self) -> list[str]:
        """
        Calculates and returns the formatted dates for the current week.
        """
        today = datetime.today()
        start_of_week = today - timedelta(days=today.weekday())
        dates_of_week = [start_of_week + timedelta(days=i) for i in range(7)]
        formatted_dates = [d.strftime("%d/%m/%Y") for d in dates_of_week]
        return formatted_dates

    async def check_availability(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Checks the availability for the requested date and turno.
        If a spot is found, it attempts to book it and sends a message.
        This method is designed to be called by the APScheduler job.
        """
        job = context.job

        persona_richiesta: Person = job.data["persona_richiesta"]
        date_richieste: list[str] = job.data['date_richieste']
        turno_richiesto: list[Turno] = job.data['turno_richiesto'] # Expecting a list, e.g., [Turno.MATTINO]

        current_day = date.today()

        # Refresh page and days list if it's a new day or if the current URL is not the booking page
        if self.has_day_changed(current_day) or "booking" not in self.driver.current_url:
            logger.info("New day or not on booking page, refreshing page and days list.")
            self.driver.refresh()
            self.days = self.get_days_list()
            self.last_iteration_day = current_day
        
        # Log current day states for all available days
        [logger.info(f"-- {d}") for d in self.days]

        for day in self.days:
            if day.date in date_richieste:
                logger.info(f"Checking {day.day_name} {day.date} for {persona_richiesta.name}")
                try:
                    # Scroll to and click the date button
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", day.button)
                    day.button.click()
                    sleep(0.5) # Give page time to update after date selection

                    # Determine which radio button to click based on requested turno
                    if Turno.POMERIGGIO in turno_richiesto:
                        requested_radio_button = self.driver.find_element(By.CSS_SELECTOR, "[for='904_turno_2']") # Pomeriggio
                        other_radio_button = self.driver.find_element(By.CSS_SELECTOR, "[for='904_turno_1']") # Mattino
                    else: # Default to Mattino if not specified or if Mattino is in the list
                        requested_radio_button = self.driver.find_element(By.CSS_SELECTOR, "[for='904_turno_1']") # Mattino
                        other_radio_button = self.driver.find_element(By.CSS_SELECTOR, "[for='904_turno_2']") # Pomeriggio

                    # Click the "other" radio button first to get its availability, then the requested one
                    # This helps detect if a spot was freed up in the requested shift
                    other_radio_button.click()
                    sleep(0.4) # Wait for availability to update
                    alert_posti_other = self.driver.find_element(By.ID, "disponibilita_effettiva")
                    unwanted_current_disp = int(alert_posti_other.text.split(":")[1].strip())
                    
                    requested_radio_button.click()
                    sleep(0.4) # Wait for availability to update
                    alert_posti_requested = self.driver.find_element(By.ID, "disponibilita_effettiva")
                    current_disp = int(alert_posti_requested.text.split(":")[1].strip())

                    # Get previous availability for comparison
                    prev_disp = day.prev_disp_morning if Turno.MATTINO in turno_richiesto else day.prev_disp_noon

                    logger.info(f"* Posti {turno_richiesto[0].value.lower()}: {current_disp} (originale: {prev_disp})")

                    # Check if a spot has become available
                    if prev_disp == 0 and current_disp > 0 and current_disp != unwanted_current_disp:
                        messaggio_posto_libero = (
                            f"\n\n🚨 Posto liberato {day.day_name} {day.date} {turno_richiesto[0].value} 🚨\n"
                            f"Prenota: https://www.areamarinaprotettagaiola.it/prenotazione#comp-l4zkd4tv\n\n"
                        )
                        logger.info(messaggio_posto_libero)
                        await context.bot.send_message(job.chat_id, text=messaggio_posto_libero.strip())

                        # Attempt to book the spot
                        try:
                            self.book(selected_people=[persona_richiesta], email=self.config.EMAIL, tel=self.config.TEL)
                            sleep(5) # Wait for booking confirmation page to load
                            
                            # Extract booking code from URL if successful
                            booking_code = None
                            if "prenotazione=" in self.driver.current_url or "booking=" in self.driver.current_url:
                                booking_code = self.driver.current_url.split('prenotazione=')[1].split('&')[0]
                                logger.info(f"Booking successful! Code: {booking_code}")
                            else:
                                logger.warning(f"Booking successful, but could not extract booking code from URL {self.driver.current_url}.")

                            # Navigate back to the main booking page to reset state for next checks
                            self.open_bookings_page()

                            # Send booking confirmation message
                            booking_status_message = (
                                f"✅ Posto prenotato per {persona_richiesta.name} in data {day.date} "
                                f"({turno_richiesto[0].name})."
                            )
                            if booking_code:
                                booking_status_message += f" Codice: {booking_code}"
                                # Save booking details
                                from src.utils.helpers import save_to_json
                                save_to_json(persona_richiesta.name, booking_code)
                            else:
                                booking_status_message += " (Codice non disponibile)."

                            await context.bot.send_message(job.chat_id, text=booking_status_message)

                            # Stop the job after successful booking
                            # The job itself needs to be removed by the handler, not here
                            logger.info(f"Booking job for {persona_richiesta.name} completed.")
                            return # Exit after successful booking and message

                        except Exception as book_e:
                            logger.error(f"Error during booking for {persona_richiesta.name}: {book_e}")
                            await context.bot.send_message(job.chat_id, text=f"❌ Errore durante la prenotazione per {persona_richiesta.name}: {book_e}")
                            # Re-open booking page in case of booking error to reset state
                            self.open_bookings_page()
                            
                    # Update previous availability for the next check
                    if Turno.MATTINO in turno_richiesto:
                        day.prev_disp_morning = current_disp
                    else:
                        day.prev_disp_noon = current_disp

                except Exception as e:
                    logger.error(f"Error checking availability for {day.date} ({turno_richiesto[0].value}): {e}")
                    # If an element is not found or other Selenium error, refresh the page to try again next cycle
                    self.open_bookings_page()
                    break # Break from inner loop to refresh days list on next job run

        logger.info("\n\n-------------\n\n")


    def book(self, selected_people: list[Person], email: str, tel: str):
        """
        Fills out the booking form with the selected people's details.
        Args:
            selected_people (list[Person]): List of Person objects to book for.
            email (str): The email address to use for booking.
            tel (str): The phone number to use for booking.
        """
        logger.info(f"Attempting to book for: {[p.name for p in selected_people]}")
        try:
            # Click the "Prenota" (Book) button to proceed to the form
            self.driver.find_element(By.ID, "CheckAvailability_904").click()
            sleep(1) # Wait for the form to load

            for idx, p in enumerate(selected_people):
                form_idx = idx + 1 # Form fields are 1-indexed
                
                # Fill in personal details for each person
                self._fill_input_field(f"nome_{form_idx}", p.name)
                self._fill_input_field(f"cognome_{form_idx}", p.surname)
                self._fill_input_field(f"sesso_{form_idx}", p.sex)
                self._fill_input_field(f"data_nascita_{form_idx}", p.bday)
                
                # Handle select2 dropdowns for comune_nascita, stato_residenza, regione_residenza, provincia_residenza, comune_residenza
                self._select2_dropdown(f"comune_nascita_{form_idx}", "NAPOLI")
                self._fill_input_field(f"codice_fiscale_{form_idx}", p.cf)
                self._fill_input_field(f"email_{form_idx}", email)
                
                self._select2_dropdown(f"stato_residenza_{form_idx}", "Italia")
                self._select2_dropdown(f"provincia_residenza_{form_idx}", "Napoli")
                # self._select2_dropdown(f"regione_residenza_{form_idx}", "CAMPANIA")
                # self._select2_dropdown(f"comune_residenza_{form_idx}", "NAPOLI")

                # Handle municipalita dropdown (specific logic for 'muni')
                try:
                    municipalita_container = self.driver.find_element(By.ID, f"select2-municipalita_{form_idx}-container")
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", municipalita_container)
                    municipalita_container.click()
                    municipalita_txt_field = self.driver.find_element(By.CLASS_NAME, "select2-search__field")
                    municipalita_txt_field.send_keys("muni")
                    municipalita_txt_field.send_keys(Keys.RETURN)
                    logger.info(f"Filled municipalita for {p.name}.")
                except Exception as e:
                    logger.warning(f"Could not fill municipalita for {p.name}: {e}")

            # Fill in main contact details
            self._fill_input_field("email_main", email)
            self._fill_input_field("email_main2", email)
            self._fill_input_field("telefono", tel)

            # Accept privacy and regulations
            self._click_checkbox("privacy")
            self._click_checkbox("regolamento")

            # Confirm booking
            prenota_btn = self.driver.find_element(By.ID, "ConfermaPrenotazione")
            self.driver.execute_script("arguments[0].scrollIntoView(true);", prenota_btn)
            prenota_btn.click()
            logger.info("Booking confirmation button clicked.")
            sleep(3) # Wait for the booking to process and redirect

        except Exception as e:
            logger.error(f"Error during booking process: {e}")
            raise # Re-raise the exception to be caught by the caller (check_availability)

    def _fill_input_field(self, element_id: str, value: str):
        """Helper to find an element by ID, scroll to it, and send keys."""
        try:
            element = self.driver.find_element(By.ID, element_id)
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            element.send_keys(value)
            logger.debug(f"Filled {element_id} with {value}.")
        except Exception as e:
            logger.warning(f"Could not fill input field {element_id}: {e}")

    def _select2_dropdown(self, container_id: str, value: str):
        """Helper to interact with Select2 dropdowns."""
        try:
            container = self.driver.find_element(By.CSS_SELECTOR, f"[aria-labelledby=select2-{container_id}-container]")
            self.driver.execute_script("arguments[0].scrollIntoView(true);", container)
            container.click()
            search_field = self.driver.find_element(By.CLASS_NAME, "select2-search__field")
            search_field.send_keys(value)
            search_field.send_keys(Keys.RETURN)
            logger.debug(f"Selected '{value}' in dropdown {container_id}.")
        except Exception as e:
            logger.warning(f"Could not interact with Select2 dropdown {container_id} for value '{value}': {e}")

    def _click_checkbox(self, element_id: str):
        """Helper to find a checkbox by ID, scroll to it, and click it."""
        try:
            checkbox = self.driver.find_element(By.ID, element_id)
            self.driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
            checkbox.click()
            logger.debug(f"Clicked checkbox {element_id}.")
        except Exception as e:
            logger.warning(f"Could not click checkbox {element_id}: {e}")

