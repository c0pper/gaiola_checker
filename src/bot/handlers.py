# src/bot/handlers.py
import logging
import os
from datetime import date
from time import sleep
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackContext

from src.gaiola.scraper import GaiolaScraper
from src.gaiola.models import Turno
from src.data.people_data import all_people
from src.utils.helpers import find_code_by_name, delete_booking_file

logger = logging.getLogger(__name__)

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /start command. Initiates the booking process by asking for a person.
    Only accessible by the configured MY_ID.
    """
    chat_id = update.effective_message.chat_id
    user_id = str(update.effective_user.id)
    user_name = update.message.from_user.name if update.message else "Unknown User"
    
    config = context.bot_data['config']
    scraper: GaiolaScraper = context.bot_data['scraper']

    logger.info(f"{user_name} started the task (User ID: {user_id}, My ID: {config.MY_ID})")
    
    if user_id != config.MY_ID:
        await update.effective_message.reply_text("Non dovresti essere qui...")
        return

    # Check if a job for this chat_id already exists
    # Note: Job names are unique. If using chat_id as name, only one job per chat is allowed.
    # If multiple concurrent bookings for different people from the same chat are desired,
    # job names need to be more specific (e.g., f"{chat_id}_{person_name}_{date_str}").
    # For now, assuming one active job per chat.
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    if current_jobs:
        await update.effective_message.reply_text("Bot già avviato. Per avviare una nuova ricerca, prima cancella il task corrente con /deletejobs.")
        return

    # Ensure scraper is on the correct page and has fresh data
    if "booking" not in scraper.driver.current_url:
        scraper.open_bookings_page()
    scraper.days = scraper.get_days_list() # Refresh available days

    keyboard = [
        [InlineKeyboardButton(p.name, callback_data=f"select_person_{p.name}")] for p in all_people
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)    
    await update.effective_message.reply_text("Seleziona la persona:", reply_markup=reply_markup)

async def show_dates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Shows the available dates from the scraper.
    """
    scraper: GaiolaScraper = context.bot_data['scraper']
    
    # Ensure scraper has the latest dates
    if "booking" not in scraper.driver.current_url:
        scraper.open_bookings_page()
    scraper.days = scraper.get_days_list()

    if scraper.days:
        nl = "\n"
        available_dates_str = nl.join([d.date for d in scraper.days])
        await update.effective_message.reply_text(f"Date disponibili:\n{available_dates_str}")
    else:
        await update.effective_message.reply_text("Nessuna data disponibile al momento.")


async def delete_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Deletes all active jobs for the current chat.
    """
    chat_id = update.effective_message.chat_id
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id)) # Get jobs specific to this chat_id

    if current_jobs:
        job_names = []
        for job in current_jobs:
            job_names.append(job.name)
            job.schedule_removal()
            logger.info(f"Deleted job: {job.name}")
        job_names_str ='\n'.join(job_names)
        await context.bot.send_message(chat_id, text="Rimossi i seguenti task:\n" + job_names_str)
    else:
        await context.bot.send_message(chat_id, text="Nessun task attivo da rimuovere.")
    
    # Also check all jobs in the queue (for debugging/overview)
    all_jobs_in_queue = context.job_queue.jobs()
    logger.info(f"Current jobs in queue after deletion: {[j.name for j in all_jobs_in_queue]}")


async def delete_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Initiates the process to delete a booking by presenting a list of saved bookings.
    """
    bookings_dir = "bookings"
    if not os.path.exists(bookings_dir):
        await update.effective_message.reply_text("La cartella 'bookings' non esiste o non contiene prenotazioni.")
        return

    bookings = [f for f in os.listdir(bookings_dir) if f.endswith(".json")]
    
    if bookings:
        keyboard = []
        for booking_file in bookings:
            try:
                # Extract name from filename (e.g., "mario_rossi_CODE.json" -> "mario_rossi")
                # Then try to map it back to a Person object for full name
                parts = booking_file.replace(".json", "").split("_")
                person_name_from_file = " ".join(parts[:-1]).replace("_", " ") # Reconstruct name, e.g., "mario rossi"
                code_from_file = parts[-1]

                # Find the actual Person object to display full name
                person_obj = next((p for p in all_people if p.name.lower() == person_name_from_file.lower()), None)
                display_name = person_obj.name if person_obj else person_name_from_file.title() # Fallback to title case

                keyboard.append([InlineKeyboardButton(f"{display_name} (Code: {code_from_file})", callback_data=f"select_person_to_delete_{person_name_from_file}_{code_from_file}")])
            except Exception as e:
                logger.warning(f"Could not parse booking file {booking_file}: {e}")
                keyboard.append([InlineKeyboardButton(booking_file.replace(".json", ""), callback_data=f"select_person_to_delete_error_{booking_file}")])

        reply_markup = InlineKeyboardMarkup(keyboard)    
        await update.effective_message.reply_text("Seleziona la prenotazione da eliminare:", reply_markup=reply_markup)
    else:
        await update.effective_message.reply_text("Nessuna prenotazione salvata da cancellare.")

