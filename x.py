import asyncio
import random
import string
import time
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.handlers import MessageHandler
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Placeholders for your API ID, API Hash, and 2Captcha API Key
api_id = 26973152  # Replace with your API ID
api_hash = "3359532bba54756f12424148064e3e4d"  # Replace with your API Hash
two_captcha_key = "a25a82134f896a53a65698212377c022"  # Replace with your 2Captcha API key

app = Client("my_account", api_id=api_id, api_hash=api_hash)

mail_bot_username = "@fakemailbot"
mail_chat_id = None

async def get_mail_chat_id():
    global mail_chat_id
    if not mail_chat_id:
        chat = await app.get_chat(mail_bot_username)
        mail_chat_id = chat.id
    return mail_chat_id

def generate_random_name():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

def generate_random_dob():
    year = random.randint(1986, 2003)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return month, day, year

def generate_random_password():
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choices(chars, k=12))  # Stronger password

def generate_random_username():
    return 'user' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

def solve_arkose(sitekey, pageurl):
    data = {
        'key': two_captcha_key,
        'method': 'funcaptcha',
        'publickey': sitekey,
        'pageurl': pageurl,
        'json': 1,
        'surl': 'https://client-api.arkoselabs.com'  # Default for Arkose
    }
    response = requests.post('http://2captcha.com/in.php', data=data).json()
    if response.get('status') != 1:
        return None
    req_id = response['request']
    while True:
        time.sleep(10)
        res = requests.get(f'http://2captcha.com/res.php?key={two_captcha_key}&action=get&id={req_id}&json=1').json()
        if res.get('status') == 1:
            return res['request']
        if 'ERROR' in res.get('request', ''):
            return None

@app.on_message(filters.command("start") & filters.private)
async def start(client: Client, message: Message):
    await message.reply_text(
        "Welcome! This bot creates fresh X accounts.\n"
        "Commands:\n"
        "/start - Show this message\n"
        "/create - Create a new X account"
    )

