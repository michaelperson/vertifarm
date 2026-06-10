"""
VertiFarm — Telemetry Service
=============================

Ingere et expose les releves des capteurs (pH, eau, energie, temperature, humidite)
pour chaque ferme. Un simulateur integre genere des releves en continu, ce qui donne
des donnees VIVANTES a observer dans Prometheus/Grafana (module Monitoring) — sans
avoir besoin de vrais capteurs.

Endpoints :
  GET  /health
  GET  /ready
  GET  /metrics                      -> metriques Prometheus (jauges par ferme)
  GET  /readings/latest              -> dernier releve de chaque ferme
  GET  /readings?farm_id=&limit=     -> historique recent
  POST /readings                     -> ingere un releve (capteur ou simulateur externe)

Variables d'environnement :
  SERVICE_PORT                 (defaut 8002)
  SIMULATOR_ENABLED            (defaut true)
  SIMULATOR_INTERVAL_SECONDS   (defaut 5)
  LOG_LEVEL                    (defaut INFO)
"""
import collections
import logging
import os
import random
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest
from pydantic import BaseModel, Field

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s [telemetry] %(message)s")
log = logging.getLogger("telemetry")

FARMS = ["lln", "gand", "bxl"]
SIMULATOR_ENABLED = os.getenv("SIMULATOR_ENABLED", "true").lower() == "true"
INTERVAL = float(os.getenv("SIMULATOR_INTERVAL_SECONDS", "5"))


@asynccontextmanager
async def lifespan(_app):
    # Amorce : un releve par ferme pour que les endpoints ne soient jamais vides.
    for f in FARMS:
        _store(_generate(f))
    if SIMULATOR_ENABLED:
        threading.Thread(target=_simulate_loop, daemon=True).start()
    yield


app = FastAPI(title="VertiFarm Telemetry Service", version="1.0.0", lifespan=lifespan)

# --- Stockage en memoire ----------------------------------------------------
HISTORY = collections.defaultdict(lambda: collections.deque(maxlen=500))
LATEST = {}
_accum = {f: {"water": 0.0, "energy": 0.0} for f in FARMS}

# --- Metriques Prometheus (une jauge par grandeur, libellee par ferme) ------
PH = Gauge("vertifarm_ph", "pH mesure", ["farm"])
WATER = Gauge("vertifarm_water_liters", "Eau consommee (litres, cumul jour)", ["farm"])
ENERGY = Gauge("vertifarm_energy_kwh", "Energie consommee (kWh, cumul jour)", ["farm"])
TEMP = Gauge("vertifarm_temperature_c", "Temperature (deg C)", ["farm"])
HUM = Gauge("vertifarm_humidity_pct", "Humidite (%)", ["farm"])
READINGS_TOTAL = Counter("vertifarm_readings_total", "Nombre de releves ingeres", ["farm"])


class Reading(BaseModel):
    farm_id: str
    ph: float = Field(ge=0, le=14)
    water_liters: float = Field(ge=0)
    energy_kwh: float = Field(ge=0)
    temperature_c: float
    humidity_pct: float = Field(ge=0, le=100)
    ts: float | None = None


def _store(reading: dict) -> dict:
    reading = dict(reading)
    reading.setdefault("ts", time.time())
    fid = reading["farm_id"]
    HISTORY[fid].append(reading)
    LATEST[fid] = reading
    PH.labels(farm=fid).set(reading["ph"])
    WATER.labels(farm=fid).set(reading["water_liters"])
    ENERGY.labels(farm=fid).set(reading["energy_kwh"])
    TEMP.labels(farm=fid).set(reading["temperature_c"])
    HUM.labels(farm=fid).set(reading["humidity_pct"])
    READINGS_TOTAL.labels(farm=fid).inc()
    return reading


def _generate(farm_id: str) -> dict:
    _accum[farm_id]["water"] += random.uniform(2.0, 6.0)
    _accum[farm_id]["energy"] += random.uniform(0.3, 0.9)
    return {
        "farm_id": farm_id,
        "ph": round(random.uniform(5.6, 6.6), 2),
        "water_liters": round(_accum[farm_id]["water"], 1),
        "energy_kwh": round(_accum[farm_id]["energy"], 2),
        "temperature_c": round(random.uniform(19.0, 24.0), 1),
        "humidity_pct": round(random.uniform(55.0, 75.0), 1),
    }


def _simulate_loop():
    log.info("Simulateur de capteurs demarre (intervalle=%ss)", INTERVAL)
    while True:
        for f in FARMS:
            _store(_generate(f))
        time.sleep(INTERVAL)


@app.get("/health", tags=["ops"])
def health():
    return {"status": "ok"}


@app.get("/ready", tags=["ops"])
def ready():
    return {"status": "ready", "farms_loaded": len(LATEST)}


@app.get("/readings/latest")
def latest():
    return list(LATEST.values())


@app.get("/readings")
def readings(farm_id: str = Query(default=None), limit: int = Query(default=20, ge=1, le=500)):
    if farm_id:
        return list(HISTORY[farm_id])[-limit:]
    out = []
    for f in FARMS:
        out.extend(list(HISTORY[f])[-limit:])
    return out


@app.post("/readings", status_code=201)
def ingest(reading: Reading):
    return _store(reading.model_dump())


@app.get("/metrics", tags=["ops"])
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
