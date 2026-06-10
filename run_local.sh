#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Lance les 4 services VertiFarm en local (sans Docker), pour démonstration.
# La conteneurisation / le déploiement sont les EXERCICES des élèves (modules 5+).
#
# Prérequis : Python 3.10+ et, pour chaque service, ses dépendances installées :
#   pip install -r services/<service>/requirements.txt
#
# Usage : ./run_local.sh   (Ctrl+C pour tout arrêter)
# -----------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")"

pids=()
cleanup() { echo; echo "Arrêt des services…"; kill "${pids[@]}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "Démarrage de VertiFarm…"

( cd services/telemetry && uvicorn app.main:app --port 8002 ) &
pids+=($!)
sleep 1
( cd services/green-score && TELEMETRY_URL=http://localhost:8002 uvicorn app.main:app --port 8003 ) &
pids+=($!)
( cd services/control-api && TELEMETRY_URL=http://localhost:8002 uvicorn app.main:app --port 8001 ) &
pids+=($!)
( cd services/shop && GREENSCORE_URL=http://localhost:8003 uvicorn app.main:app --port 8000 ) &
pids+=($!)

cat <<'INFO'

VertiFarm est lancé :
  - Boutique (front)   : http://localhost:8000
  - Control API        : http://localhost:8001/docs
  - Telemetry          : http://localhost:8002/docs
  - Green Score Engine : http://localhost:8003/docs
  - Métriques Prometheus : http://localhost:<port>/metrics

Ctrl+C pour arrêter.
INFO

wait
