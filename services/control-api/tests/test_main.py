"""Tests de la Control API. Les eleves n'ecrivent pas ces tests : ils les EXECUTENT
(module 7) et les branchent comme quality gate dans le pipeline (module 8)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_metrics_exposes_prometheus():
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "vertifarm_control_setpoint_ph" in r.text


def test_list_farms():
    farms = client.get("/farms").json()
    assert {f["id"] for f in farms} == {"lln", "gand", "bxl"}


def test_get_unknown_farm_404():
    assert client.get("/farms/inconnu").status_code == 404


def test_update_setpoint_ph():
    r = client.put("/setpoints/lln", json={
        "ph": 6.4, "water_target_l": 120, "light_hours": 16, "co2_ppm": 1000})
    assert r.status_code == 200
    assert r.json()["ph"] == 6.4


def test_invalid_ph_rejected():
    r = client.put("/setpoints/lln", json={
        "ph": 99, "water_target_l": 120, "light_hours": 16, "co2_ppm": 1000})
    assert r.status_code == 422  # validation pydantic


def test_irrigate():
    r = client.post("/farms/gand/irrigate")
    assert r.status_code == 200
    assert r.json()["status"] == "started"


def test_sensors_fallback_when_telemetry_down():
    # La telemetrie n'est pas lancee pendant les tests : on doit recevoir un repli.
    r = client.get("/sensors")
    assert r.status_code == 200
    assert r.json()["source"] in ("telemetry", "fallback")
