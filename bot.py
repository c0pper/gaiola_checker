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
from pyvirtualdisplay import Display
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackContext, CallbackQueryHandler, MessageHandler, filters
from dotenv import load_dotenv
import platform
from booking import book
from data import all_people

load_dotenv()
TELE_TOKEN = os.getenv('TELE_TOKEN')
MY_ID = os.getenv("MY_ID")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


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
# ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
chosen_days_str = os.getenv('CHOSEN_DAYS')
if chosen_days_str:
    chosen_days = chosen_days_str.split(',')
else:
    chosen_days = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]

if platform.system() == "Linux":
    options = Options()
    options.headless = True  # Run in headless mode
    driver = webdriver.Firefox(options=options, service=Service(executable_path='/usr/local/bin/geckodriver'))
elif platform.system() == "Windows":
    driver = webdriver.Firefox()


last_iteration_day = None
days = None


def get_days_list():
    bottoni_data = driver.find_elements(By.CLASS_NAME, "bottoni_data_904")
    bottoni_data_validi = [btn for btn in bottoni_data if 'btn-danger' not in btn.get_attribute('class').split(' ')]
    days = [Day(btn.text, btn, idx, datetime.strptime(btn.text, "%d/%m/%Y").strftime("%A"), 0, 0, 0, 0) for idx, btn in enumerate(bottoni_data_validi)]
    return days



#  Open Gaiola window -------------------------------------------------------------------------------
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

while not days:  # è il primo ciclo dopo l'avvio
    logger.info("creating days list")
    sleep(1)
    days = get_days_list()
    
logger.info(f"\n\nRelevant possible days list:\n{[d.date for d in days]}\n\n")
logger.info(f"\n\nUser chosen days:\n{chosen_days}\n\n")


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
    await update.effective_message.reply_text(f"Date disponibili:\n{nl.join([d.date for d in days])}")

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
    
    await query.edit_message_text("Seleziona il turno:", reply_markup=reply_markup)


async def select_shift(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    selected_shift = query.data.split('_')[-1]
    if selected_shift == "m":
        context.user_data['selected_shift'] = [Turno.MATTINO] 
    elif selected_shift == "m": 
        context.user_data['selected_shift'] = [Turno.POMERIGGIO]
    elif selected_shift == "mp": 
        context.user_data['selected_shift'] = [Turno.POMERIGGIO, Turno.MATTINO]
    
    
    keyboard = [
        [InlineKeyboardButton(d.date, callback_data=f"select_date_{d.date}")] for d in days
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Assuming date selection is handled separately, for simplicity
    await query.edit_message_text("Seleziona la data:", reply_markup=reply_markup)


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
        interval=20, 
        first=5, 
        name=str(chat_id), 
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
                    interval=random.randint(17,25), 
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
    # else:
    #     days = get_days_list()
        
    last_iteration_day = current_day

    [logger.info(f"-- {day}") for day in days]

    if days[-1].date not in get_dates_of_current_week():  # è una nuova settimana 
        logger.info("\nNew week detected, refreshing page\n")
        driver.refresh()
        days = get_days_list()
        [logger.info(f"-- {day}") for day in days]

    persona_richiesta = job.data["persona_richiesta"]
    date_richieste = job.data['date_richieste']
    turno_richiesto = job.data['turno_richiesto']
    
    for day in days:
        # if day.date == data_richiesta:
        #     await check_single_day(day, turno_richiesto)
        
        # Arbitrarily decided that i want only weekend days
        if day.date in date_richieste:
            logger.info(f"\n\nChecking {day.day_name} {day.date} for {persona_richiesta.name}")
            driver.execute_script("arguments[0].scrollIntoView(true);", day.button)
            day.button.click()
            turns = driver.find_elements(By.NAME, 'turno')
            for idx, e in enumerate(turns):
                turno = Turno.MATTINO if idx == 0 else Turno.POMERIGGIO
                e.click()
                sleep(0.1)
                alert_posti = driver.find_element(By.ID, "disponibilita_effettiva")
                current_disp = int(alert_posti.text[-1])
                prev_disp = day.prev_disp_morning if turno == Turno.MATTINO else day.prev_disp_noon
                # new_disp = day.new_disp_morning if turno == Turno.MATTINO else day.new_disp_noon

                logger.info(f"* Posti {turno.value.lower()}: {str(current_disp)} (originale: {prev_disp})")
                if prev_disp == 0 and current_disp != 0:
                    messaggio_posto_libero = f"\n\nPosto liberato {day.day_name} {day.date} {turno.value}\nPrenota: https://booking.areamarinaprotettagaiola.it/booking/\n\n"
                    logger.info(messaggio_posto_libero)
                        
                    if turno in turno_richiesto:
                            await context.bot.send_message(job.chat_id, text=messaggio_posto_libero.strip())
                            
                            #TODO
                            # current_jobs = context.job_queue.get_jobs_by_name(str(context._chat_id))
                            # for job in current_jobs:
                            #     job.schedule_removal()
                            # book(driver=driver, selected_people=[persona_richiesta], email=os.getenv("EMAIL"))
                            # await context.bot.send_message(job.chat_id, text=f"Posto prenotato per {persona_richiesta.name} in data {day.date} ({turno.name})")
                    else: # avvisa ugualmente se il posto c'è ma non nel turno richiesto
                        await context.bot.send_message(job.chat_id, text=messaggio_posto_libero.strip())

                #  aggiornamento disponibilità precedente
                if turno == Turno.MATTINO:
                    day.prev_disp_morning = current_disp
                else:
                    day.prev_disp_noon = current_disp
            
    print("\n\n-------------\n\n")


async def delete_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    current_jobs = context.job_queue.get_jobs_by_name(str(context._chat_id))
    if current_jobs:
        for job in current_jobs:
            job.schedule_removal()
            logger.info(f"Deleted job: {job.name}")
            await context.bot.send_message(job.chat_id, text=f"Deleted job: {job.name}")
    else:
        await context.bot.send_message(update.effective_message.chat_id, text=f"No jobs active")
    current_jobs = context.job_queue.get_jobs_by_name(str(context._chat_id))
    logger.info(f"Current jobs: {current_jobs}")


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


def run_bot() -> None:
    """Run bot."""
    
    
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELE_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("deletejobs", delete_jobs))
    application.add_handler(CommandHandler("showdates", show_dates))
    application.add_handler(CallbackQueryHandler(select_person, pattern="^select_person_"))
    application.add_handler(CallbackQueryHandler(select_shift, pattern="^select_shift_"))
    application.add_handler(CallbackQueryHandler(select_date, pattern="^select_date_"))
    application.add_handler(CommandHandler("notifyday", start_notify_on_days))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


run_bot()