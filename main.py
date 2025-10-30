# main.py

from fastapi import FastAPI, Request, APIRouter
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from datetime import datetime, date
from zoneinfo import ZoneInfo
from fastapi.staticfiles import StaticFiles
import random
import requests

from utils.telegram_client import TOKEN
from utils.file_helpers import load_json, save_json
from utils.formatters import prepare_data, emoji
from utils.helpers import now_argentina, get_full_date, parse_tipo, time_ago

# Servicios
from services.dolar_services import (
    fetch_dolar_rates,
    format_message,
    get_all_dolar_rates,
)

# Storage (persistencia)
from storage.initial_rates import (
    load_initial_rates,
    save_initial_rates_by_day
)
from config.constants import DATA_FILE, CHECK_INTERVAL_MINUTES, HISTORY_JSON_FILE
from scheduler.main_scheduler import start_scheduler, stop_scheduler

# ---------------- Config ----------------
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# ---------------- FastAPI ----------------
app = FastAPI(title="Dólar Argentina Bot + Web")

# ---------------- Configurar Estáticos ----------------
app.mount("/static", StaticFiles(directory="static"), name="static")

# ---------------- Templates ----------------
templates = Jinja2Templates(directory="templates")
templates.env.globals['time_ago'] = time_ago

# ---------------- Helpers (Funciones reutilizables que son web/bot-agnósticas) ----------------
def now_argentina():
    return datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))

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
    initial_rates_mock = {
        "oficial": 350, "blue": 650, "mep": 630, "ccl": 640, "tarjeta": 580,
        "cripto": 600, "mayorista": 345
    }
    
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
    data = get_all_dolar_rates() # Cotizaciones actuales
    now_dt = now_argentina()
    now = now_dt.strftime('%Y-%m-%d %H:%M')
    full_date = get_full_date()
    
    # 1. Inicialización de variables
    last_save_timestamp = None 
    last_individual_updates = {} 
    history = []

    # ------------------- LECTURA AISLADA DEL HISTORIAL -------------------
    try:
        history = load_json(HISTORY_JSON_FILE)
        
        # 1. Obtener el timestamp global (el último registro del historial)
        if isinstance(history, list) and len(history) > 0 and history[-1].get("timestamp"):
            last_save_timestamp = history[-1]["timestamp"]
            
        # 🚨 DIAGNÓSTICO: Muestra qué valor tomó la ruta web
        print(f"Ruta Web: Valor leído de history.json: {last_save_timestamp}")
            
    except Exception as e:
        print(f"Advertencia: Error al leer {HISTORY_JSON_FILE}: {e.__class__.__name__} - {e}")
        pass 
        
    # 2. Establecer el FALLBACK (hora de la consulta) SOLO si el historial estaba vacío o falló la lectura
    if last_save_timestamp is None:
        last_save_timestamp = now_dt.isoformat()
        
    # ----------------------------------------------------------------------
    # 3. LÓGICA CLAVE: ENCONTRAR ÚLTIMOS TIMESTAMPS INDIVIDUALES
    # Iteramos el historial al revés (del más reciente al más antiguo)
    # Solo guardamos el primer (último) timestamp que encontramos para cada tipo de dólar.
    for record in reversed(history):
        
        # 🚨 CORRECCIÓN CRÍTICA: Ignorar registros que no son diccionarios (maneja el AttributeError)
        if not isinstance(record, dict):
            # No falla, simplemente salta el registro corrupto (cadena, etc.)
            continue 
            
        dolar_type = record.get("tipo") 
        timestamp = record.get("timestamp")
        
        # Si tiene tipo y timestamp, y no lo hemos registrado ya (porque iteramos al revés)
        if dolar_type and timestamp and dolar_type not in last_individual_updates:
            last_individual_updates[dolar_type] = timestamp
            
    # ----------------------------------------------------------------------

    try:
        today_str = date.today().isoformat()

        # Cargar/Guardar aperturas
        all_initials = load_initial_rates() 
        save_initial_rates_by_day(data) 
        
        # Usar la apertura del día para los cálculos
        initial_rates_today = all_initials.get(today_str, data)
        prepared = prepare_data(data, initial_dict=initial_rates_today)

        # 💾 Actualizar últimos valores (last_rates.json)
        save_json(DATA_FILE, data) 
        
    except Exception as e:
        print(f"Error procesando cotizaciones en ruta web: {e}")
        return HTMLResponse(f"⚠️ Error obteniendo cotizaciones: {e}", status_code=500)
        
    # La variable ya tiene el valor correcto (Historial, o Fallback si el historial falló)
    timestamp_for_cards = last_save_timestamp

    # 4. Renderizar la plantilla con todas las variables necesarias
    return templates.TemplateResponse(
        "dolar_table.html",
        {
            "request": request, 
            "title": "Cotizaciones Reales", 
            "now": now, 
            "full_date": full_date, 
            "data": prepared,
            "CHECK_INTERVAL_MINUTES": CHECK_INTERVAL_MINUTES,
            "last_updates": last_individual_updates, # <-- ¡CLAVE para horas individuales!
            "timestamp_for_cards": timestamp_for_cards # <-- Fallback
        }
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

        # 1. Manejo de /start, /help, etc. (se mantiene sin cambios)
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

        # 2. Manejo de /dolar (se actualiza el guardado de last_rates)
        if text.startswith("/dolar"):
            rates_data = fetch_dolar_rates()
            tipo = parse_tipo(text)
            
            # Cargar last_rates usando los helpers de utils/file_helpers.py
            last_rates = load_json(DATA_FILE) 
            
            msg = format_message(rates_data, last_rates, tipo)
            
            # Guardar last_rates usando los helpers de utils/file_helpers.py
            save_json(DATA_FILE, rates_data.get("rates", {})) 
            
            try:
                # Usar safe_send_message de utils/telegram_helpers.py sería ideal aquí, 
                # pero mantenemos requests.post por si la integración es más compleja.
                requests.post(f"{BASE_URL}/sendMessage", data={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"})
            except Exception as e:
                print("Error enviando mensaje a Telegram:", e)
            return {"ok": True}

        # 3. Respuesta por defecto
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
    stop_scheduler() # Aseguramos que el scheduler se detenga limpiamente

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