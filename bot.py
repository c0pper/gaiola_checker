import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from pyvirtualdisplay import Display
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from datetime import datetime, timedelta
from time import sleep
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv


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

display = Display(visible=0, size=(1366, 768))
display.start()

opts = webdriver.ChromeOptions()
opts.add_argument('--no-sandbox')
opts.add_argument('--disable-dev-shm-usage')
driver = webdriver.Firefox(service=FirefoxService(executable_path="geckodriver"))
# driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=opts)
# driver = webdriver.Chrome(options=opts)

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
        if check_job_exists(str(chat_id), context):
            await update.effective_message.reply_text("Bot già avviato")
        else:
            context.job_queue.run_repeating(check_availability, interval=20, first=5, name=str(chat_id), chat_id=chat_id)
            text = f"Bot avviato."
            await update.effective_message.reply_text(text)


async def check_availability(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the alarm message."""
    job = context.job

    bottoni_data = driver.find_elements(By.CLASS_NAME, "bottoni_data_904")
    bottoni_data_validi = [btn for btn in bottoni_data if 'btn-danger' not in btn.get_attribute('class').split(' ')]
    
    while "days" not in globals():
        print("creating days list")
        global days 
        days = [Day(btn.text, btn, idx, datetime.strptime(btn.text, "%d/%m/%Y").strftime("%A"), 0, 0, 0, 0) for idx, btn in enumerate(bottoni_data_validi)]
    # [print(day) for day in days]

    if days[-1].date not in get_dates_of_current_week():  # è una nuova settimana 
        print("New week detected, refreshing page")
        driver.refresh()
        bottoni_data = driver.find_elements(By.CLASS_NAME, "bottoni_data_904")
        bottoni_data_validi = [btn for btn in bottoni_data if 'btn-danger' not in btn.get_attribute('class').split(' ')]
        days = [Day(btn.text, btn, idx, datetime.strptime(btn.text, "%d/%m/%Y").strftime("%A"), 0, 0, 0, 0) for idx, btn in enumerate(bottoni_data_validi)]

    for day in days:
        print(f"Checking {day.day_name} {day.date}")
        driver.execute_script("arguments[0].scrollIntoView(true);", day.button)
        day.button.click()
        turns = driver.find_elements(By.NAME, 'turno')
        for idx, e in enumerate(turns):
            e.click()
            sleep(0.1)
            alert_posti = driver.find_element(By.ID, "disponibilita_effettiva")
            if idx == 0:
                turno = "mattino"
                day.new_disp_morning = int(alert_posti.text[-1])
                print(f"* Posti {turno}: {str(day.new_disp_morning)} (originale: {day.prev_disp_morning})")
                if day.prev_disp_morning == 0 and day.new_disp_morning != 0:
                    messaggio_posto_libero = f"Posto liberato {day.day_name} {day.date} {turno}\nPrenota: https://www.areamarinaprotettagaiola.it/prenotazione"
                    print(messaggio_posto_libero)
                    await context.bot.send_message(job.chat_id, text=messaggio_posto_libero)
                day.prev_disp_morning = day.new_disp_morning
            else:
                turno = "pomeriggio"
                day.new_disp_noon = int(alert_posti.text[-1])
                print(f"* Posti {turno}: {str(day.new_disp_noon)} (originale: {day.prev_disp_noon})")
                if day.prev_disp_noon == 0 and day.new_disp_noon != 0:
                    messaggio_posto_libero = f"Posto liberato {day.day_name} {day.date} {turno}\nPrenota: https://www.areamarinaprotettagaiola.it/prenotazione"
                    print(messaggio_posto_libero)
                    await context.bot.send_message(job.chat_id, text=messaggio_posto_libero)
                day.prev_disp_noon = day.new_disp_noon
            
    print("-------------\n\n")


def run_bot() -> None:
    """Run bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELE_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


run_bot()