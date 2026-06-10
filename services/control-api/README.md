# control-api (port 8001)

Pilotage des fermes VertiFarm : consignes (pH, eau, lumière, CO₂) et actions (arrosage).

## Endpoints
- `GET /farms`, `GET /farms/{id}` — fermes
- `GET /setpoints/{id}` / `PUT /setpoints/{id}` — consignes (le pH se règle ici)
- `POST /farms/{id}/irrigate` — déclenche un arrosage
- `GET /sensors` — lit la télémétrie temps réel (repli si indisponible)
- `GET /health` · `GET /ready` · `GET /metrics` · `GET /docs`

## Variables d'environnement
- `SERVICE_PORT` (8001) · `TELEMETRY_URL` (http://localhost:8002) · `LOG_LEVEL` (INFO)

## Lancer / tester
```bash
pip install -r requirements.txt
uvicorn app.main:app --port 8001
python -m pytest        # nécessite requirements-dev.txt à la racine
```
