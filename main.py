import os
import random
import requests
from loguru import logger
from anticaptchaofficial.funcaptchaproxyless import funcaptchaProxyless
from datetime import datetime

website_url = "https://auth.roblox.com/v2/signup"

def get_xsrf_token():
    response = requests.post("https://auth.roblox.com/v2/login", headers={"X-CSRF-TOKEN": ""})
    xsrf_token = response.headers.get('x-csrf-token')
    if xsrf_token:
        logger.debug(f'csrf-token: {xsrf_token}')
        return xsrf_token
    else:
        logger.error("Failed to fetch X-Csrf-Token")
        return None

def get_field_data(csrf_token):
    headers = {
        'authority': 'auth.roblox.com',
        'x-csrf-token': csrf_token,
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
        'content-type': 'application/json;charset=UTF-8',
        'accept': 'application/json, text/plain, */*',
    }
    response = requests.post('https://auth.roblox.com/v2/signup', headers=headers, json={})
    if response.ok:
        return response.json()["failureDetails"][0]["fieldData"]
    else:
        logger.error(f"Failed to get field data: {response.text}")
        return None

def parse_field_data(field_data):
    captcha_id, blob = field_data.split(',')
    return {'captcha_id': captcha_id, 'captcha_blob': blob}

def solve_captcha(blob_value):
    api_key = os.getenv('anticaptcha_api_key')
    if not api_key:
        logger.error("Anti-captcha API key is not set")
        return None

    solver = funcaptchaProxyless()
    solver.set_key(api_key)
    solver.set_website_url(website_url)
    website_key = requests.get("https://apis.rbxcdn.com/captcha/v1/metadata").json()["funCaptchaPublicKeys"]['ACTION_TYPE_WEB_SIGNUP']
    solver.set_website_key(website_key)
    solver.set_data_blob(str({"blob": blob_value}))

    captcha_response = solver.solve_and_return_solution()
    if captcha_response != 0:
        logger.success(f"Successful CAPTCHA response: {captcha_response}")
        return captcha_response
    else:
        logger.error(f"Failed CAPTCHA: {solver.error_code}")
        return None

def generate_birthday():
    day = str(random.randint(1, 25))
    month = 'Mar'
    year = str(random.randint(1980, 2006))
    return f"{day} {month} {year}"

def create_account(username, password):
    csrf_token = get_xsrf_token()
    if not csrf_token:
        logger.error("Failed to get X-Csrf-Token")
        return None

    field_data = get_field_data(csrf_token)
    if not field_data:
        logger.error("Failed to get field data")
        return None

    captcha_data = parse_field_data(field_data)
    captcha_token = solve_captcha(captcha_data['captcha_blob'])
    if not captcha_token:
        logger.error("Failed to solve CAPTCHA")
        return None

    birthday = generate_birthday()
    registration_payload = {
        "username": username,
        "password": password,
        "birthday": birthday,
        "gender": 1,
        "isTosAgreementBoxChecked": True,
        "context": "MultiverseSignupForm",
        "referralData": None,
        "captchaId": captcha_data['captcha_id'],
        "captchaToken": captcha_token,
        "captchaProvider": "PROVIDER_ARKOSE_LABS",
        "agreementIds": [
            "848d8d8f-0e33-4176-bcd9-aa4e22ae7905",
            "54d8a8f0-d9c8-4cf3-bd26-0cbf8af0bba3"
        ]
    }

    headers = {
        'x-csrf-token': csrf_token,
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
        'content-type': 'application/json;charset=UTF-8',
        'accept': 'application/json, text/plain, */*',
    }

    with requests.session() as session:
        response = session.post(website_url, json=registration_payload, headers=headers)
        if response.ok:
            logger.success('Successful Registration!')
            return username, password, birthday, response.cookies
        else:
            logger.error('Failed Registration!')
            logger.debug(response.headers)
            logger.debug(response.text)
            logger.debug(response.status_code)
            return None

def send_to_discord(webhook_url, message):
    data = {"content": message}
    response = requests.post(webhook_url, json=data)
    if response.status_code == 204:
        logger.success("Message sent to Discord webhook successfully")
    else:
        logger.error(f"Failed to send message to Discord webhook: {response.status_code}")

def main():
    webhook_url = input("Enter your Discord webhook URL: ")
    num_accounts = int(input("How many accounts do you want to generate (1-10000)? "))
    if not (1 <= num_accounts <= 10000):
        logger.error("Number of accounts must be between 1 and 10000")
        return

    with open('acc.txt', 'w') as file:
        for _ in range(num_accounts):
            username = f"user{random.randint(10000, 99999)}"
            password = f"pass{random.randint(10000, 99999)}"
            account = create_account(username, password)
            if account:
                username, password, birthday, _ = account
                date_created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                country = "USA"  # Example country, you may want to use an actual IP geolocation service
                account_info = f"_______________\nUsername: {username}\nPassword: {password}\nDate: {date_created}\nCountry: {country}\n_______________\n"
                file.write(account_info)

    with open('acc.txt', 'r') as file:
        content = file.read()
        send_to_discord(webhook_url, f"```\n{content}\n```")

if __name__ == "__main__":
    main()
