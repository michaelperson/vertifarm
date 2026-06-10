"""
VertiFarm — Control API
=======================

Pilote les fermes : consulte l'état, ajuste les consignes (pH, eau, lumière, CO2)
et déclenche les actions (arrosage). Sert de point d'entrée pour le pilotage.

Ce service est volontairement simple et SANS base de données : les données vivent
en mémoire. C'est suffisant pour la formation et facile à conteneuriser/déployer.

Endpoints utiles pour la formation :
  GET  /health                      -> liveness probe (Kubernetes)
  GET  /ready                       -> readiness probe (Kubernetes)
  GET  /metrics                     -> métriques Prometheus (module Monitoring)
  GET  /farms                       -> liste des fermes
  GET  /farms/{id}                  -> détail d'une ferme
  GET  /setpoints/{id}              -> consignes d'une ferme
  PUT  /setpoints/{id}              -> modifie les consignes (ex: ajuster le pH)
  POST /farms/{id}/irrigate         -> déclenche un cycle d'arrosage
  GET  /sensors                     -> lit la télémétrie temps réel (sinon fallback)

Variables d'environnement :
  SERVICE_PORT    (défaut 8001)
  TELEMETRY_URL   (défaut http://localhost:8002)
  LOG_LEVEL       (défaut INFO)
"""
import logging
import os

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest
from pydantic import BaseModel, Field

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s [control-api] %(message)s")
log = logging.getLogger("control-api")

TELEMETRY_URL = os.getenv("TELEMETRY_URL", "http://localhost:8002")

app = FastAPI(title="VertiFarm Control API", version="1.0.0")

# --- Données de référence : 3 fermes ---------------------------------------
FARMS = {
    "lln": {"id": "lln", "name": "VertiFarm Louvain-la-Neuve", "city": "Louvain-la-Neuve",
            "crops": ["basilic", "roquette", "mache"]},
    "gand": {"id": "gand", "name": "VertiFarm Gand", "city": "Gand",
             "crops": ["coriandre", "epinard"]},
    "bxl": {"id": "bxl", "name": "VertiFarm Bruxelles", "city": "Bruxelles",
            "crops": ["menthe", "laitue"]},
}

# Consignes de culture par ferme (modifiables via l'API)
SETPOINTS = {
    "lln": {"ph": 6.0, "water_target_l": 120.0, "light_hours": 16, "co2_ppm": 1000},
    "gand": {"ph": 6.2, "water_target_l": 140.0, "light_hours": 15, "co2_ppm": 1100},
    "bxl": {"ph": 5.8, "water_target_l": 100.0, "light_hours": 16, "co2_ppm": 950},
}

# --- Métriques Prometheus ---------------------------------------------------
IRRIGATION = Counter("vertifarm_control_irrigation_total",
                     "Nombre de cycles d'arrosage declenches", ["farm"])
SETPOINT_PH = Gauge("vertifarm_control_setpoint_ph",
                    "Consigne de pH par ferme", ["farm"])
for _fid, _sp in SETPOINTS.items():
    SETPOINT_PH.labels(farm=_fid).set(_sp["ph"])


class SetpointUpdate(BaseModel):
    ph: float = Field(ge=0, le=14, description="pH cible (0-14)")
    water_target_l: float = Field(ge=0, description="Objectif d'eau journalier (litres)")
    light_hours: int = Field(ge=0, le=24, description="Heures de lumiere par jour")
    co2_ppm: int = Field(ge=0, description="CO2 cible (ppm)")


@app.get("/health", tags=["ops"])
def health():
    """Liveness probe : le process repond."""
    return {"status": "ok"}


@app.get("/ready", tags=["ops"])
def ready():
    """Readiness probe : pret a recevoir du trafic."""
    return {"status": "ready"}


@app.get("/farms")
def list_farms():
    return list(FARMS.values())


@app.get("/farms/{farm_id}")
def get_farm(farm_id: str):
    if farm_id not in FARMS:
        raise HTTPException(status_code=404, detail="Ferme inconnue")
    return FARMS[farm_id]


@app.get("/setpoints/{farm_id}")
def get_setpoints(farm_id: str):
    if farm_id not in SETPOINTS:
        raise HTTPException(status_code=404, detail="Ferme inconnue")
    return SETPOINTS[farm_id]


@app.put("/setpoints/{farm_id}")
def update_setpoints(farm_id: str, body: SetpointUpdate):
    if farm_id not in SETPOINTS:
        raise HTTPException(status_code=404, detail="Ferme inconnue")
    SETPOINTS[farm_id] = body.model_dump()
    SETPOINT_PH.labels(farm=farm_id).set(body.ph)
    log.info("Consignes mises a jour pour %s: %s", farm_id, SETPOINTS[farm_id])
    return SETPOINTS[farm_id]


@app.post("/farms/{farm_id}/irrigate")
def irrigate(farm_id: str):
    """Declenche un cycle d'arrosage (l'action au coeur de l'incident du fil rouge)."""
    if farm_id not in FARMS:
        raise HTTPException(status_code=404, detail="Ferme inconnue")
    IRRIGATION.labels(farm=farm_id).inc()
    log.info("Cycle d'arrosage declenche pour %s", farm_id)
    return {"farm": farm_id, "action": "irrigate", "status": "started"}


@app.get("/sensors")
def sensors():
    """Lit la telemetrie temps reel ; en cas d'indisponibilite, valeurs de repli."""
    try:
        r = httpx.get(f"{TELEMETRY_URL}/readings/latest", timeout=2.0)
        r.raise_for_status()
        return {"source": "telemetry", "readings": r.json()}
    except Exception as exc:  # noqa: BLE001  (robustesse pedagogique)
        log.warning("Telemetrie indisponible (%s) -> valeurs de repli", exc)
        fallback = [{"farm_id": f, "ph": SETPOINTS[f]["ph"]} for f in FARMS]
        return {"source": "fallback", "readings": fallback}


@app.get("/metrics", tags=["ops"])
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
