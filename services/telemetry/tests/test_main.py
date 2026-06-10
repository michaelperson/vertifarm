"""Tests du Telemetry Service. Le simulateur est désactivé pour des tests déterministes."""
import os

os.environ["SIMULATOR_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_health():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_latest_has_three_farms():
    with TestClient(app) as client:  # startup amorce 1 relevé par ferme
        data = client.get("/readings/latest").json()
        assert {r["farm_id"] for r in data} == {"lln", "gand", "bxl"}


def test_ingest_reading():
    with TestClient(app) as client:
        payload = {"farm_id": "lln", "ph": 6.1, "water_liters": 50.0,
                   "energy_kwh": 5.0, "temperature_c": 21.0, "humidity_pct": 60.0}
        r = client.post("/readings", json=payload)
        assert r.status_code == 201
        assert r.json()["farm_id"] == "lln"


def test_invalid_ph_rejected():
    with TestClient(app) as client:
        payload = {"farm_id": "lln", "ph": 50, "water_liters": 1,
                   "energy_kwh": 1, "temperature_c": 21, "humidity_pct": 60}
        assert client.post("/readings", json=payload).status_code == 422


def test_metrics_exposes_gauges():
    with TestClient(app) as client:
        text = client.get("/metrics").text
        assert "vertifarm_ph" in text
        assert "vertifarm_energy_kwh" in text
