#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# VertiFarm : lance les 4 services en local (sans Docker), pour démonstration.
# La conteneurisation et le déploiement sont les EXERCICES des élèves (modules 5+).
#
# Prérequis : uv uniquement (https://docs.astral.sh/uv/).
#   Windows : Git Bash ou WSL   ·   Linux   ·   macOS
#   Au premier lancement, le script crée .venv, télécharge Python si besoin
#   et installe les dépendances des 4 services. Les lancements suivants sont
#   immédiats (réinstallation uniquement si un requirements*.txt a changé).
#
# Usage :
#   ./run_local.sh                       (Ctrl+C pour tout arrêter)
#   Depuis PowerShell :
#   & "C:\Program Files\Git\bin\bash.exe" ./run_local.sh
#
# Options (variables d'environnement) :
#   PYTHON_VERSION=3.13 ./run_local.sh   version de Python (défaut : .python-version, sinon 3.12)
#   FORCE_INSTALL=1     ./run_local.sh   force la réinstallation des dépendances
#   RESET_VENV=1        ./run_local.sh   supprime et recrée .venv
# -----------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"

DEFAULT_PYTHON="3.12"
SERVICES=(telemetry green-score control-api shop)   # ordre = graphe de dépendances

# --- Affichage ----------------------------------------------------------------
if [ -t 1 ]; then B=$'\e[1m'; G=$'\e[32m'; Y=$'\e[33m'; R=$'\e[31m'; N=$'\e[0m'; else B=; G=; Y=; R=; N=; fi
info() { echo "${G}▸${N} $*"; }
warn() { echo "${Y}⚠${N} $*" >&2; }
die()  { echo "${R}✖${N} $*" >&2; exit 1; }

# --- Plateforme : layout du venv (Scripts/ sous Windows, bin/ ailleurs) -------
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) IS_WINDOWS=1; VENV_PY=".venv/Scripts/python.exe" ;;
  *)                    IS_WINDOWS=0; VENV_PY=".venv/bin/python" ;;
esac
VENV_PY_ABS="$ROOT/$VENV_PY"

# --- 1. uv --------------------------------------------------------------------
command -v uv >/dev/null 2>&1 || die "uv introuvable. Installation :
    Windows : winget install --id astral-sh.uv -e   (puis rouvrir le terminal)
    Linux/macOS : curl -LsSf https://astral.sh/uv/install.sh | sh"
info "uv $(uv --version | awk '{print $2}')"

# --- 2. Version de Python -------------------------------------------------------
if   [ -n "${PYTHON_VERSION:-}" ]; then PY_REQ="$PYTHON_VERSION"
elif [ -f .python-version ];       then PY_REQ="$(tr -d '[:space:]' < .python-version)"
else                                    PY_REQ="$DEFAULT_PYTHON"
fi

# --- 3. Environnement virtuel ---------------------------------------------------
# Un .venv créé sous Windows est inutilisable sous WSL/Linux (et inversement) :
# on le détecte et on le recrée.
if [ "${RESET_VENV:-0}" = 1 ]; then
  info "RESET_VENV=1 : suppression de .venv"; rm -rf .venv
elif [ -d .venv ] && [ ! -x "$VENV_PY" ]; then
  warn ".venv existe mais ne correspond pas à cette plateforme ($(uname -s)) : recréation."
  warn "Évitez de partager le même dossier entre Windows et WSL."
  rm -rf .venv
fi

if [ ! -x "$VENV_PY" ]; then
  info "Création de .venv (Python $PY_REQ)…"
  uv venv --python "$PY_REQ" .venv
  FORCE_INSTALL=1
fi

# --- 4. Dépendances (résolution unique pour les 4 services) ---------------------
REQS=()
for s in "${SERVICES[@]}"; do
  [ -f "services/$s/requirements.txt" ] || die "services/$s/requirements.txt introuvable."
  REQS+=("services/$s/requirements.txt")
done
[ -f requirements-dev.txt ] && REQS+=("requirements-dev.txt")

STAMP=".venv/.vertifarm-deps.sha256"
deps_hash="$({ echo "$PY_REQ"; cat "${REQS[@]}"; } | "$VENV_PY" -c \
  'import hashlib,sys; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())')"

