# main.py
from fastapi import FastAPI, Request
from apscheduler.schedulers.background import BackgroundScheduler
from utils.telegram_client import TOKEN
from services.dolar_services import fetch_dolar_rates, format_message
from services.notifier import send_daily_notification
import requests
import os

app = FastAPI()

# URL base para el webhook
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        print("DATA RECIBIDA:", data)

        if "message" not in data:
            print("No es un mensaje, ignorando")
            return {"ok": True}

        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "").lower()
        print("CHAT_ID:", chat_id, "TEXTO:", text)

        if text.startswith("/dolar"):
            rates_data = fetch_dolar_rates()
            tipo = None
            if "blue" in text:
                tipo = "blue"
            elif "oficial" in text:
                tipo = "oficial"
            elif "mep" in text or "bolsa" in text:
                tipo = "mep"
            elif "ccl" in text:
                tipo = "ccl"
            elif "tarjeta" in text:
                tipo = "tarjeta"
            elif "cripto" in text:
                tipo = "cripto"
            elif "mayorista" in text:
                tipo = "mayorista"

            msg = format_message(rates_data, tipo)
            print("MENSAJE A ENVIAR:", msg)
            resp = requests.post(f"{BASE_URL}/sendMessage",
                                 data={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"})
            print("RESPUESTA TELEGRAM:", resp.text)

        else:
            help_msg = (
                "Usa los comandos:\n"
                "/dolar - todas las cotizaciones\n"
                "/dolar_oficial - oficial\n"
                "/dolar_blue - blue\n"
                "/dolar_mep - MEP / Bolsa\n"
                "/dolar_ccl - Contado con Liquidación\n"
                "/dolar_tarjeta - tarjeta\n"
                "/dolar_cripto - cripto\n"
                "/dolar_mayorista - mayorista"
            )
            resp = requests.post(f"{BASE_URL}/sendMessage",
                                 data={"chat_id": chat_id, "text": help_msg, "parse_mode": "HTML"})
            print("RESPUESTA TELEGRAM (help):", resp.text)

        return {"ok": True}

    except Exception as e:
        print("ERROR EN WEBHOOK:", e)
        return {"ok": False, "error": str(e)}

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
