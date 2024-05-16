import os
from datetime import datetime, timedelta, date
from time import sleep
from dataclasses import dataclass
import logging
from enum import Enum
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from pyvirtualdisplay import Display
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv


options = Options()
options.headless = True  # Run in headless mode
driver = webdriver.Firefox(executable_path='/usr/local/bin/geckodriver', options=options)

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

load_dotenv()
TELE_TOKEN = os.getenv('TELE_TOKEN')
MY_ID = os.getenv("MY_ID")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_dates_of_current_week():
    today = datetime.today()
    start_of_week = today - timedelta(days=today.weekday())
    dates_of_week = [start_of_week + timedelta(days=i) for i in range(7)]
    formatted_dates = [date.strftime("%d/%m/%Y") for date in dates_of_week]
    return formatted_dates



#  Open Gaiola window -------------------------------------------------------------------------------

# display = Display(visible=0, size=(1366, 768))
# display.start()

driver = webdriver.Firefox()

driver.get("https://www.areamarinaprotettagaiola.it/prenotazione/")
print(driver.current_url)
driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2)")
driver.find_element(By.PARTIAL_LINK_TEXT, "PRENOTA").click()
original_window = driver.current_window_handle
for window_handle in driver.window_handles:
    if window_handle != original_window:
        driver.switch_to.window(window_handle)
        break
sleep(1)
print(driver.current_url)
days = None
last_iteration_day = None


#  Setup Bot ----------------------------------------------------------------------------------------

def check_job_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    else:
        return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a job to the queue."""
    chat_id = update.effective_message.chat_id
    user_id = str(update.effective_user.id)
    logger.info(f"{update.message.from_user.name} started the task (ID: {MY_ID})")
    if user_id != str(MY_ID):
        await update.effective_message.reply_text("Non dovresti essere qui...")
    else:
        if check_job_exists(str(chat_id), context):
            await update.effective_message.reply_text("Bot già avviato")
        else:
            context.job_queue.run_repeating(check_availability, interval=20, first=5, name=str(chat_id), chat_id=chat_id)
            text = f"Bot avviato."
            await update.effective_message.reply_text(text)


async def start_notify_on_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Notify on days by specifing date and turn like 05/08/2023P"""
    chat_id = update.effective_message.chat_id
    user_id = str(update.effective_user.id)
    print(f"{user_id} started the task (ID: {MY_ID})")
    if user_id != str(MY_ID):
        await update.effective_message.reply_text("Non dovresti essere qui...")
    else:
        if len(context.args) == 1:
            data_richiesta = context.args[0][:-1]
            turno_richiesto = context.args[0][-1:].lower()

            if turno_richiesto not in ["m", "p"]:
                text = f"{turno_richiesto} non è un turno valido, scrivi M o P per mattina o pomeriggio"
            if check_job_exists(str(chat_id), context):
                text = f"Bot già avviato. Ricerca data: {data_richiesta} {turno_richiesto}"
            else:
                context.job_queue.run_repeating(
                    check_availability, 
                    interval=20, 
                    first=5, 
                    name=str(chat_id), 
                    chat_id=chat_id, 
                    data={
                            "date": data_richiesta, 
                            "turn": turno_richiesto
                        }
                    )
                text = f"Bot avviato. Ricerca data: {data_richiesta} {turno_richiesto}"
        else:
            text = "Scrivi la data e il turno desiderato separati da spazi (/start 01/01/2000 M/P)"
        await update.effective_message.reply_text(text)


def get_days_list():
    bottoni_data = driver.find_elements(By.CLASS_NAME, "bottoni_data_904")
    bottoni_data_validi = [btn for btn in bottoni_data if 'btn-danger' not in btn.get_attribute('class').split(' ')]
    days = [Day(btn.text, btn, idx, datetime.strptime(btn.text, "%d/%m/%Y").strftime("%A"), 0, 0, 0, 0) for idx, btn in enumerate(bottoni_data_validi)]
    return days


