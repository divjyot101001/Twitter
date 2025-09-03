import asyncio
import random
import string
import time
import requests
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.handlers import MessageHandler
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import os

# ───── CONFIG ─────
api_id = 26973152
api_hash = "3359532bba54756f12424148064e3e4d"
bot_token = "8019263869:AAEL67NjDyOe15FaVpwG-4leuCWyFNZApx0"
two_captcha_key = "a25a82134f896a53a65698212377c022"

mail_bot_username = "@fakemailbot"
mail_chat_id = None

# ───── CLIENTS ─────
user_client = Client("user_session", api_id=api_id, api_hash=api_hash)
bot_client = Client("bot_session", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# ───── HELPERS ─────
async def get_mail_chat_id():
    global mail_chat_id
    if not mail_chat_id:
        chat = await user_client.get_chat(mail_bot_username)
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
    return ''.join(random.choices(chars, k=12))

def generate_random_username():
    return 'user' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

def solve_arkose(sitekey, pageurl):
    data = {
        'key': two_captcha_key,
        'method': 'funcaptcha',
        'publickey': sitekey,
        'pageurl': pageurl,
        'json': 1,
        'surl': 'https://client-api.arkoselabs.com'
    }
    response = requests.post('http://2captcha.com/in.php', data=data).json()
    if response.get('status') != 1:
        return None
    req_id = response['request']
    while True:
        time.sleep(10)
        res = requests.get(
            f'http://2captcha.com/res.php?key={two_captcha_key}&action=get&id={req_id}&json=1'
        ).json()
        if res.get('status') == 1:
            return res['request']
        if 'ERROR' in res.get('request', ''):
            return None

# ───── BOT COMMANDS ─────
@bot_client.on_message(filters.command("start") & filters.private)
async def start(client: Client, message: Message):
    await message.reply_text(
        "Welcome! This bot creates fresh X accounts.\n\n"
        "Commands:\n"
        "/start - Show this message\n"
        "/create - Create a new X account"
    )

@bot_client.on_message(filters.command("create") & filters.private)
async def create_account(client: Client, message: Message):
    user_id = message.from_user.id
    await bot_client.send_message(user_id, "🚀 Starting account creation...")

    mail_chat = await get_mail_chat_id()
    await user_client.send_message(mail_chat, "/generate")
    await bot_client.send_message(user_id, "Sent /generate to @fakemailbot")

    queue = asyncio.Queue()

    async def mail_handler(cl, msg: Message):
        await queue.put(msg)

    handler = user_client.add_handler(MessageHandler(mail_handler, filters=filters.chat(mail_chat)))

    try:
        inline_msg = await queue.get()
        if inline_msg.reply_markup and inline_msg.reply_markup.inline_keyboard:
            button_index = random.randint(0, len(inline_msg.reply_markup.inline_keyboard) - 1)
            await inline_msg.click(button_index)
            await bot_client.send_message(user_id, f"Selected domain option {button_index + 1}")
        else:
            await bot_client.send_message(user_id, "❌ No inline buttons found.")
            return

        email_msg = await queue.get()
        email_text = email_msg.text
        if "Your new fakemail address is" in email_text:
            email = email_text.split("Your new fakemail address is ")[1].split("\n")[0].strip()
            await bot_client.send_message(user_id, f"📧 Generated email: {email}")
        else:
            await bot_client.send_message(user_id, "❌ Failed to get email.")
            return

        await user_client.send_message(mail_chat, "/id")
        await queue.get()
        await bot_client.send_message(user_id, "Got /id response from mail bot.")

        # ───── START BROWSER ─────
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = uc.Chrome(options=options, use_subprocess=True)
        wait = WebDriverWait(driver, 20)

        try:
            driver.get("https://x.com/i/flow/signup")
            await bot_client.send_message(user_id, "Opened X signup page.")

            # Name
            random_name = generate_random_name()
            wait.until(EC.presence_of_element_located((By.NAME, "name"))).send_keys(random_name)
            await bot_client.send_message(user_id, f"Entered name: {random_name}")

            # Email
            wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(email)
            await bot_client.send_message(user_id, f"Entered email: {email}")

            # DOB
            month, day, year = generate_random_dob()
            driver.find_element(By.ID, "SELECTOR_1").send_keys(str(month))
            driver.find_element(By.ID, "SELECTOR_2").send_keys(str(day))
            driver.find_element(By.ID, "SELECTOR_3").send_keys(str(year))
            await bot_client.send_message(user_id, f"Entered DOB: {month}/{day}/{year}")

            wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="Next"]/ancestor::div[@role="button"]'))).click()
            await bot_client.send_message(user_id, "Clicked Next.")

            try:
                wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="Next"]/ancestor::div[@role="button"]'))).click()
            except TimeoutException:
                pass

            wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="Sign up"]/ancestor::div[@role="button"]'))).click()
            await bot_client.send_message(user_id, "Clicked Sign up, waiting for OTP...")

            # Captcha
            try:
                arkose_div = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-apikey]')))
                sitekey = arkose_div.get_attribute('data-apikey')
                await bot_client.send_message(user_id, "⚠️ Captcha detected, solving...")
                token = solve_arkose(sitekey, driver.current_url)
                if token:
                    driver.execute_script(f'document.getElementById("enforcementToken").value = "{token}";')
                    wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="Sign up"]/ancestor::div[@role="button"]'))).click()
                    await bot_client.send_message(user_id, "Captcha solved.")
                else:
                    await bot_client.send_message(user_id, "❌ Failed to solve captcha.")
                    return
            except TimeoutException:
                await bot_client.send_message(user_id, "No captcha detected.")

            # OTP from email
            time.sleep(5)
            otp_msg = await queue.get()
            otp_text = otp_msg.text
            otp = None
            if "Please enter this verification code" in otp_text:
                for line in otp_text.split("\n"):
                    if line.strip().isdigit() and len(line.strip()) == 6:
                        otp = line.strip()
                        break
            if not otp:
                await bot_client.send_message(user_id, "❌ OTP not found.")
                return

            wait.until(EC.presence_of_element_located((By.NAME, "code"))).send_keys(otp)
            await bot_client.send_message(user_id, f"Entered OTP: {otp}")

            wait.until(EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "Next") or contains(text(), "Verify")]/ancestor::div[@role="button"]'))).click()

            random_pass = generate_random_password()
            wait.until(EC.presence_of_element_located((By.NAME, "password"))).send_keys(random_pass)
            wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="Next"]/ancestor::div[@role="button"]'))).click()
            await bot_client.send_message(user_id, f"Password set: {random_pass}")

            try:
                username_input = wait.until(EC.presence_of_element_located((By.NAME, "username")))
                random_username = generate_random_username()
                username_input.send_keys(random_username)
                wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="Next"]/ancestor::div[@role="button"]'))).click()
                await bot_client.send_message(user_id, f"Username set: @{random_username}")
            except TimeoutException:
                pass

            driver.quit()
            await bot_client.send_message(user_id, f"✅ Account created!\n\nEmail: {email}\nPassword: {random_pass}")

        except Exception as e:
            driver.quit()
            await bot_client.send_message(user_id, f"❌ Error: {str(e)}")

    finally:
        user_client.remove_handler(handler)

# ───── ENTRY POINT ─────
if __name__ == "__main__":
    async def main():
        await user_client.start()
        await bot_client.start()
        print("✅ Both clients started")
        await idle()
        await user_client.stop()
        await bot_client.stop()

    asyncio.run(main())