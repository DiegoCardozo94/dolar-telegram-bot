from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from datetime import datetime
from zoneinfo import ZoneInfo
import random

def now_argentina():
    return datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))

from services.dolar_services import (
    get_all_dolar_rates,
    save_last_rates,
    load_initial_rates,
    save_initial_rates
)

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# ----------------- Helpers -----------------
def emoji(diff):
    if diff > 0:
        return "🟢"
    elif diff < 0:
        return "🔴"
    else:
        return "🟡"

# Valores iniciales para el mock
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
    """Calcula emojis y variaciones %"""
    prepared = {}
    for name, rates in data_dict.items():
        try:
            compra = float(rates.get("compra", rates)) if isinstance(rates, dict) else float(rates)
            venta = float(rates.get("venta", rates)) if isinstance(rates, dict) else float(rates)

            if initial_dict is not None:
                if name not in initial_dict:
                    initial_dict[name] = {"compra": compra, "venta": venta}
                diff_compra = compra - initial_dict[name]["compra"]
                diff_venta = venta - initial_dict[name]["venta"]
                pct_compra = f"{(diff_compra / initial_dict[name]['compra'] * 100):+.2f}%"
                pct_venta = f"{(diff_venta / initial_dict[name]['venta'] * 100):+.2f}%"
            else:
                diff_compra = diff_venta = 0
                pct_compra = pct_venta = "+0.00%"
        except Exception:
            compra = venta = diff_compra = diff_venta = 0
            pct_compra = pct_venta = "+0.00%"

        prepared[name] = {
            "compra": f"{compra:.2f}",
            "venta": f"{venta:.2f}",
            "emoji_compra": emoji(diff_compra),
            "emoji_venta": emoji(diff_venta),
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
    now = datetime.now()
    day_name = dias[now.weekday()].capitalize()  # weekday() devuelve 0=lunes
    day_num = now.day
    month_name = meses[now.month - 1].capitalize()  # month empieza en 1
    return f"Cotización del dólar hoy {day_name} {day_num} de {month_name}"

# ----------------- Routes -----------------

@app.get("/mock", response_class=HTMLResponse)
async def mock_rates(request: Request):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full_date = get_full_date()
    data = {}
    for name, initial in initial_rates_mock.items():
        compra = initial + random.uniform(-5, 5)
        venta = initial + random.uniform(-5, 5)
        data[name] = {"compra": compra, "venta": venta}

    prepared = prepare_data(data, {k: {"compra": v, "venta": v} for k, v in initial_rates_mock.items()})

    # Actualizo el mock para la próxima vez (compra y venta)
    for name in data:
        initial_rates_mock[name] = (data[name]["compra"] + data[name]["venta"]) / 2

    return templates.TemplateResponse(
        "dolar_table.html",
        {"request": request, "title": "Mock Cotizaciones", "now": now, "full_date": full_date, "data": prepared}
    )

@app.get("/", response_class=HTMLResponse)
async def real_rates(request: Request):
    data = get_all_dolar_rates()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    full_date = get_full_date()

    try:
        initial_rates = load_initial_rates()  # si no existe, se crea con los valores actuales
        if not initial_rates:
            initial_rates = data
            save_initial_rates(initial_rates)

        prepared = prepare_data(data, initial_dict=initial_rates)

        save_last_rates(data)

    except Exception as e:
        return HTMLResponse(f"⚠️ Error obteniendo cotizaciones: {e}", status_code=500)

    return templates.TemplateResponse(
        "dolar_table.html",
        {"request": request, "title": "Cotizaciones Reales", "now": now, "full_date": full_date, "data": prepared}
    )
