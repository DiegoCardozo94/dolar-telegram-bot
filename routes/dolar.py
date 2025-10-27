from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from io import BytesIO
import matplotlib.pyplot as plt
import pandas as pd
import os
from datetime import datetime

from services.dolar_services import fetch_dolar_rates, format_message

router = APIRouter(prefix="/dolar", tags=["Dólar"])

# Archivo donde se guardará el historial completo
HISTORY_FILE = "data/dolar_history.csv"
os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)

# Tipos de dólar que queremos registrar
DOLAR_TYPES = ["oficial", "blue", "mep", "ccl", "tarjeta", "cripto", "mayorista"]

def log_rates(rates: dict):
    """Guarda las cotizaciones en CSV para el gráfico."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = {"timestamp": timestamp}
    for tipo in DOLAR_TYPES:
        data = rates.get(tipo, {})
        try:
            row[tipo] = float(data.get("venta", 0))
        except (ValueError, TypeError):
            row[tipo] = 0

    file_exists = os.path.isfile(HISTORY_FILE)
    df = pd.DataFrame([row])
    df.to_csv(HISTORY_FILE, mode='a', header=not file_exists, index=False)

@router.get("/rates")
async def get_dolar_rates():
    data = fetch_dolar_rates()
    message = format_message(data)
    if "rates" in data:
        log_rates(data["rates"])
    return {"rates": data, "message": message}

@router.get("/grafico")
async def grafico_dolar():
    if not os.path.isfile(HISTORY_FILE):
        return {"error": "No hay historial aún."}
    
    df = pd.read_csv(HISTORY_FILE, parse_dates=["timestamp"]).tail(100)
    plt.figure(figsize=(10,5))
    
    colors = {
        "oficial": "green",
        "blue": "blue",
        "mep": "orange",
        "ccl": "purple",
        "tarjeta": "red",
        "cripto": "cyan",
        "mayorista": "brown"
    }

    for tipo in DOLAR_TYPES:
        if tipo in df.columns:
            plt.plot(df["timestamp"], df[tipo], label=tipo.title(), color=colors.get(tipo, "black"), linewidth=2)
    
    plt.title("📈 Evolución del Dólar (últimas 100 actualizaciones)")
    plt.xlabel("Hora")
    plt.ylabel("Precio (ARS)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)
    
    return StreamingResponse(buf, media_type="image/png")
