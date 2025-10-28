# main.py
from fastapi import FastAPI, Request, APIRouter
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo
import random
import requests
from utils.telegram_client import TOKEN
from services.dolar_services import (
    fetch_dolar_rates,
    format_message,
    load_last_rates,
    save_last_rates,
    get_all_dolar_rates,
    load_initial_rates,
    save_initial_rates
)
from scheduler import start_scheduler

# ---------------- Config ----------------
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# ---------------- FastAPI ----------------
app = FastAPI(title="Dólar Argentina Bot + Web")

# ---------------- Templates ----------------
templates = Jinja2Templates(directory="templates")

# ---------------- Helpers ----------------
def now_argentina():
    return datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))

def emoji(diff):
    if diff > 0:
        return "🟢"
    elif diff < 0:
        return "🔴"
    else:
        return "🟡"

initial_rates_mock = {
    "oficial": 350,
    "blue": 650,
    "mep": 630,
    "ccl": 640,
    "tarjeta": 580,
    "cripto": 600,
    "mayorista": 345
}

def prepare_data(data_dict, initial_dict=None):
    prepared = {}
    for name, rates in data_dict.items():
        compra = float(rates.get("compra", rates)) if isinstance(rates, dict) else float(rates)
        venta = float(rates.get("venta", rates)) if isinstance(rates, dict) else float(rates)

        # 🔹 Apertura segura: si no existe, toma el valor actual
        apertura_compra = float(initial_dict.get(name, {}).get("compra", compra)) if initial_dict else compra
        apertura_venta = float(initial_dict.get(name, {}).get("venta", venta)) if initial_dict else venta

        diff_compra = compra - apertura_compra
        diff_venta = venta - apertura_venta
        pct_compra = f"{(diff_compra / apertura_compra * 100):+.2f}%" if apertura_compra else "+0.00%"
        pct_venta = f"{(diff_venta / apertura_venta * 100):+.2f}%" if apertura_venta else "+0.00%"

        prepared[name] = {
            "compra": f"{compra:.2f}",
            "venta": f"{venta:.2f}",
            "apertura_compra": f"{apertura_compra:.2f}",
            "apertura_venta": f"{apertura_venta:.2f}",
            "apertura_emoji_compra": "🟢" if diff_compra>0 else "🔴" if diff_compra<0 else "🟡",
            "apertura_emoji_venta": "🟢" if diff_venta>0 else "🔴" if diff_venta<0 else "🟡",
            "emoji_compra": "🟢" if diff_compra>0 else "🔴" if diff_compra<0 else "🟡",
            "emoji_venta": "🟢" if diff_venta>0 else "🔴" if diff_venta<0 else "🟡",
            "pct_compra": pct_compra,
            "pct_venta": pct_venta
        }

    return prepared

def get_full_date():
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    now = now_argentina()
    day_name = dias[now.weekday()].capitalize()
    day_num = now.day
    month_name = meses[now.month - 1].capitalize()
    return f"Cotización del dólar hoy {day_name} {day_num} de {month_name}"

def parse_tipo(text: str) -> str | None:
    mapping = {
        "oficial":"oficial","blue":"blue","mep":"mep","bolsa":"mep",
        "ccl":"ccl","tarjeta":"tarjeta","cripto":"cripto","mayorista":"mayorista"
    }
    for k,v in mapping.items():
        if k in text:
            return v
    return None

# ---------------- Routers ----------------
web_router = APIRouter()
bot_router = APIRouter()

# ----------- Web routes -----------
@web_router.get("/mock", response_class=HTMLResponse)
async def mock_rates(request: Request):
    now = now_argentina().strftime('%Y-%m-%d %H:%M:%S')
    full_date = get_full_date()
    data = {}
    for name, initial in initial_rates_mock.items():
        compra = initial + random.uniform(-5, 5)
        venta = initial + random.uniform(-5, 5)
        data[name] = {"compra": compra, "venta": venta}

    prepared = prepare_data(data, {k: {"compra": v, "venta": v} for k, v in initial_rates_mock.items()})

    for name in data:
        initial_rates_mock[name] = (data[name]["compra"] + data[name]["venta"]) / 2

    return templates.TemplateResponse(
        "dolar_table.html",
        {"request": request, "title": "Mock Cotizaciones", "now": now, "full_date": full_date, "data": prepared}
    )

@web_router.get("/", response_class=HTMLResponse)
async def real_rates(request: Request):
    data = get_all_dolar_rates()  # Cotizaciones actuales
    now = now_argentina().strftime('%Y-%m-%d %H:%M')
    full_date = get_full_date()

    try:
        from datetime import date
        today_str = date.today().isoformat()  # 'YYYY-MM-DD'

        # Cargar todas las aperturas históricas
        all_initials = load_initial_rates()  # carga un dict: {"2025-10-28": {...}, ...}

        # Guardar la apertura solo si no existe la del día actual
        if today_str not in all_initials:
            all_initials[today_str] = data
            save_initial_rates(all_initials)

        # Usar la apertura del día para los cálculos
        initial_rates_today = all_initials.get(today_str, data)
        prepared = prepare_data(data, initial_dict=initial_rates_today)

        # Actualizar últimos valores
        save_last_rates(data)

    except Exception as e:
        return HTMLResponse(f"⚠️ Error obteniendo cotizaciones: {e}", status_code=500)

    return templates.TemplateResponse(
        "dolar_table.html",
        {"request": request, "title": "Cotizaciones Reales", "now": now, "full_date": full_date, "data": prepared}
    )

# ----------- Bot Webhook -----------
@bot_router.post("/webhook")
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

        default_msg = "No entendí ese comando. Escribí /dolar para ver las opciones 💬"
        try:
            requests.post(f"{BASE_URL}/sendMessage", data={"chat_id": chat_id, "text": default_msg, "parse_mode": "HTML"})
        except Exception as e:
            print("Error enviando mensaje a Telegram:", e)
        return {"ok": True}
    except Exception as e:
        print("ERROR EN WEBHOOK:", e)
        return {"ok": False, "error": str(e)}

# ---------------- Lifespan ----------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Iniciando scheduler del bot...")
    start_scheduler()
    yield
    print("🛑 Apagando bot...")

app.router.lifespan_context = lifespan

# ---------------- Health ----------------
@app.get("/health")
async def health():
    return {"status": "ok"}

# ---------------- Register Routers ----------------
app.include_router(web_router)
app.include_router(bot_router)

# ---------------- Run ----------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
