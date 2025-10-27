from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import requests
from utils.telegram_client import TOKEN
from services.dolar_services import (
    fetch_dolar_rates,
    format_message,
    load_last_rates,
    save_last_rates,
    log_rates
)
from scheduler import start_scheduler  # tu scheduler
from routes.dolar import router as dolar_router  # rutas /dolar

app = FastAPI(title="Dólar Telegram Bot API")

# ⚙️ Incluir router de rutas de dólar
app.include_router(dolar_router)

# URL base de Telegram
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# 🕓 Ciclo de vida: iniciar scheduler al arrancar
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Iniciando bot y scheduler...")
    start_scheduler()
    yield
    print("🛑 Apagando bot...")

app.router.lifespan_context = lifespan

@app.get("/health")
async def health():
    return {"status": "ok"}

# ---------------- Webhook Telegram ----------------
@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        if "message" not in data:
            return {"ok": True}

        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "").lower().strip()

        # Mensaje de bienvenida / ayuda
        if text in ["/start", "/help", "hola", "buenas"]:
            help_msg = (
                "👋 ¡Bienvenido al bot del Dólar Argentina! 🇦🇷\n\n"
                "💵 Comandos disponibles:\n"
                "/dolar - todas las cotizaciones\n"
                "/dolar_oficial - oficial\n"
                "/dolar_blue - blue\n"
                "/dolar_mep - MEP / Bolsa\n"
                "/dolar_ccl - Contado con Liquidación\n"
                "/dolar_tarjeta - tarjeta\n"
                "/dolar_cripto - cripto\n"
                "/dolar_mayorista - mayorista"
            )
            requests.post(
                f"{BASE_URL}/sendMessage",
                data={"chat_id": chat_id, "text": help_msg, "parse_mode": "HTML"},
            )
            return {"ok": True}

        # ✅ Comando /dolar y variantes
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

            # Cargar última cotización para calcular variación
            last_rates = load_last_rates()
            msg = format_message(rates_data, last_rates, tipo)
            # Guardar cotización actual como "last_rates"
            save_last_rates(rates_data.get("rates", {}))
            # Guardar historial en CSV
            log_rates(rates_data.get("rates", {}))

            requests.post(
                f"{BASE_URL}/sendMessage",
                data={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
            )
            return {"ok": True}

        # Mensaje por defecto si no reconoce el comando
        requests.post(
            f"{BASE_URL}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": "No entendí ese comando. Escribí /dolar para ver las opciones 💬",
                "parse_mode": "HTML",
            },
        )
        return {"ok": True}

    except Exception as e:
        print("ERROR EN WEBHOOK:", e)
        return {"ok": False, "error": str(e)}
