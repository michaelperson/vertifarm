"""Tests du Green Score Engine. On teste la formule directement (fonction pure)
ainsi que les endpoints ops, sans dépendre de la télémétrie."""
from fastapi.testclient import TestClient

from app.main import app, compute_score

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_perfect_farm_scores_100():
    reading = {"farm_id": "lln", "ph": 6.0, "water_liters": 100.0, "energy_kwh": 10.0}
    assert compute_score(reading)["green_score"] == 100.0


def test_overuse_lowers_score():
    # Largement au-dessus des budgets eau/energie de lln (130 L / 14 kWh)
    reading = {"farm_id": "lln", "ph": 6.0, "water_liters": 260.0, "energy_kwh": 28.0}
    result = compute_score(reading)
    assert result["green_score"] < 50


def test_ph_deviation_penalised():
    reading = {"farm_id": "bxl", "ph": 7.0, "water_liters": 50.0, "energy_kwh": 5.0}
    result = compute_score(reading)
    assert result["details"]["penalite_ph"] == 10.0


def test_score_bounded_zero():
    reading = {"farm_id": "lln", "ph": 2.0, "water_liters": 9999.0, "energy_kwh": 9999.0}
    assert compute_score(reading)["green_score"] == 0.0


def test_metrics_exposes_score_gauge():
    compute_score({"farm_id": "lln", "ph": 6.0, "water_liters": 100.0, "energy_kwh": 10.0})
    assert "vertifarm_green_score" in client.get("/metrics").text


def test_score_endpoint_503_when_telemetry_down():
    assert client.get("/score").status_code == 503