@app.on_message(filters.command("create") & filters.private)
async def create_account(client: Client, message: Message):
    user_id = message.from_user.id
    await message.reply_text("Starting account creation process...")

    # Interact with fake mail bot
    mail_chat = await get_mail_chat_id()
    
    # Send /generate
    await client.send_message(mail_chat, "/generate")
    await client.send_message(user_id, "Sent /generate to @fakemailbot")

    # Queue for messages from mail bot
    queue = asyncio.Queue()
    async def mail_handler(cl, msg: Message):
        await queue.put(msg)

    handler = app.add_handler(MessageHandler(mail_handler, filters=filters.chat(mail_chat)))

    try:
        # Wait for message with inline buttons
        inline_msg = await queue.get()
        if inline_msg.reply_markup and inline_msg.reply_markup.inline_keyboard:
            # Select random option (assuming 2 options)
            button_index = random.randint(0, len(inline_msg.reply_markup.inline_keyboard) - 1)
            await inline_msg.click(button_index)
            await client.send_message(user_id, f"Selected random domain option {button_index + 1}")
        else:
            await client.send_message(user_id, "No inline buttons found.")
            return

        # Wait for email message
        email_msg = await queue.get()
        email_text = email_msg.text
        if "Your new fakemail address is" in email_text:
            email = email_text.split("Your new fakemail address is ")[1].split("\n")[0].strip()
            await client.send_message(user_id, f"Generated email: {email}")
        else:
            await client.send_message(user_id, "Failed to get email.")
            return

        # Send /id and consume the response
        await client.send_message(mail_chat, "/id")
        await client.send_message(user_id, "Sent /id to @fakemailbot")
        id_msg = await queue.get()  # Consume /id response
        await client.send_message(user_id, "Received /id response.")

        # Now start undetected Chrome for X signup
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = uc.Chrome(options=options, use_subprocess=True)
        wait = WebDriverWait(driver, 20)

        try:
            driver.get("https://x.com/i/flow/signup")
            await client.send_message(user_id, "Opened X signup page.")

            # Enter name
            random_name = generate_random_name()
            name_input = wait.until(EC.presence_of_element_located((By.NAME, "name")))
            name_input.send_keys(random_name)
            await client.send_message(user_id, f"Entered name: {random_name}")

            # Enter email
            email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
            email_input.send_keys(email)
            await client.send_message(user_id, f"Entered email: {email}")

            # Enter DOB
            month, day, year = generate_random_dob()
            month_select = driver.find_element(By.ID, "SELECTOR_1")
            month_select.send_keys(str(month))
            day_select = driver.find_element(By.ID, "SELECTOR_2")
            day_select.send_keys(str(day))
            year_select = driver.find_element(By.ID, "SELECTOR_3")
            year_select.send_keys(str(year))
            await client.send_message(user_id, f"Entered DOB: {month}/{day}/{year}")

            # Click Next
            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="Next"]/ancestor::div[@role="button"]')))
            next_button.click()
            await client.send_message(user_id, "Clicked Next.")

            # Customize experience Next
            try:
                next_customize = wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="Next"]/ancestor::div[@role="button"]')))
                next_customize.click()
                await client.send_message(user_id, "Clicked Next on customize.")
            except TimeoutException:
                pass

            # Click Sign up
            signup_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="Sign up"]/ancestor::div[@role="button"]')))
            signup_button.click()
            await client.send_message(user_id, "Clicked Sign up. Waiting for OTP...")

            # Check for Captcha
            try:
                arkose_div = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-apikey]')))
                sitekey = arkose_div.get_attribute('data-apikey')
                await client.send_message(user_id, "Captcha detected. Solving...")
                token = solve_arkose(sitekey, driver.current_url)
                if token:
                    driver.execute_script(f'document.getElementById("enforcementToken").value = "{token}";')
                    # Assuming the token input id, may need adjustment
                    # Re-click signup or submit
                    signup_button.click()
                    await client.send_message(user_id, "Captcha solved and submitted.")
                else:
                    await client.send_message(user_id, "Failed to solve captcha.")
                    return
            except TimeoutException:
                await client.send_message(user_id, "No captcha detected.")

            # Wait for OTP message from mail bot
            time.sleep(5)  # Give time for email to arrive
            otp_msg = await queue.get()
            otp_text = otp_msg.text
            if "Please enter this verification code to get started on X:" in otp_text:
                lines = otp_text.split("\n")
                for i, line in enumerate(lines):
                    if "Please enter this verification code to get started on X:" in line:
                        otp = lines[i+1].strip()
                        if len(otp) == 6 and otp.isdigit():
                            await client.send_message(user_id, f"Received OTP: {otp}")
                            break
                else:
                    await client.send_message(user_id, "Invalid OTP format.")
                    return
            else:
                await client.send_message(user_id, "No OTP found in message.")
                return

            # Enter OTP
            otp_input = wait.until(EC.presence_of_element_located((By.NAME, "code")))
            otp_input.send_keys(otp)
            await client.send_message(user_id, "Entered OTP.")

            # Click Next/Verify
            verify_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "Next") or contains(text(), "Verify")]/ancestor::div[@role="button"]')))
            verify_button.click()
            await client.send_message(user_id, "Clicked Verify/Next.")

            # Enter password
            random_pass = generate_random_password()
            password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
            password_input.send_keys(random_pass)
            await client.send_message(user_id, f"Entered password: {random_pass}")

            # Click Next
            next_pass_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="Next"]/ancestor::div[@role="button"]')))
            next_pass_button.click()
            await client.send_message(user_id, "Clicked Next after password.")

            # Optionally set username if prompted
            try:
                username_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
                random_username = generate_random_username()
                username_input.send_keys(random_username)
                await client.send_message(user_id, f"Entered username: @{random_username}")
                next_username = wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="Next"]/ancestor::div[@role="button"]')))
                next_username.click()
                await client.send_message(user_id, "Clicked Next after username.")
            except TimeoutException:
                await client.send_message(user_id, "No username prompt, proceeding.")

            # Close browser
            driver.quit()
            await client.send_message(user_id, f"Account created successfully! Email: {email}\nPassword: {random_pass}\nLogin to set further details if needed.")

        except Exception as e:
            await client.send_message(user_id, f"Error during account creation: {str(e)}")
            driver.quit()

    finally:
        app.remove_handler(handler)

if __name__ == "__main__":
    app.run()