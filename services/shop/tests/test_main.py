"""Tests de la boutique. Le Green Score Engine n'est pas lancé : le catalogue doit
quand même se charger (green_score = null)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "VertiFarm" in r.text


def test_products_listed():
    products = client.get("/api/products").json()
    assert len(products) == 7
    assert all("green_score" in p for p in products)


def test_create_order():
    r = client.post("/api/orders", json={
        "customer": "Restaurant Le Potager",
        "lines": [{"product_id": "basilic", "quantity": 3}]})
    assert r.status_code == 201
    assert r.json()["customer"] == "Restaurant Le Potager"


def test_order_unknown_product_rejected():
    r = client.post("/api/orders", json={
        "customer": "X", "lines": [{"product_id": "dragonfruit", "quantity": 1}]})
    assert r.status_code == 400


def test_empty_order_rejected():
    r = client.post("/api/orders", json={"customer": "X", "lines": []})
    assert r.status_code == 422


def test_metrics():
    assert "vertifarm_shop_orders_total" in client.get("/metrics").text
