import os
from datetime import datetime, timedelta, date
import random
from time import sleep
from dataclasses import dataclass
import logging
from enum import Enum
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from pyvirtualdisplay import Display
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackContext, CallbackQueryHandler, MessageHandler, filters
from dotenv import load_dotenv
import platform
from booking import book
from data import all_people
from helpers import save_to_json, find_code_by_name, delete_booking_file

load_dotenv()
TELE_TOKEN = os.getenv('TELE_TOKEN')
MY_ID = os.getenv("MY_ID")
CUSTOM_USER_AGENT = os.getenv('CUSTOM_USER_AGENT', 'Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0')
FIREFOX_PROFILE_PATH = os.getenv('FIREFOX_PROFILE_PATH')

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)

@dataclass
class Day:
    date: str
    button: any
    day_number: int
    day_name: str
    new_disp_morning: int
    prev_disp_morning: int
    new_disp_noon: int
    prev_disp_noon: int

    def __repr__(self) -> str:
        return f"{self.date} - prev_disp_morning: {self.prev_disp_morning}, new_disp_morning: {self.new_disp_morning}, prev_disp_noon: {self.prev_disp_noon}, new_disp_noon: {self.new_disp_noon}"

class Turno(Enum):
    MATTINO = "Mattino"
    POMERIGGIO = "Pomeriggio"

# Arbitrarily set days that i want to check
chosen_days_str = os.getenv('CHOSEN_DAYS')
if chosen_days_str:
    chosen_days = chosen_days_str.split(',')
else:
    chosen_days = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]

def is_raspberry_pi():
    try:
        with open('/proc/cpuinfo', 'r') as cpuinfo:
            if 'Raspberry Pi' in cpuinfo.read():
                return True
    except FileNotFoundError:
        pass
    return False

def human_like_delay(min_delay=0.5, max_delay=2.0):
    """Generate human-like random delays"""
    delay = random.uniform(min_delay, max_delay)
    sleep(delay)

def human_like_scroll(driver, element=None):
    """Simulate human-like scrolling"""
    if element:
        # Scroll to element with random offset
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
            element
        )
    else:
        # Random scroll
        scroll_amount = random.randint(100, 500)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
    
    human_like_delay(0.5, 1.5)

def human_like_mouse_movement(driver, element):
    """Simulate human-like mouse movement to element"""
    actions = ActionChains(driver)
    
    # Move to a random point near the element first
    actions.move_to_element_with_offset(element, 
                                       random.randint(-10, 10), 
                                       random.randint(-10, 10))
    actions.perform()
    human_like_delay(0.1, 0.3)
    
    # Then move to the actual element
    actions.move_to_element(element)
    actions.perform()
    human_like_delay(0.2, 0.5)

def get_enhanced_driver():
    """Enhanced driver with better anti-detection measures"""
    options = Options()
    
    # Basic options
    if is_raspberry_pi():
        options.headless = True
    
    # Enhanced anti-detection preferences
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
    
    # Check if a Firefox profile path is provided and exists
    if FIREFOX_PROFILE_PATH and os.path.exists(FIREFOX_PROFILE_PATH):
        logger.info(f"Using Firefox profile from: {FIREFOX_PROFILE_PATH}")
        profile = FirefoxProfile(FIREFOX_PROFILE_PATH)
        
        # Set additional profile preferences
        profile.set_preference("dom.webdriver.enabled", False)
        profile.set_preference("useAutomationExtension", False)
        profile.set_preference("general.useragent.override", CUSTOM_USER_AGENT)
        
        options.profile = profile
    else:
        logger.warning("No Firefox profile path provided or path does not exist. Using default profile.")
    
    # Set custom User-Agent
    options.set_preference("general.useragent.override", CUSTOM_USER_AGENT)
    logger.info(f"Setting User-Agent to: {CUSTOM_USER_AGENT}")
    
    service = Service(executable_path='/usr/local/bin/geckodriver') if is_raspberry_pi() else None
    driver = webdriver.Firefox(options=options, service=service)
    
    # Execute JavaScript to remove webdriver property
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    # Add some randomness to viewport size
    if not is_raspberry_pi():
        width = random.randint(1200, 1920)
        height = random.randint(800, 1080)
        driver.set_window_size(width, height)
    
    return driver

