"""
VertiFarm — Shop (boutique circuit court)
=========================================

Front web + petite API de commande. C'est le service EXPOSÉ AU PUBLIC : c'est donc
la cible idéale du scan de sécurité OWASP ZAP (module Tests) et de la chaîne de
déploiement (module CI/CD). Il affiche le Green Score de chaque ferme en le
demandant au Green Score Engine.

Endpoints :
  GET  /                 -> page web (HTML)
  GET  /health
  GET  /ready
  GET  /metrics
  GET  /api/products     -> catalogue (enrichi du Green Score si disponible)
  GET  /api/orders       -> liste des commandes
  POST /api/orders       -> crée une commande

Variables d'environnement :
  SERVICE_PORT     (défaut 8000)
  GREENSCORE_URL   (défaut http://localhost:8003)
  LOG_LEVEL        (défaut INFO)
"""
import logging
import os
import time
import uuid
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from pydantic import BaseModel, Field

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s [shop] %(message)s")
log = logging.getLogger("shop")

GREENSCORE_URL = os.getenv("GREENSCORE_URL", "http://localhost:8003")
STATIC_DIR = Path(__file__).parent / "static"

# Catalogue intégré (le service reste autonome, sans dépendance de fichier externe).
PRODUCTS = [
    {"id": "basilic", "name": "Basilic frais", "farm_id": "lln", "price_eur": 2.20, "unit": "botte"},
    {"id": "roquette", "name": "Roquette sauvage", "farm_id": "lln", "price_eur": 1.90, "unit": "100g"},
    {"id": "mache", "name": "Mache", "farm_id": "lln", "price_eur": 2.10, "unit": "100g"},
    {"id": "coriandre", "name": "Coriandre", "farm_id": "gand", "price_eur": 2.00, "unit": "botte"},
    {"id": "epinard", "name": "Jeunes epinards", "farm_id": "gand", "price_eur": 2.40, "unit": "100g"},
    {"id": "menthe", "name": "Menthe", "farm_id": "bxl", "price_eur": 1.80, "unit": "botte"},
    {"id": "laitue", "name": "Laitue Batavia", "farm_id": "bxl", "price_eur": 1.50, "unit": "piece"},
]
ORDERS = []

ORDERS_TOTAL = Counter("vertifarm_shop_orders_total", "Nombre de commandes creees")

app = FastAPI(title="VertiFarm Shop", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class OrderLine(BaseModel):
    product_id: str
    quantity: int = Field(ge=1, le=999)


class Order(BaseModel):
    customer: str = Field(min_length=1, max_length=120)
    lines: list[OrderLine] = Field(min_length=1)


def _green_scores() -> dict:
    """Récupère les Green Scores par ferme ; dictionnaire vide si indisponible."""
    try:
        r = httpx.get(f"{GREENSCORE_URL}/score", timeout=2.0)
        r.raise_for_status()
        return {s["farm_id"]: s["green_score"] for s in r.json()}
    except Exception as exc:  # noqa: BLE001
        log.warning("Green Score indisponible (%s)", exc)
        return {}


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/health", tags=["ops"])
def health():
    return {"status": "ok"}


@app.get("/ready", tags=["ops"])
def ready():
    return {"status": "ready"}


@app.get("/api/products")
def products():
    scores = _green_scores()
    return [{**p, "green_score": scores.get(p["farm_id"])} for p in PRODUCTS]


@app.get("/api/orders")
def list_orders():
    return ORDERS


@app.post("/api/orders", status_code=201)
def create_order(order: Order):
    known = {p["id"] for p in PRODUCTS}
    for line in order.lines:
        if line.product_id not in known:
            raise HTTPException(status_code=400, detail=f"Produit inconnu: {line.product_id}")
    record = {
        "id": str(uuid.uuid4()),
        "customer": order.customer,
        "lines": [line.model_dump() for line in order.lines],
        "ts": time.time(),
    }
    ORDERS.append(record)
    ORDERS_TOTAL.inc()
    log.info("Commande creee: %s (%d lignes)", record["id"], len(record["lines"]))
    return record


@app.get("/metrics", tags=["ops"])
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
