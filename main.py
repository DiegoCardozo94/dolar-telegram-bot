from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import requests
from utils.telegram_client import TOKEN
import uvicorn
from app import app  
from services.dolar_services import (
    fetch_dolar_rates,
    format_message,
    load_last_rates,
    save_last_rates,
    get_all_dolar_rates
)
from scheduler import start_scheduler
from routes.dolar import router as dolar_router

app = FastAPI(title="Dólar Telegram Bot API")
app.include_router(dolar_router)

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# ---------------- Scheduler ----------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Iniciando bot y scheduler...")
    start_scheduler()
    yield
    print("🛑 Apagando bot...")

app.router.lifespan_context = lifespan

# ---------------- Health ----------------
@app.get("/health")
async def health():
    return {"status": "ok"}

# ---------------- Parse tipo ----------------
def parse_tipo(text: str) -> str | None:
    mapping = {
        "oficial":"oficial","blue":"blue","mep":"mep","bolsa":"mep",
        "ccl":"ccl","tarjeta":"tarjeta","cripto":"cripto","mayorista":"mayorista"
    }
    for k,v in mapping.items():
        if k in text:
            return v
    return None

# ---------------- Webhook ----------------
@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        if "message" not in data:
            return {"ok": True}
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "").lower().strip()

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
            try:
                requests.post(f"{BASE_URL}/sendMessage", data={"chat_id": chat_id, "text": help_msg, "parse_mode": "HTML"})
            except Exception as e:
                print("Error enviando mensaje a Telegram:", e)
            return {"ok": True}

        if text.startswith("/dolar"):
            rates_data = fetch_dolar_rates()
            tipo = parse_tipo(text)
            last_rates = load_last_rates()
            msg = format_message(rates_data, last_rates, tipo)
            save_last_rates(rates_data.get("rates", {}))
            try:
                requests.post(f"{BASE_URL}/sendMessage", data={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"})
            except Exception as e:
                print("Error enviando mensaje a Telegram:", e)
            return {"ok": True}

        # Default
        default_msg = "No entendí ese comando. Escribí /dolar para ver las opciones 💬"
        try:
            requests.post(f"{BASE_URL}/sendMessage", data={"chat_id": chat_id, "text": default_msg, "parse_mode": "HTML"})
        except Exception as e:
            print("Error enviando mensaje a Telegram:", e)
        return {"ok": True}

    except Exception as e:
        print("ERROR EN WEBHOOK:", e)
        return {"ok": False, "error": str(e)}
    
if __name__ == "__main__":
    # Ejecuta el servidor
    uvicorn.run(
        "app:app",           # Módulo y variable FastAPI
        host="0.0.0.0",      # Escucha en todas las interfaces (útil en Docker o producción)
        port=8000,
        reload=True          # Recarga automática en desarrollo
    )