def wait_for_element(driver, by, value, timeout=10):
    """Wait for element with timeout"""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except TimeoutException:
        logger.warning(f"Element not found within {timeout} seconds: {value}")
        return None

def safe_click(driver, element, use_js=False):
    """Safely click an element with human-like behavior"""
    try:
        # Scroll to element
        human_like_scroll(driver, element)
        
        # Wait a bit
        human_like_delay(0.5, 1.0)
        
        # Move mouse to element
        human_like_mouse_movement(driver, element)
        
        # Wait for element to be clickable
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(element))
        
        if use_js:
            # Use JavaScript click as fallback
            driver.execute_script("arguments[0].click();", element)
        else:
            # Try normal click first
            element.click()
        
        # Wait after click
        human_like_delay(1.0, 2.0)
        return True
        
    except Exception as e:
        logger.error(f"Error clicking element: {e}")
        if not use_js:
            # Retry with JavaScript click
            return safe_click(driver, element, use_js=True)
        return False


def open_bookings_page_enhanced(driver):
    """Enhanced booking page opening with better anti-detection"""
    try:
        # Navigate to the main page first
        logger.info("Navigating to main page...")
        driver.get("https://www.areamarinaprotettagaiola.it/prenotazione/")
        
        # Wait for page to load
        human_like_delay(2, 4)
        
        # Handle cookies banner
        try:
            cookies_button = wait_for_element(driver, By.CSS_SELECTOR, '[data-hook="consent-banner-close-button"]', 5)
            if cookies_button:
                logger.info("Closing cookies banner...")
                safe_click(driver, cookies_button)
        except Exception as e:
            logger.info(f"No cookie banner found: {e}")
        
        # Handle initial alert/popup
        # try:
        #     # Try multiple selectors for the popup close button
        #     popup_selectors = [
        #         ".wixui-button__label",
        #         "[data-testid='popupCloseButton']",
        #         ".close-button",
        #         "[aria-label='Close']"
        #     ]
            
        #     for selector in popup_selectors:
        #         try:
        #             popup_button = wait_for_element(driver, By.CSS_SELECTOR, selector, 3)
        #             if popup_button:
        #                 logger.info(f"Closing popup with selector: {selector}")
        #                 safe_click(driver, popup_button)
        #                 break
        #         except Exception:
        #             continue
                    
        # except Exception as e:
        #     logger.info(f"No initial alert found: {e}")
        
        # Wait and do some human-like browsing behavior
        human_like_delay(2, 4)
        
        # Random scroll to simulate reading
        for _ in range(random.randint(1, 3)):
            human_like_scroll(driver)
            human_like_delay(1, 2)
        
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
                prenota_button = wait_for_element(driver, By.CSS_SELECTOR, selector, 5)
                if prenota_button:
                    logger.info(f"Found PRENOTA button with selector: {selector}")
                    break
            except Exception:
                continue
        
        if not prenota_button:
            logger.error("Could not find PRENOTA QUI button")
            return False
        
        # Scroll to button area and wait
        human_like_scroll(driver, prenota_button)
        human_like_delay(1, 3)
        
        # Click the button
        logger.info("Clicking PRENOTA QUI button...")
        if not safe_click(driver, prenota_button):
            logger.error("Failed to click PRENOTA button")
            return False
        
        # Handle window switching if new window opens
        original_window = driver.current_window_handle
        human_like_delay(2, 4)  # Wait for potential new window
        
        # Check if new window opened
        if len(driver.window_handles) > 1:
            for window_handle in driver.window_handles:
                if window_handle != original_window:
                    driver.switch_to.window(window_handle)
                    logger.info("Switched to new window")
                    break
        
        # Wait for new page to load
        human_like_delay(2, 4)
        
        logger.info(f"Current URL after navigation: {driver.current_url}")
        
        # Check if we got redirected to an access denied page
        if "access" in driver.current_url.lower() and "denied" in driver.current_url.lower():
            logger.error("Got redirected to access denied page")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error in open_bookings_page_enhanced: {e}")
        return False



