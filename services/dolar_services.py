import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from utils.formatters import emoji # Importamos la función emoji ya refactorizada

# ---------------- Configuración ----------------
DOLAR_API = "https://dolarapi.com/v1/dolares"

DOLAR_TYPES = ["oficial", "blue", "mep", "ccl", "tarjeta", "cripto", "mayorista"]

# ---------------- Funciones de cálculo (Se mantienen) ----------------
def compute_diff(data, last):
    """Calcula la diferencia absoluta y porcentual entre cotizaciones."""
    
    # Manejo de casos donde no hay cotización previa
    last_compra = last.get("compra", data["compra"]) # Si no hay última, se usa la actual para diff 0
    last_venta = last.get("venta", data["venta"])
    
    diff_compra = data["compra"] - last_compra
    diff_venta = data["venta"] - last_venta
    
    # Evita la división por cero si la última cotización es 0
    pct_compra = round((diff_compra / last_compra) * 100, 2) if last_compra else 0
    pct_venta = round((diff_venta / last_venta) * 100, 2) if last_venta else 0
    
    return diff_compra, diff_venta, pct_compra, pct_venta

# ---------------- Función principal para traer cotizaciones ----------------
def fetch_dolar_rates():
    """
    Obtiene las cotizaciones de la API externa, las parsea y calcula
    la fecha de actualización.
    
    Retorna:
    {
        "rates": { "blue": {...}, "oficial": {...} }, 
        "updated_at": "..."
    }
    """
    try:
        # Petición a la API
        resp = requests.get(DOLAR_API, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        rates, last_update = {}, None

        # Parseo de la API
        for item in data:
            nombre = item["nombre"].lower()
            compra, venta = item.get("compra"), item.get("venta")
            
            if compra is None or venta is None:
                continue
            
            promedio = (compra + venta) / 2
            fecha = item.get("fechaActualizacion")
            
            # Determina la última fecha de actualización de todas las cotizaciones
            if fecha:
                dt = datetime.fromisoformat(fecha.replace("Z", "+00:00"))
                if not last_update or dt > last_update:
                    last_update = dt

            # Mapear nombres a tus tipos
            rate_data = {"compra": compra, "venta": venta, "promedio": promedio}
            if "oficial" in nombre: rates["oficial"] = rate_data
            elif "blue" in nombre: rates["blue"] = rate_data
            elif "bolsa" in nombre or "mep" in nombre: rates["mep"] = rate_data
            elif "contado con liqui" in nombre or "ccl" in nombre: rates["ccl"] = rate_data
            elif "tarjeta" in nombre: rates["tarjeta"] = rate_data
            elif "cripto" in nombre: rates["cripto"] = rate_data
            elif "mayorista" in nombre: rates["mayorista"] = rate_data
            # NOTA: La lógica de guardar diferencias y rates YA NO VA AQUÍ.

        # Convertir fecha a hora Argentina para el reporte
        argentina_tz = ZoneInfo("America/Argentina/Buenos_Aires")
        fecha_str = last_update.astimezone(argentina_tz).strftime("%d/%m/%Y %H:%M") if last_update else "desconocida"

        return {"rates": rates, "updated_at": fecha_str}

    except Exception as e:
        # Usamos la función de logging o simplemente retornamos el error
        from utils.file_helpers import log_error # Importación local para evitar dependencia circular
        log_error(f"Error obteniendo cotizaciones de la API: {e}")
        return {"error": f"No se pudo obtener la cotización ({e})", "rates": {}}

# ---------------- Formateo de mensajes (Se mantiene pero simplificado) ----------------
def format_message(result, last_rates, tipo=None):
    """
    Formatea las cotizaciones para un mensaje de Telegram.
    NOTA: Las funciones de formato más complejas deben idealmente ir en un módulo 'formatters'.
    """
    if "error" in result:
        return result["error"]

    rates = result.get("rates", {})
    updated_at = result.get("updated_at", "fecha desconocida")

    emojis_dict = {
        "oficial":"🏦",
        "blue":"💵",
        "mep":"📊",
        "ccl":"💹",
        "tarjeta":"💳",
        "cripto":"🪙",
        "mayorista":"🏛️"
    }

    def format_rate(name):
        data = rates.get(name, {"compra": 0, "venta": 0})
        last = last_rates.get(name, {"compra": 0, "venta": 0})
        
        # Usa la función compute_diff de este mismo módulo
        diff_compra, diff_venta, pct_compra, pct_venta = compute_diff(data, last)
        
        e = emojis_dict.get(name, "💰")
        
        return (
            f"{e} *{name.capitalize()}*\n"
            f"   Compra: {emoji(diff_compra)} ${data['compra']:.2f} ({diff_compra:+.2f}, {pct_compra:+.2f}%)\n"
            f"   Venta:  {emoji(diff_venta)} ${data['venta']:.2f} ({diff_venta:+.2f}, {pct_venta:+.2f}%)"
        )

    if tipo:
        tipo = tipo.lower()
        if tipo in DOLAR_TYPES:
            return format_rate(tipo) + f"\n🕒 Última actualización: {updated_at}"
        else:
            return f"No se encontró el tipo '{tipo}'. Tipos disponibles: {', '.join(DOLAR_TYPES)}"

    # Mostrar todos los tipos
    msg = "\n".join([format_rate(name) for name in DOLAR_TYPES])
    msg += f"\n\n🕒 Última actualización: {updated_at}"
    return msg

# ---------------- Funciones de uso general ----------------
def get_all_dolar_rates():
    """Función wrapper simple para obtener solo las rates."""
    result = fetch_dolar_rates()
    return result.get("rates", {})
