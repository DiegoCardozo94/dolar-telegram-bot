import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes.whatsapp import app, get_dolar_rates

import pytest
from fastapi.testclient import TestClient
from routes.whatsapp import app, get_dolar_rates

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

# --- Mock de la API de dólar para no depender de internet ---
@pytest.fixture(autouse=True)
def mock_dolar(monkeypatch):
    rates = {"oficial": 200, "blue": 380, "mep": 380}
    monkeypatch.setattr("main.get_dolar_rates", lambda: rates)

# --- Tests ---
def test_whatsapp_all_dolar(client):
    resp = client.post("/whatsapp", data={"Body": "dolar"})
    assert resp.status_code == 200
    text = resp.text
    assert "Dólar oficial" in text
    assert "Dólar blue" in text
    assert "Dólar mep" in text

def test_whatsapp_oficial(client):
    resp = client.post("/whatsapp", data={"Body": "dolar oficial"})
    assert resp.status_code == 200
    text = resp.text
    assert "Dólar oficial" in text
    assert "Dólar blue" not in text

def test_whatsapp_blue(client):
    resp = client.post("/whatsapp", data={"Body": "dolar blue"})
    assert resp.status_code == 200
    text = resp.text
    assert "Dólar blue" in text
    assert "Dólar oficial" not in text

def test_whatsapp_mep(client):
    resp = client.post("/whatsapp", data={"Body": "dolar mep"})
    assert resp.status_code == 200
    text = resp.text
    assert "Dólar mep" in text
    assert "Dólar oficial" not in text

def test_whatsapp_unknown(client):
    resp = client.post("/whatsapp", data={"Body": "hola"})
    assert resp.status_code == 200
    text = resp.text
    assert "Escribe 'dolar'" in text