driver = get_enhanced_driver()
success = open_bookings_page_enhanced(driver)


last_iteration_day = None
days = None

def get_days_list():
    bottoni_data = driver.find_elements(By.CLASS_NAME, "bottoni_data_904")
    bottoni_data_validi = [btn for btn in bottoni_data if 'btn-danger' not in btn.get_attribute('class').split(' ')]
    days = []
    for idx, btn in enumerate(bottoni_data_validi):
        try:
            days.append(Day(btn.text, btn, idx, datetime.strptime(btn.text, "%d/%m/%Y").strftime("%A"), 0, 0, 0, 0))
        except ValueError:
            logger.info(f"Found invalid button with text {btn.text}")
    return days

def has_day_changed(current_day):
    """Check if the day has changed compared to the last iteration day."""
    global last_iteration_day
    return current_day != last_iteration_day

while not days:  # è il primo ciclo dopo l'avvio
    logger.info("creating days list")
    sleep(1)
    days = get_days_list()
    
logger.info(f"\n\nRelevant possible days list:\n{[d.date for d in days]}\n\n")
# logger.info(f"\n\nUser chosen days:\n{chosen_days}\n\n")


def get_dates_of_current_week():
    today = datetime.today()
    start_of_week = today - timedelta(days=today.weekday())
    dates_of_week = [start_of_week + timedelta(days=i) for i in range(7)]
    formatted_dates = [date.strftime("%d/%m/%Y") for date in dates_of_week]
    return formatted_dates

#  Setup Bot ----------------------------------------------------------------------------------------

def check_job_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    else:
        return True


async def show_dates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show dates available."""
    nl = "\n"
    dates = get_dates_of_current_week()
    await update.effective_message.reply_text(f"Date disponibili:\n{nl.join(dates)}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a job to the queue."""
    chat_id = update.effective_message.chat_id
    user_id = str(update.effective_user.id)
    logger.info(f"{update.message.from_user.name} started the task (ID: {MY_ID})")
    logger.info(f"\n\nSelected days for checking: {','.join(chosen_days)}")
    
    
    if user_id != str(MY_ID):
        await update.effective_message.reply_text("Non dovresti essere qui...")
    else:
        if check_job_exists(str(chat_id), context):
            await update.effective_message.reply_text("Bot già avviato")
    
        global days
        global last_iteration_day
        current_day = date.today()
        last_iteration_day = current_day
        # driver.get("https://booking.areamarinaprotettagaiola.it/booking/")
        if "booking" not in driver.current_url:
            open_bookings_page_enhanced(driver)
        days = get_days_list()
        
        keyboard = [
            [InlineKeyboardButton(p.name, callback_data=f"select_person_{p.name}")] for p in all_people
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)    
        await update.effective_message.reply_text("Seleziona la persona:", reply_markup=reply_markup)


