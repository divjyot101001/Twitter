import telebot
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.chrome.options import Options
import random
import string
import time

# Replace with your Telegram bot token
TOKEN = '8019263869:AAEL67NjDyOe15FaVpwG-4leuCWyFNZApx0'

bot = telebot.TeleBot(TOKEN)

user_data = {}

def generate_random_name():
    return ''.join(random.choices(string.ascii_letters, k=random.randint(5, 10)))

def generate_random_password():
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choices(chars, k=12))

def generate_random_username():
    return 'user_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

def generate_dob():
    year = random.randint(1980, 1999)
    month = random.randint(1, 12)
    day = random.randint(1, 28)  # Safe for all months
    return month, day, year

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Please provide the email for the new Twitter account.")
    user_data[chat_id] = {'state': 'waiting_email'}

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        return

    state = user_data[chat_id]['state']

    if state == 'waiting_email':
        email = message.text.strip()
        user_data[chat_id]['email'] = email
        bot.send_message(chat_id, "Starting Twitter account creation...")

        # Set up headless Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)
        user_data[chat_id]['driver'] = driver

        try:
            driver.get("https://x.com/i/flow/signup")
            wait = WebDriverWait(driver, 30)

            # Enter name
            name_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="ocf_SignupNameInput"]')))
            random_name = generate_random_name()
            name_input.send_keys(random_name)

            # Click "Use email instead"
            use_email_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="ocf_SignupUseEmailLink"]')))
            use_email_link.click()

            # Enter email
            email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="ocf_SignupEmailInput"]')))
            email_input.send_keys(email)

            # Select DOB
            month, day, year = generate_dob()
            month_select = Select(wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="ocf_SignupBirthMonthSelect"]'))))
            month_select.select_by_value(str(month))

            day_select = Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="ocf_SignupBirthDaySelect"]'))
            day_select.select_by_value(str(day))

            year_select = Select(driver.find_element(By.CSS_SELECTOR, '[data-testid="ocf_SignupBirthYearSelect"]'))
            year_select.select_by_value(str(year))

            # Click Next
            next_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="ocf_SignupNextButton"]')))
            next_button.click()

            # Click Next on the next screen (customization)
            next_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="ocf_SignupNextButton"]')))
            next_button.click()

            # Click Sign up
            signup_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="ocf_SignupSubmitButton"]')))
            signup_button.click()

            # Now wait for OTP screen
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="ocf_SignupVerificationCodeInput"]')))

            bot.send_message(chat_id, "Please provide the OTP sent to your email.")
            user_data[chat_id]['state'] = 'waiting_otp'

        except Exception as e:
            bot.send_message(chat_id, f"An error occurred: {str(e)}")
            driver.quit()
            del user_data[chat_id]

    elif state == 'waiting_otp':
        otp = message.text.strip()
        driver = user_data[chat_id]['driver']
        wait = WebDriverWait(driver, 30)

        try:
            code_input = driver.find_element(By.CSS_SELECTOR, '[data-testid="ocf_SignupVerificationCodeInput"]')
            code_input.send_keys(otp)

            next_button = driver.find_element(By.CSS_SELECTOR, '[data-testid="ocf_SignupVerificationNextButton"]')
            next_button.click()

            # Set password
            password = generate_random_password()
            user_data[chat_id]['password'] = password
            password_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="ocf_SignupCreatePasswordInput"]')))
            password_input.send_keys(password)

            next_button = driver.find_element(By.CSS_SELECTOR, '[data-testid="ocf_SignupCreatePasswordNextButton"]')
            next_button.click()

            # Set username
            username = generate_random_username()
            username_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="ocf_UsernameInput"]')))
            username_input.clear()
            username_input.send_keys(username)

            next_button = driver.find_element(By.CSS_SELECTOR, '[data-testid="ocf_UsernameNextButton"]')
            next_button.click()

            # Skip additional steps if any (e.g., profile pic, bio)
            time.sleep(5)  # Wait for completion
            try:
                skip_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="ocf_SkipButton"]')))
                skip_button.click()
                time.sleep(2)
            except:
                pass

            # Account created
            bot.send_message(chat_id, f"Account created successfully!\nUsername: @{username}\nPassword: {password}")

            driver.quit()
            del user_data[chat_id]

        except Exception as e:
            bot.send_message(chat_id, f"An error occurred: {str(e)}")
            driver.quit()
            del user_data[chat_id]

if __name__ == '__main__':
    bot.polling()