if [ "${FORCE_INSTALL:-0}" = 1 ] || [ ! -f "$STAMP" ] || [ "$(cat "$STAMP")" != "$deps_hash" ]; then
  info "Installation des dépendances…"
  req_args=()
  for r in "${REQS[@]}"; do req_args+=(-r "$r"); done
  uv pip install --python "$VENV_PY" "${req_args[@]}" \
    || die "Échec de la résolution des dépendances (conflit de versions entre services ?)."
  echo "$deps_hash" > "$STAMP"
else
  info "Dépendances à jour."
fi

# --- Utilitaires (en Python : portable Windows/Linux/macOS, pas de lsof/curl) --
port_in_use() {
  "$VENV_PY" - "$1" <<'PY'
import socket, sys
s = socket.socket(); s.settimeout(0.5)
sys.exit(0 if s.connect_ex(("127.0.0.1", int(sys.argv[1]))) == 0 else 1)
PY
}

wait_ready() {  # attend que /health réponde (max ~15 s)
  "$VENV_PY" - "$1" <<'PY'
import sys, time, urllib.request
port = int(sys.argv[1])
for _ in range(30):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1)
        sys.exit(0)
    except Exception:
        time.sleep(0.5)
sys.exit(1)
PY
}

# --- 5. Ports libres ? -------------------------------------------------------------
port_of() {
  case "$1" in
    shop) echo 8000 ;; control-api) echo 8001 ;; telemetry) echo 8002 ;; green-score) echo 8003 ;;
  esac
}
for s in "${SERVICES[@]}"; do
  p="$(port_of "$s")"
  if port_in_use "$p"; then
    die "Le port $p ($s) est déjà occupé (instance précédente orpheline ?).
    Windows (PowerShell) : Get-NetTCPConnection -LocalPort $p -State Listen | % { Stop-Process -Id \$_.OwningProcess -Force }
    Linux/macOS          : kill \$(lsof -t -i :$p)"
  fi
done

# --- 6. Cycle de vie des processus -------------------------------------------------
pids=()
cleanup() {
  trap - EXIT INT TERM
  [ "${#pids[@]}" -eq 0 ] && return 0
  echo; info "Arrêt des services…"
  for pid in "${pids[@]}"; do
    # Git Bash : kill ne suffit pas toujours à arrêter un exécutable Windows natif
    if [ "$IS_WINDOWS" = 1 ] && [ -r "/proc/$pid/winpid" ]; then
      taskkill //F //T //PID "$(cat "/proc/$pid/winpid")" >/dev/null 2>&1 || true
    fi
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  info "Terminé."
}
trap cleanup EXIT
trap 'cleanup; exit 130' INT TERM

# start_service <nom> [VAR=valeur ...]
start_service() {
  local name="$1"; shift
  local port; port="$(port_of "$name")"
  (
    cd "services/$name"
    # shellcheck disable=SC2163  # export dynamique VAR=valeur, voulu
    for kv in "$@"; do export "$kv"; done
    # exec : uvicorn REMPLACE le sous-shell, donc $! est bien le PID d'uvicorn
    exec "$VENV_PY_ABS" -m uvicorn app.main:app --host 127.0.0.1 --port "$port"
  ) &
  pids+=("$!")
}

ensure_ready() {
  wait_ready "$(port_of "$1")" || die "Le service $1 n'a pas démarré (voir les logs ci-dessus)."
}

# --- 7. Démarrage dans l'ordre des dépendances -------------------------------------
echo; info "${B}Démarrage de VertiFarm…${N}"

start_service telemetry
ensure_ready  telemetry

start_service green-score TELEMETRY_URL=http://localhost:8002
start_service control-api TELEMETRY_URL=http://localhost:8002
ensure_ready  green-score
ensure_ready  control-api

start_service shop GREENSCORE_URL=http://localhost:8003
ensure_ready  shop

cat <<INFO

${G}${B}VertiFarm est lancé :${N}
  - Boutique (front)     : http://localhost:8000
  - Control API          : http://localhost:8001/docs
  - Telemetry            : http://localhost:8002/docs
  - Green Score Engine   : http://localhost:8003/docs
  - Métriques Prometheus : http://localhost:<port>/metrics

Ctrl+C pour arrêter.
INFO

wait