async def show_current_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Shows all currently active jobs in the queue.
    """
    current_jobs = context.job_queue.jobs()
    if current_jobs:
        jobs_info = []
        for job in current_jobs:
            jobs_info.append(f"Task: {job.name} (Next run: {job.next_run_time.strftime('%H:%M:%S') if job.next_run_time else 'N/A'})")
        jobs_str = "\n".join(jobs_info)
        await update.effective_message.reply_text(f"Task attivi:\n{jobs_str}")
    else:
        await update.effective_message.reply_text("Nessun task attivo.")

# --- Callback Query Handlers ---

async def select_person(update: Update, context: CallbackContext) -> None:
    """
    Handles the callback when a person is selected for booking.
    """
    query = update.callback_query
    await query.answer()

    selected_person_name = query.data.split('_')[-1]
    selected_person = next((p for p in all_people if p.name == selected_person_name), None)

    if not selected_person:
        await query.edit_message_text("Errore: Persona non trovata.")
        return

    context.user_data['selected_person'] = selected_person
    
    keyboard = [
        [InlineKeyboardButton("Mattina", callback_data="select_shift_m")],
        [InlineKeyboardButton("Pomeriggio", callback_data="select_shift_p")],
        [InlineKeyboardButton("Entrambi", callback_data="select_shift_mp")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(f"Persona selezionata:\n{context.user_data['selected_person'].name}\n\nSeleziona il turno:", reply_markup=reply_markup)

async def select_shift(update: Update, context: CallbackContext) -> None:
    """
    Handles the callback when a shift (morning/afternoon/both) is selected.
    """
    query = update.callback_query
    await query.answer()
    
    selected_shift_code = query.data.split('_')[-1]
    selected_shifts = []
    if "m" in selected_shift_code:
        selected_shifts.append(Turno.MATTINO)
    if "p" in selected_shift_code:
        selected_shifts.append(Turno.POMERIGGIO)
    
    context.user_data['selected_shift'] = selected_shifts
    
    scraper: GaiolaScraper = context.bot_data['scraper']
    # Ensure scraper has the latest dates before presenting them
    if "booking" not in scraper.driver.current_url:
        scraper.open_bookings_page()
    scraper.days = scraper.get_days_list()

    keyboard = [
        [InlineKeyboardButton(d.date, callback_data=f"select_date_{d.date}")] for d in scraper.days
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    shift_names = [t.value for t in selected_shifts]
    await query.edit_message_text(f"Turno selezionato:\n{', '.join(shift_names)}\n\nSeleziona la data:", reply_markup=reply_markup)

async def select_date(update: Update, context: CallbackContext) -> None:
    """
    Handles the callback when a date is selected.
    This is the final step before scheduling the availability check job.
    """
    query = update.callback_query
    await query.answer()
    
    selected_date = query.data.split('_')[-1]
    context.user_data['selected_date'] = selected_date
    
    persona_richiesta = context.user_data.get('selected_person')
    turno_richiesto = context.user_data.get('selected_shift')
    
    if not persona_richiesta or not turno_richiesto:
        await query.edit_message_text("Errore: Riprova la selezione (persona o turno mancante).")
        return

    chat_id = update.effective_message.chat_id
    scraper: GaiolaScraper = context.bot_data['scraper']

    job_name = f"{update.effective_chat.username} booking for {persona_richiesta.name} on {selected_date} - {','.join([t.name for t in turno_richiesto])}"
    
    # Schedule the job to check availability
    context.job_queue.run_repeating(
        scraper.check_availability, # This is the method to call
        interval=scraper.config.CHECK_INTERVAL, # Check every 30 seconds
        first=5, # First run after 5 seconds
        name=str(chat_id), # Use chat_id as job name for easy management (one job per chat)
        chat_id=chat_id,
        data={
            "persona_richiesta": persona_richiesta,
            "date_richieste": [selected_date], # Pass as a list for consistency with scraper logic
            "turno_richiesto": turno_richiesto
        },
        # Pass send_message_func to the job data so check_availability can use it
        # This is a workaround as job_queue doesn't directly pass bot context to job function
        # A better way is to bind the method to the scraper instance which has access to context.bot
        # For simplicity, passing the function directly here.
        # Alternatively, make check_availability a standalone function that takes scraper and context.
        # For this refactor, I've made check_availability a method of GaiolaScraper that takes send_message_func.
        # job_kwargs={'send_message_func': context.bot.send_message}
    )
    
    text = (f"Bot avviato. Ricerca posti per {persona_richiesta.name} {persona_richiesta.surname} "
            f"in data {selected_date} turno {' / '.join([t.value for t in turno_richiesto])}.\n"
            f"Il task si chiama: '{job_name}'")
    await query.edit_message_text(text)


async def select_person_to_delete(update: Update, context: CallbackContext) -> None:
    """
    Handles the callback when a booking is selected for deletion.
    """
    query = update.callback_query
    await query.answer()

    # Data format: select_person_to_delete_{person_name_from_file}_{code_from_file}
    parts = query.data.split('_')
    if len(parts) < 4: # Error case or malformed data
        await query.edit_message_text("Errore: Dati di cancellazione non validi.")
        return

    person_name_from_file = parts[3] # This is the lowercased name from the filename
    booking_code = parts[4] # This is the code from the filename

    # Find the actual Person object to get CF
    person_list = [p for p in all_people if p.name.lower() == person_name_from_file.lower()]

    if not person_list:
        await query.edit_message_text(f"Errore: Persona '{person_name_from_file}' non trovata nella lista delle persone.")
        return
    
    person_obj = person_list[0]
    
    scraper: GaiolaScraper = context.bot_data['scraper']
    
    try:
        cancellation_url = f"https://booking.areamarinaprotettagaiola.it/booking/prenotazione_cancella.php?action=2&id={booking_code}&cf={person_obj.cf}"
        logger.info(f"Attempting to cancel booking via URL: {cancellation_url}")
        
        scraper.driver.get(cancellation_url)
        # Check for success message on the page if possible, or rely on file deletion
        sleep(2) # Give time for cancellation to process

        delete_status = delete_booking_file(person_obj.name, booking_code)
        
        if delete_status:
            await query.edit_message_text(f"Prenotazione per {person_obj.name} (Codice: {booking_code}) cancellata con successo.")
        else:
            await query.edit_message_text(f"Errore nella cancellazione della prenotazione per {person_obj.name} (Codice: {booking_code}). Il file potrebbe non essere stato trovato o eliminato.")
    except Exception as e:
        logger.error(f"Error during booking cancellation for {person_obj.name}: {e}")
        await query.edit_message_text(f"Si è verificato un errore durante la cancellazione della prenotazione per {person_obj.name}: {e}")

