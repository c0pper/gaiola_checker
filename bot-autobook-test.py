import os
from datetime import datetime, timedelta, date
from time import sleep
from dataclasses import dataclass
import logging
from enum import Enum
from selenium import webdriver
from selenium.webdriver.common.by import By
from pyvirtualdisplay import Display
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
from data import people, EMAIL, TEL


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

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


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
    print(f"{user_id} started the task")
    print(os.getenv("MY_ID"))
    if user_id != str(os.getenv("MY_ID")):
        await update.effective_message.reply_text("Non dovresti essere qui...")
    else:
        if len(context.args) >= 2:
            data_richiesta = context.args[0]
            turno_richiesto = context.args[1].lower()
            people_input = context.args[2].lower().split(",")
            selected_people = [person for person in people if person.name.lower().split()[0] in people_input]
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
                            "turn": turno_richiesto,
                            "selected_people": selected_people
                        }
                    )
                text = f"Bot avviato. Ricerca data: {data_richiesta} {turno_richiesto}"
        else:
            text = "Scrivi la data e il turno desiderato separati da spazi (/start 01/01/2000 M/P)"
        await update.effective_message.reply_text(text)




async def remove_job_if_exists(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    chat_id = update.effective_message.chat_id
    current_jobs = context.job_queue.get_jobs_by_name(chat_id)
    print(f"Current jobs = {current_jobs}")
    if not current_jobs:
        text = f"Nessun task da rimuovere"
        return False
    for job in current_jobs:
        job.schedule_removal()
        text = f"Rimossi task {chat_id}"
    await context.bot.send_message(job.chat_id, text=text)
    return True



def get_days_list():
    bottoni_data = driver.find_elements(By.CLASS_NAME, "bottoni_data_904")
    bottoni_data_validi = [btn for btn in bottoni_data if 'btn-danger' not in btn.get_attribute('class').split(' ')]
    days = [Day(btn.text, btn, idx, datetime.strptime(btn.text, "%d/%m/%Y").strftime("%A"), 0, 0, 0, 0) for idx, btn in enumerate(bottoni_data_validi)]
    return days


def book(selected_people: list):
    #  clicca prenota
    driver.find_element(By.ID, "CheckAvailability_904").click()
    sleep(1)
    for idx, p in enumerate(selected_people):
        idx += 1
        nome = driver.find_element(By.ID, f"nome_{idx}")
        driver.execute_script("arguments[0].scrollIntoView(true);", nome)
        nome.send_keys(p.name)

        cognome = driver.find_element(By.ID, f"cognome_{idx}")
        driver.execute_script("arguments[0].scrollIntoView(true);", cognome)
        cognome.send_keys(p.surname)

        sex = driver.find_element(By.ID, f"sesso_{idx}")
        driver.execute_script("arguments[0].scrollIntoView(true);", sex)
        sex.send_keys(p.sex)

        data_nascita = driver.find_element(By.ID, f"data_nascita_{idx}")
        driver.execute_script("arguments[0].scrollIntoView(true);", data_nascita)
        data_nascita.send_keys(p.bday)

        comune_nascita = driver.find_element(By.CSS_SELECTOR, f"[aria-labelledby=select2-comune_nascita_{idx}-container]")
        driver.execute_script("arguments[0].scrollIntoView(true);", comune_nascita)
        comune_nascita.click()
        comune_nascita.send_keys("NAPOLI")
        for _ in range(5):
            comune_nascita.send_keys(Keys.ARROW_DOWN)
        comune_nascita.send_keys(Keys.RETURN)

        cf = driver.find_element(By.ID, f"codice_fiscale_{idx}")
        driver.execute_script("arguments[0].scrollIntoView(true);", comune_nascita)
        cf.send_keys(p.cf)

        email = driver.find_element(By.ID, f"email_{idx}")
        driver.execute_script("arguments[0].scrollIntoView(true);", email)
        email.send_keys(EMAIL)

        comune_residenza = driver.find_element(By.CSS_SELECTOR, f"[aria-labelledby=select2-comune_residenza_{idx}-container]")
        driver.execute_script("arguments[0].scrollIntoView(true);", comune_residenza)
        comune_residenza.click()
        comune_residenza.send_keys("NAPOLI")
        for _ in range(5):
            comune_residenza.send_keys(Keys.ARROW_DOWN)
        comune_residenza.send_keys(Keys.RETURN)

        municipalita = driver.find_element(By.ID, f"select2-municipalita_{idx}-container")
        driver.execute_script("arguments[0].scrollIntoView(true);", municipalita)
        municipalita.click()
        municipalita_txt_field = driver.find_element(By.CLASS_NAME, "select2-search__field")
        municipalita_txt_field.send_keys("muni")
        municipalita_txt_field.send_keys(Keys.RETURN)

    email_main = driver.find_element(By.ID, "email_main")
    driver.execute_script("arguments[0].scrollIntoView(true);", email_main)
    email_main.send_keys(EMAIL)

    email_main2 = driver.find_element(By.ID, "email_main2")
    driver.execute_script("arguments[0].scrollIntoView(true);", email_main2)
    email_main2.send_keys(EMAIL)

    telefono = driver.find_element(By.ID, "telefono")
    driver.execute_script("arguments[0].scrollIntoView(true);", telefono)
    telefono.send_keys(TEL)

    privacy = driver.find_element(By.ID, "privacy")
    driver.execute_script("arguments[0].scrollIntoView(true);", privacy)
    privacy.click()

    regolamento = driver.find_element(By.ID, "regolamento")
    driver.execute_script("arguments[0].scrollIntoView(true);", regolamento)
    regolamento.click()

    prenota_btn = driver.find_element(By.ID, "ConfermaPrenotazione")
    prenota_btn.click()


async def check_availability(context: ContextTypes.DEFAULT_TYPE) -> None:   
    """Send the alarm message."""
    global days
    global last_iteration_day
    job = context.job
    data_richiesta = job.data['date']
    turno_richiesto = Turno.MATTINO if job.data['turn'] == "m" else Turno.POMERIGGIO
    print(f"Data richiesta: {data_richiesta} Turno: {turno_richiesto}")

    current_day = date.today()
    print(current_day, last_iteration_day)
    if last_iteration_day and last_iteration_day != current_day: # se è un nuovo giorno refreshiamo la pagina
        print("New day, refreshing page")
        driver.refresh()
        days = get_days_list()
    else:
        days = get_days_list()
        
    last_iteration_day = current_day
    
    while not days:  # è il primo ciclo dopo l'avvio
        print("creating days list")
        days = get_days_list()
    [print(f"-- {day}") for day in days]

    if days[-1].date not in get_dates_of_current_week():  # è una nuova settimana 
        print("\nNew week detected, refreshing page\n")
        driver.refresh()
        days = get_days_list()
        [print(f"-- {day}") for day in days]

    for day in days:
        if day.date == data_richiesta:
            print(f"Checking {day.day_name} {day.date}")
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

            #  aggiornamento disponibilità precedente
            if turno_richiesto == Turno.MATTINO:
                day.prev_disp_morning = current_disp
            else:
                day.prev_disp_noon = current_disp
            
            print(f"* Posti {turno_richiesto.value.lower()}: {str(current_disp)} (originale: {prev_disp})")
            if prev_disp == 0 and current_disp != 0:
                messaggio_posto_libero = f"Posto liberato {day.day_name} {day.date} {turno_richiesto.value}\nPrenota: https://www.areamarinaprotettagaiola.it/prenotazione"
                print(messaggio_posto_libero)
                await context.bot.send_message(job.chat_id, text=messaggio_posto_libero)
                book()

            
    print("-------------\n\n")


def run_bot() -> None:
    """Run bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELE_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", remove_job_if_exists))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


run_bot()