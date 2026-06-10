"""
VertiFarm — Green Score Engine
==============================

Calcule le « Green Score » (0-100) de chaque ferme à partir de la télémétrie :
plus une ferme respecte ses budgets eau/énergie et son pH optimal, plus le score
est élevé. C'est le KPI durabilité du board (module Sustainability), mesuré en
continu (module Monitoring) et contrôlable en pipeline (gate du module CI/CD).

Formule (volontairement simple et explicable) :
    score = 100
            - penalite_eau     (depassement du budget eau)
            - penalite_energie (depassement du budget energie)
            - penalite_ph      (ecart au pH optimal 6.0)
    borne entre 0 et 100.

Endpoints :
  GET /health
  GET /ready
  GET /metrics                 -> jauge vertifarm_green_score{farm}
  GET /score                   -> score de toutes les fermes
  GET /score/{farm_id}         -> score d'une ferme

Variables d'environnement :
  SERVICE_PORT   (défaut 8003)
  TELEMETRY_URL  (défaut http://localhost:8002)
  LOG_LEVEL      (défaut INFO)
"""
import logging
import os

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s [green-score] %(message)s")
log = logging.getLogger("green-score")

TELEMETRY_URL = os.getenv("TELEMETRY_URL", "http://localhost:8002")

# Budgets journaliers par ferme (litres d'eau, kWh) et pH optimal.
BUDGETS = {
    "lln": {"water_l": 130.0, "energy_kwh": 14.0},
    "gand": {"water_l": 150.0, "energy_kwh": 17.0},
    "bxl": {"water_l": 110.0, "energy_kwh": 12.0},
}
PH_OPTIMAL = 6.0

GREEN_SCORE = Gauge("vertifarm_green_score", "Green Score par ferme (0-100)", ["farm"])

app = FastAPI(title="VertiFarm Green Score Engine", version="1.0.0")


def compute_score(reading: dict) -> dict:
    """Calcule le score d'une ferme à partir d'un relevé de télémétrie."""
    fid = reading["farm_id"]
    budget = BUDGETS.get(fid, {"water_l": 130.0, "energy_kwh": 14.0})

    water_over = max(0.0, (reading["water_liters"] - budget["water_l"]) / budget["water_l"])
    energy_over = max(0.0, (reading["energy_kwh"] - budget["energy_kwh"]) / budget["energy_kwh"])

    penalite_eau = round(water_over * 40.0, 1)
    penalite_energie = round(energy_over * 40.0, 1)
    penalite_ph = round(abs(reading.get("ph", PH_OPTIMAL) - PH_OPTIMAL) * 10.0, 1)

    score = max(0.0, min(100.0, 100.0 - penalite_eau - penalite_energie - penalite_ph))
    GREEN_SCORE.labels(farm=fid).set(score)
    return {
        "farm_id": fid,
        "green_score": round(score, 1),
        "details": {
            "penalite_eau": penalite_eau,
            "penalite_energie": penalite_energie,
            "penalite_ph": penalite_ph,
            "water_liters": reading["water_liters"],
            "energy_kwh": reading["energy_kwh"],
            "ph": reading.get("ph"),
            "budget": budget,
        },
    }


def _fetch_latest() -> list:
    r = httpx.get(f"{TELEMETRY_URL}/readings/latest", timeout=2.0)
    r.raise_for_status()
    return r.json()


@app.get("/health", tags=["ops"])
def health():
    return {"status": "ok"}


@app.get("/ready", tags=["ops"])
def ready():
    return {"status": "ready"}


@app.get("/score")
def score_all():
    try:
        readings = _fetch_latest()
    except Exception as exc:  # noqa: BLE001
        log.warning("Telemetrie indisponible (%s)", exc)
        raise HTTPException(status_code=503, detail="Telemetrie indisponible")
    return [compute_score(r) for r in readings]


@app.get("/score/{farm_id}")
def score_one(farm_id: str):
    try:
        readings = _fetch_latest()
    except Exception as exc:  # noqa: BLE001
        log.warning("Telemetrie indisponible (%s)", exc)
        raise HTTPException(status_code=503, detail="Telemetrie indisponible")
    for r in readings:
        if r["farm_id"] == farm_id:
            return compute_score(r)
    raise HTTPException(status_code=404, detail="Ferme inconnue ou sans releve")


@app.get("/metrics", tags=["ops"])
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
