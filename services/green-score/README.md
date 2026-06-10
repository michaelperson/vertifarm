# green-score (port 8003)

Calcule le **Green Score** (0–100) de chaque ferme à partir de la télémétrie. KPI
durabilité du board (module Sustainability), mesuré en continu (module Monitoring),
utilisable comme **gate** de pipeline (module CI/CD).

## Formule
`score = 100 − pénalité_eau − pénalité_énergie − pénalité_pH` (borné 0–100), où les
pénalités sanctionnent le dépassement des budgets eau/énergie et l'écart au pH optimal (6.0).

## Endpoints
- `GET /score` — score de toutes les fermes
- `GET /score/{id}` — score d'une ferme
- `GET /health` · `GET /ready` · `GET /metrics` (jauge `vertifarm_green_score{farm}`) · `GET /docs`

Renvoie `503` si la télémétrie est indisponible (pas de score sans données).

## Variables d'environnement
- `SERVICE_PORT` (8003) · `TELEMETRY_URL` (http://localhost:8002) · `LOG_LEVEL` (INFO)

## Lancer / tester
```bash
pip install -r requirements.txt
uvicorn app.main:app --port 8003
python -m pytest
```