async def check_availability(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the alarm message."""
    global days
    global last_iteration_day
    job = context.job

    current_day = date.today()
    logger.info(f"Current day: {current_day}, Last iteration day: {last_iteration_day}")
    if last_iteration_day and last_iteration_day != current_day: # se è un nuovo giorno refreshiamo la pagina
        logger.info("New day, refreshing page")
        driver.refresh()
        days = get_days_list()
    else:
        days = get_days_list()
        
    last_iteration_day = current_day
    
    while not days:  # è il primo ciclo dopo l'avvio
        logger.info("creating days list")
        days = get_days_list()
    [logger.info(f"-- {day}") for day in days]

    if days[-1].date not in get_dates_of_current_week():  # è una nuova settimana 
        logger.info("\nNew week detected, refreshing page\n")
        driver.refresh()
        days = get_days_list()
        [logger.info(f"-- {day}") for day in days]

    async def check_single_day(day, turno_richiesto):

        logger.info(f"Checking {day.day_name} {day.date}")
        driver.execute_script("arguments[0].scrollIntoView(true);", day.button)
        day.button.click()
        turns = driver.find_elements(By.NAME, 'turno')
        if turno_richiesto == Turno.MATTINO:
            turns[1].click()
            turns[0].click()
        elif turno_richiesto == Turno.POMERIGGIO:
            turns[0].click()
            turns[1].click()
        sleep(0.1)
        alert_posti = driver.find_element(By.ID, "disponibilita_effettiva")
        current_disp = int(alert_posti.text[-1])
        prev_disp = day.prev_disp_morning if turno_richiesto == Turno.MATTINO else day.prev_disp_noon
        # new_disp = day.new_disp_morning if turno == Turno.MATTINO else day.new_disp_noon

        logger.info(f"* Posti {turno_richiesto.value.lower()}: {str(current_disp)} (originale: {prev_disp})")
        if prev_disp == 0 and current_disp != 0:
            messaggio_posto_libero = f"Posto liberato {day.day_name} {day.date} {turno_richiesto.value}\nPrenota: https://www.areamarinaprotettagaiola.it/prenotazione#comp-l4zkd4tv"
            print(messaggio_posto_libero)
            await context.bot.send_message(job.chat_id, text=messaggio_posto_libero)

        #  aggiornamento disponibilità precedente
        if turno_richiesto == Turno.MATTINO:
            day.prev_disp_morning = current_disp
        else:
            day.prev_disp_noon = current_disp


    for day in days:
        if job.data:
            logger.info(f"JOB DATA CONTEXT FOUND {job.data}")
            data_richiesta = job.data['date']
            turno_richiesto = Turno.MATTINO if job.data['turn'] == "m" else Turno.POMERIGGIO
            if day.date == data_richiesta:
                await check_single_day(day, turno_richiesto)

        else:
            # Arbitrarily decided that i want only weekend days
            if day.day_name.lower() in ["saturday", "sunday"]:
                logger.info(f"Checking {day.day_name} {day.date}")
                driver.execute_script("arguments[0].scrollIntoView(true);", day.button)
                day.button.click()
                turns = driver.find_elements(By.NAME, 'turno')
                for idx, e in enumerate(turns):
                    e.click()
                    sleep(0.1)
                    alert_posti = driver.find_element(By.ID, "disponibilita_effettiva")
                    turno = Turno.MATTINO if idx == 0 else Turno.POMERIGGIO
                    current_disp = int(alert_posti.text[-1])
                    prev_disp = day.prev_disp_morning if turno == Turno.MATTINO else day.prev_disp_noon
                    # new_disp = day.new_disp_morning if turno == Turno.MATTINO else day.new_disp_noon

                    logger.info(f"* Posti {turno.value.lower()}: {str(current_disp)} (originale: {prev_disp})")
                    if prev_disp == 0 and current_disp != 0:
                        messaggio_posto_libero = f"\n\nPosto liberato {day.day_name} {day.date} {turno.value}\nPrenota: https://www.areamarinaprotettagaiola.it/prenotazione\n\n"
                        logger.info(messaggio_posto_libero)
                        await context.bot.send_message(job.chat_id, text=messaggio_posto_libero.strip())

                    #  aggiornamento disponibilità precedente
                    if turno == Turno.MATTINO:
                        day.prev_disp_morning = current_disp
                    else:
                        day.prev_disp_noon = current_disp
            
    print("\n\n-------------\n\n")


def run_bot() -> None:
    """Run bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELE_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("notifyday", start_notify_on_days))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


run_bot()