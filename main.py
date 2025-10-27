from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import requests
from utils.telegram_client import TOKEN
from services.dolar_services import fetch_dolar_rates, format_message
from scheduler import start_scheduler  # 👈 nuevo import

app = FastAPI()

# URL base para el webhook
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# 🕓 Nuevo manejador de ciclo de vida
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Iniciando bot y scheduler...")
    start_scheduler()  # se lanza una vez al iniciar
    yield  # Aquí corre la app
    print("🛑 Apagando bot...")

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        print("DATA RECIBIDA:", data)

        if "message" not in data:
            print("No es un mensaje, ignorando")
            return {"ok": True}

        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "").lower().strip()
        print("CHAT_ID:", chat_id, "TEXTO:", text)

        # ✅ Mensaje de bienvenida / ayuda
        if text == "/start" or text in ["/help", "hola", "buenas"]:
            help_msg = (
                "👋 ¡Bienvenido al bot del Dólar Argentina! 🇦🇷\n\n"
                "Te puedo mostrar las cotizaciones en tiempo real y avisarte "
                "si cambian durante el día (10 a 17 hs).\n\n"
                "💵 <b>Comandos disponibles:</b>\n"
                "/dolar - todas las cotizaciones\n"
                "/dolar_oficial - oficial\n"
                "/dolar_blue - blue\n"
                "/dolar_mep - MEP / Bolsa\n"
                "/dolar_ccl - Contado con Liquidación\n"
                "/dolar_tarjeta - tarjeta\n"
                "/dolar_cripto - cripto\n"
                "/dolar_mayorista - mayorista"
            )
            resp = requests.post(
                f"{BASE_URL}/sendMessage",
                data={"chat_id": chat_id, "text": help_msg, "parse_mode": "HTML"},
            )
            print("RESPUESTA TELEGRAM (help):", resp.text)
            return {"ok": True}

        # ✅ Comando /dolar o variantes
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
            resp = requests.post(
                f"{BASE_URL}/sendMessage",
                data={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
            )
            print("RESPUESTA TELEGRAM:", resp.text)
            return {"ok": True}

        # Mensaje por defecto si no reconoce el comando
        resp = requests.post(
            f"{BASE_URL}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": "No entendí ese comando. Escribí /dolar para ver las opciones 💬",
                "parse_mode": "HTML",
            },
        )
        print("RESPUESTA TELEGRAM (default):", resp.text)
        return {"ok": True}

    except Exception as e:
        print("ERROR EN WEBHOOK:", e)
        return {"ok": False, "error": str(e)}
