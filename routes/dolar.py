from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from io import BytesIO
import matplotlib.pyplot as plt
import pandas as pd
import os

from services.dolar_services import fetch_dolar_rates, format_message, log_rates, HISTORY_FILE

router = APIRouter(prefix="/dolar", tags=["Dólar"])

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
    plt.figure(figsize=(8,4))
    plt.plot(df["timestamp"], df["blue"], label="Blue", color="blue", linewidth=2)
    plt.plot(df["timestamp"], df["oficial"], label="Oficial", color="green", linestyle="--")
    plt.title("📈 Evolución del Dólar (últimas actualizaciones)")
    plt.xlabel("Hora"); plt.ylabel("Precio (ARS)")
    plt.legend(); plt.grid(True); plt.tight_layout()
    buf = BytesIO(); plt.savefig(buf, format="png"); plt.close(); buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