async def select_person(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    selected_person_name = query.data.split('_')[-1]
    context.user_data['selected_person'] = next(p for p in all_people if p.name == selected_person_name)
    
    keyboard = [
        [InlineKeyboardButton("Mattina", callback_data="select_shift_m")],
        [InlineKeyboardButton("Pomeriggio", callback_data="select_shift_p")],
        [InlineKeyboardButton("Entrambi", callback_data="select_shift_mp")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(f"Persona selezionata:\n{context.user_data['selected_person'].name}\n\nSeleziona il turno:", reply_markup=reply_markup)


async def select_shift(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    selected_shift = query.data.split('_')[-1]
    if selected_shift == "m":
        context.user_data['selected_shift'] = [Turno.MATTINO] 
    elif selected_shift == "p": 
        context.user_data['selected_shift'] = [Turno.POMERIGGIO]
    elif selected_shift == "mp": 
        context.user_data['selected_shift'] = [Turno.POMERIGGIO, Turno.MATTINO]
    
    
    keyboard = [
        [InlineKeyboardButton(d.date, callback_data=f"select_date_{d.date}")] for d in days
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Assuming date selection is handled separately, for simplicity
    await query.edit_message_text(f"Turno selezionato:\n{','.join([t.name for t in context.user_data['selected_shift']])}\n\nSeleziona la data:", reply_markup=reply_markup)


async def select_date(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    selected_date = query.data.split('_')[-1]
    context.user_data['selected_date'] = selected_date
    
    persona_richiesta = context.user_data['selected_person']
    data_richiesta = selected_date.split(",")
    turno_richiesto = context.user_data['selected_shift']
    
    chat_id = update.effective_message.chat_id
    
    
    context.job_queue.run_repeating(
        check_availability, 
        interval=10, 
        first=3, 
        name=f"{update.effective_chat.username} booking for {persona_richiesta.name} for {data_richiesta} - {turno_richiesto}", 
        chat_id=chat_id, 
        data={
            "persona_richiesta": persona_richiesta,
            "date_richieste": data_richiesta, 
            "turno_richiesto": turno_richiesto
        }
    )
    
    text = (f"Bot avviato. Ricerca posti per {persona_richiesta.name} {persona_richiesta.surname} "
            f"in data {' & '.join(data_richiesta)} turno {' / '.join([t.name for t in turno_richiesto])}")
    await update.effective_message.reply_text(text)

async def check_availability(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the alarm message."""

    global last_iteration_day
    global days
    job = context.job

    current_day = date.today()
    if has_day_changed(current_day):
        logger.info("\nNew day, refreshing page\n")
        driver.refresh()
        days = get_days_list()
        last_iteration_day = current_day
        

    [print(f"-- {day}") for day in days]

    # if days[-1].date not in get_dates_of_current_week():  # è una nuova settimana 
    #     logger.info("\nNew week detected, refreshing page\n")
    #     driver.refresh()
    #     days = get_days_list()
    #     [logger.info(f"-- {day}") for day in days]

    persona_richiesta = job.data["persona_richiesta"]
    date_richieste = job.data['date_richieste']
    turno_richiesto = job.data['turno_richiesto']
    
    for day in days:
        if day.date in date_richieste:
            logger.info(f"\n\nChecking {day.day_name} {day.date} for {persona_richiesta.name}")
            driver.execute_script("arguments[0].scrollIntoView(true);", day.button)
            day.button.click()
            # turns = driver.find_elements(By.NAME, 'turno')
            # for idx, e in enumerate(turns):
                # turno = Turno.MATTINO if idx == 0 else Turno.POMERIGGIO
                # if turno in turno_richiesto:
                    # e.click()
                    # sleep(0.1)
            if turno_richiesto[0].name == "POMERIGGIO":
                requested_radio_button = driver.find_element(By.CSS_SELECTOR, "[for='904_turno_2']")
                other_radio_button = driver.find_element(By.CSS_SELECTOR, "[for='904_turno_1']")
            else:
                requested_radio_button = driver.find_element(By.CSS_SELECTOR, "[for='904_turno_1']")
                other_radio_button = driver.find_element(By.CSS_SELECTOR, "[for='904_turno_2']")
            
            other_radio_button.click()
            alert_posti = driver.find_element(By.ID, "disponibilita_effettiva")
            unwanted_current_disp = int(alert_posti.text.split(":")[1])
            sleep(0.4)
            requested_radio_button.click()

            alert_posti = driver.find_element(By.ID, "disponibilita_effettiva")
            current_disp = int(alert_posti.text.split(":")[1])
            prev_disp = day.prev_disp_morning if turno_richiesto[0] == Turno.MATTINO else day.prev_disp_noon
            # new_disp = day.new_disp_morning if turno == Turno.MATTINO else day.new_disp_noon

            logger.info(f"* Posti {turno_richiesto[0].value.lower()}: {str(current_disp)} (originale: {prev_disp})")
            if prev_disp == 0 and current_disp != 0 and current_disp != unwanted_current_disp:
                
                messaggio_posto_libero = f"\n\nPosto liberato {day.day_name} {day.date} {turno_richiesto[0].value}\nPrenota: https://www.areamarinaprotettagaiola.it/prenotazione#comp-l4zkd4tv\n\n"
                logger.info(messaggio_posto_libero)
                await context.bot.send_message(job.chat_id, text=messaggio_posto_libero.strip())
                
                #TODO
                book(driver=driver, selected_people=[persona_richiesta], email=os.getenv("EMAIL"))
                sleep(30)
                code = driver.current_url.split('prenotazione=')[1]
                header_link = driver.find_element(By.CSS_SELECTOR, ".navbar-brand")
                header_link.click()
                current_jobs = context.job_queue.get_jobs_by_name(job.name)
                for job in current_jobs:
                    job.schedule_removal()
                await context.bot.send_message(job.chat_id, text=f"Posto prenotato per {persona_richiesta.name} in data {day.date} ({turno_richiesto[0].name}) Codice: {code}")

                save_to_json(persona_richiesta.name, code)

            #  aggiornamento disponibilità precedente
            if turno_richiesto[0] == Turno.MATTINO:
                day.prev_disp_morning = current_disp
            else:
                day.prev_disp_noon = current_disp
            
    print("\n\n-------------\n\n")


async def delete_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    current_jobs = context.job_queue.jobs()
    if current_jobs:
        for job in current_jobs:
            job.schedule_removal()
            logger.info(f"Deleted job: {job.name}")
            await context.bot.send_message(job.chat_id, text=f"Deleted job: {job.name}")
    else:
        await context.bot.send_message(update.effective_message.chat_id, text=f"No jobs active")
    current_jobs = context.job_queue.get_jobs_by_name(str(context._chat_id))
    logger.info(f"Current jobs: {current_jobs}")


#WIP
async def delete_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bookings = os.listdir("bookings")
    if bookings:
        keyboard = [
            [InlineKeyboardButton(p.replace("_", " ").replace(".json", ""), callback_data=f"select_person_to_delete_{p.split('_')[0]}")] for p in bookings
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)    
        await update.effective_message.reply_text("Seleziona la persona di cui eliminare la prenotazione:", reply_markup=reply_markup)
    else:
        await update.effective_message.reply_text("Nessuna prenotazione da cancellare")


#WIP
async def select_person_to_delete(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    selected_person_name = query.data.split('_')[-1]
    person_list = [p for p in all_people if p.name.lower() == selected_person_name.lower()]

    if not person_list:
        await update.effective_message.reply_text(f"Person named {selected_person_name} not found.")
        return
    
    person_obj = person_list[0]
    code = find_code_by_name(person_obj.name)
    
    cancellation_url = f"https://booking.areamarinaprotettagaiola.it/booking/prenotazione_cancella.php?action=2&id={code.replace('.json', '')}&cf={person_obj.cf}"
    logger.info(cancellation_url)
    driver.get(cancellation_url)
    delete_status = delete_booking_file(person_obj.name, code)
    
    if delete_status:
        await update.effective_message.reply_text(f"Prenotazione per {person_obj.name} cancellata")
    else:
        await update.effective_message.reply_text(f"Errore nella cancellazione")


async def show_current_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    current_jobs = context.job_queue.jobs()
    if current_jobs:
        for job in current_jobs:
            jobs_str = "\n\n".join([job.name for job in current_jobs])
            job.schedule_removal()
            logger.info(jobs_str)
            await context.bot.send_message(job.chat_id, text=jobs_str)
    else:
        await context.bot.send_message(update.effective_message.chat_id, text=f"No jobs active")
    logger.info(f"Current jobs: {current_jobs}")


def run_bot() -> None:
    """Run bot."""
    
    
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELE_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("deletebooking", delete_booking))
    application.add_handler(CallbackQueryHandler(select_person_to_delete, pattern="^select_person_to_delete_"))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("deletejobs", delete_jobs))
    application.add_handler(CommandHandler("showdates", show_dates))
    application.add_handler(CallbackQueryHandler(select_person, pattern="^select_person_"))
    application.add_handler(CallbackQueryHandler(select_shift, pattern="^select_shift_"))
    application.add_handler(CallbackQueryHandler(select_date, pattern="^select_date_"))
    application.add_handler(CommandHandler("showcurrentjobs", show_current_jobs))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


run_bot()