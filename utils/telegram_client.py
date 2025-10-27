import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(chat_id: str, message: str):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    resp = requests.post(url, data=payload)
    return resp.json()

def send_telegram_image(chat_id: str, image_url: str):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    payload = {"chat_id": chat_id, "photo": image_url}
    resp = requests.post(url, data=payload)
    return resp.json()
