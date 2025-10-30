# scheduler/tasks.py

from zoneinfo import ZoneInfo
from datetime import datetime

# Lógica de servicio
from services.dolar_services import fetch_dolar_rates 
# Clientes de Storage
from storage.supabase_client import insertar_cotizacion_supabase
from storage.csv_history import append_to_csv
from storage.json_history import append_to_json_history
from utils.file_helpers import log_error, save_json
from utils.telegram_helpers import safe_send_message
from utils.formatters import emoji
from config.constants import DATA_FILE, MIN_CHANGE_THRESHOLD

# Variables globales para el estado del scheduler
last_rates = {}
market_open_sent = False
market_close_sent = False

def check_and_save_dolar():
    """
    Lógica principal ejecutada periódicamente:
    1. Verifica horario de mercado.
    2. Obtiene las cotizaciones.
    3. Compara cambios.
    4. Guarda en historial (JSON/CSV/Supabase).
    5. Envía alerta a Telegram si hay cambios significativos.
    """
    global last_rates, market_open_sent, market_close_sent

    # Usar hora local de Argentina
    now = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))

    # 🔁 Reiniciar banderas cada nuevo día antes de las 10:00
    if now.hour < 10:
        market_open_sent = False
        market_close_sent = False

    # 🏦 Apertura
    if now.hour == 10 and not market_open_sent:
        safe_send_message("🏦 ¡El mercado abrió! Comenzando monitoreo de cotizaciones...")
        market_open_sent = True

    # 🏛️ Cierre
    if now.hour == 17 and not market_close_sent:
        safe_send_message("🏛️ ¡El mercado cerró! Monitoreo finalizado por hoy.")
        market_close_sent = True

    # ⏸️ Si el mercado no está abierto, salir
    if not (10 <= now.hour < 17):
        return

    # 💰 Fetch de cotizaciones
    try:
        data = fetch_dolar_rates()
        rates = data.get("rates", {})
        timestamp = now.isoformat()
    except Exception as e:
        log_error(f"Error obteniendo cotizaciones: {e}")
        return

    messages = []
    csv_rows = []

    # 📈 Guardado histórico y comparación
    for name, info in rates.items():
        try:
            compra = float(info["compra"])
            venta = float(info["venta"])
        except (TypeError, ValueError, KeyError):
            continue

        last = last_rates.get(name, {})
        last_compra = last.get("compra", compra)
        last_venta = last.get("venta", venta)

        # Cálculo de diferencias
        diff_compra = compra - last_compra
        diff_venta = venta - last_venta
        pct_compra = round((diff_compra / last_compra) * 100, 2) if last_compra else 0
        pct_venta = round((diff_venta / last_venta) * 100, 2) if last_venta else 0
        
        # Objeto de datos completo para guardado
        storage_data = {
            "timestamp": timestamp,
            "compra": compra,
            "venta": venta,
            "diff_compra": diff_compra,
            "diff_venta": diff_venta,
            "pct_compra": pct_compra,
            "pct_venta": pct_venta
        }


        # Prepara fila para CSV (solo las columnas necesarias)
        csv_rows.append({
            "timestamp": timestamp,
            "dolar_name": name,
            "compra": compra,
            "venta": venta,
            "diff_compra": diff_compra,
            "diff_venta": diff_venta
        })

        # Evalúa si hubo cambio significativo para alerta
        if abs(diff_compra) >= MIN_CHANGE_THRESHOLD or abs(diff_venta) >= MIN_CHANGE_THRESHOLD:
            msg = (
                f"{name.title()}\n"
                f"   Compra: {emoji(diff_compra)} ${compra:.2f} ({diff_compra:+.2f}, {pct_compra:+.2f}%)\n"
                f"   Venta:  {emoji(diff_venta)} ${venta:.2f} ({diff_venta:+.2f}, {pct_venta:+.2f}%)"
            )
            messages.append(msg)

            # 💾 Guardado de Historial (Multiples destinos)
            insertar_cotizacion_supabase(name, **storage_data)
            append_to_json_history(name, storage_data)

        # Actualiza el estado de la última cotización (se hace siempre)
        last_rates[name] = {"compra": compra, "venta": venta}

    # 🧾 Guardar CSV histórico (se llama una sola vez con todos los rows)
    append_to_csv(csv_rows)

    # 💾 Guardar últimos rates en JSON
    save_json(DATA_FILE, last_rates)

    # 📲 Enviar mensaje si hubo cambios
    if messages:
        safe_send_message("🚨 **Actualización Dólar** 🚨\n\n" + "\n\n".join(messages))

def send_daily_summary():
    """Tarea para enviar un resumen diario al cierre del mercado."""
    safe_send_message("📊 Resumen diario de cotizaciones")
    check_and_save_dolar()

def reset_flags():
    """Tarea para reiniciar las banderas de apertura/cierre al inicio del día."""
    global market_open_sent, market_close_sent
    market_open_sent = False
    market_close_sent = False