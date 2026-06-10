# shop (port 8000)

Boutique web (front + API de commande). **Seul service exposé au public** → cible idéale
du scan de sécurité **OWASP ZAP** (module Tests) et de la chaîne de déploiement (CI/CD).
Affiche le Green Score de chaque ferme en interrogeant `green-score`.

## Endpoints
- `GET /` — page web (HTML/CSS/JS dans `app/static/`)
- `GET /api/products` — catalogue enrichi du Green Score (null si `green-score` indisponible)
- `GET /api/orders` / `POST /api/orders` — commandes
- `GET /health` · `GET /ready` · `GET /metrics` · `GET /docs`

## Variables d'environnement
- `SERVICE_PORT` (8000) · `GREENSCORE_URL` (http://localhost:8003) · `LOG_LEVEL` (INFO)

## Lancer / tester
```bash
pip install -r requirements.txt
uvicorn app.main:app --port 8000
python -m pytest
```
