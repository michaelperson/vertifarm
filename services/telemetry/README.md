# telemetry (port 8002)

Ingestion et **simulation** des capteurs (pH, eau, énergie, température, humidité) par
ferme. Le simulateur intégré produit des relevés en continu → données vivantes pour
Prometheus/Grafana (module Monitoring), sans capteurs physiques.

## Endpoints
- `GET /readings/latest` — dernier relevé de chaque ferme
- `GET /readings?farm_id=&limit=` — historique récent
- `POST /readings` — ingère un relevé
- `GET /health` · `GET /ready` · `GET /metrics` · `GET /docs`

Métriques exposées : `vertifarm_ph`, `vertifarm_water_liters`, `vertifarm_energy_kwh`,
`vertifarm_temperature_c`, `vertifarm_humidity_pct`, `vertifarm_readings_total` (par ferme).

## Variables d'environnement
- `SERVICE_PORT` (8002) · `SIMULATOR_ENABLED` (true) · `SIMULATOR_INTERVAL_SECONDS` (5) · `LOG_LEVEL` (INFO)

## Lancer / tester
```bash
pip install -r requirements.txt
uvicorn app.main:app --port 8002
python -m pytest
```
