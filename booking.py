from time import sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

def book(driver, selected_people: list, email):
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
        email.send_keys(email)

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
    email_main.send_keys(email)

    email_main2 = driver.find_element(By.ID, "email_main2")
    driver.execute_script("arguments[0].scrollIntoView(true);", email_main2)
    email_main2.send_keys(email)

    telefono = driver.find_element(By.ID, "telefono")
    driver.execute_script("arguments[0].scrollIntoView(true);", telefono)
    telefono.send_keys("3334445566")

    privacy = driver.find_element(By.ID, "privacy")
    driver.execute_script("arguments[0].scrollIntoView(true);", privacy)
    privacy.click()

    regolamento = driver.find_element(By.ID, "regolamento")
    driver.execute_script("arguments[0].scrollIntoView(true);", regolamento)
    regolamento.click()

    prenota_btn = driver.find_element(By.ID, "ConfermaPrenotazione")
    prenota_btn.click()