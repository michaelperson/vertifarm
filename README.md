# VertiFarm — code source pédagogique (fil rouge DevOps 2026)

Application support de la formation DevOps. Les élèves **n'écrivent pas de code** :
ils *opèrent* cette application au fil des modules (conteneurisation, orchestration,
IaC, tests, CI/CD, monitoring). Le code est volontairement simple, lisible et déjà
instrumenté pour servir chaque module.

## Les 4 services

VertiFarm exploite des fermes verticales urbaines. Le système est composé de 4 micro-services indépendants (Python / FastAPI), sans dépendance cloud.

| Service | Port | Rôle | Sert surtout… |
|---|---|---|---|
| **shop** | 8000 | Boutique web (front + commandes), service exposé au public | Tests OWASP, CI/CD |
| **control-api** | 8001 | Pilotage des fermes (consignes pH/eau/lumière, arrosage) | Conteneurs, CI/CD |
| **telemetry** | 8002 | Ingestion + simulation des capteurs (pH, eau, énergie…) | Monitoring (données vivantes) |
| **green-score** | 8003 | Calcule le Green Score (durabilité) à partir de la télémétrie | Sustainability, gate CI/CD |

Flux de données : `telemetry` → `green-score` et `control-api` → ; `green-score` → `shop`.
Chaque service est **résilient** : si un voisin est indisponible, il dégrade proprement
(valeurs de repli), pour ne jamais bloquer une démonstration.

## Points communs à tous les services (utiles pour la formation)

- `GET /health` — liveness probe (Kubernetes, module 5)
- `GET /ready` — readiness probe
- `GET /metrics` — exposition **Prometheus** (module 9)
- `GET /docs` — documentation interactive (Swagger UI, générée automatiquement)
- Configuration par **variables d'environnement** (12-factor : prêt pour conteneurs/CI/IaC)

## Lancer en local (sans Docker)

### Pré-requis

Un seul outil : [**uv**](https://docs.astral.sh/uv/) (≥ 0.12). Python n'a **pas** besoin
d'être installé : uv télécharge la bonne version (3.12 par défaut).

| OS | Installer uv | Terminal pour lancer le script |
|---|---|---|
| Windows | `winget install --id astral-sh.uv -e` (puis rouvrir le terminal) | **Git Bash** ou **WSL** |
| Linux / macOS | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | terminal habituel |

### Tout lancer

```bash
./run_local.sh
```

Depuis PowerShell :

```powershell
& "C:\Program Files\Git\bin\bash.exe" ./run_local.sh
```

Au **premier lancement**, le script crée l'environnement virtuel `.venv`, installe en
une seule résolution les dépendances des 4 services (+ `requirements-dev.txt`), puis
démarre les services dans l'ordre de leurs dépendances (`telemetry` → `green-score` et
`control-api` → `shop`) en attendant que chacun réponde sur `/health`.
Les lancements suivants sont immédiats : réinstallation uniquement si un
`requirements*.txt` a changé. **Ctrl+C** arrête proprement les 4 services.

Puis ouvrir la boutique : http://localhost:8000 — et les API : http://localhost:8001/docs, etc.

### Options

| Commande | Effet |
|---|---|
| `PYTHON_VERSION=3.13 ./run_local.sh` | autre version de Python (sinon `.python-version`, sinon 3.12) |
| `FORCE_INSTALL=1 ./run_local.sh` | force la réinstallation des dépendances |
| `RESET_VENV=1 ./run_local.sh` | supprime et recrée `.venv` |

### Lancer un seul service (développement)

```bash
source .venv/Scripts/activate      # Windows (Git Bash) — Linux/macOS : source .venv/bin/activate
cd services/telemetry
uvicorn app.main:app --port 8002 --reload
```

Les URL des voisins se règlent par variables d'environnement : `TELEMETRY_URL`
(défaut `http://localhost:8002`) et `GREENSCORE_URL` (défaut `http://localhost:8003`).

### Dépannage

| Symptôme | Cause | Solution |
|---|---|---|
| `$'\r': command not found` | script converti en CRLF au clone | vérifier `.gitattributes`, puis `git rm --cached run_local.sh && git checkout run_local.sh` |
| `uvicorn` / `uv` non reconnu | uv absent, ou terminal pas rouvert après installation | installer uv, rouvrir le terminal, relancer `./run_local.sh` |
| `Le port 800x est déjà occupé` | instance précédente orpheline | le script affiche la commande pour libérer le port |
| `.venv existe mais ne correspond pas à cette plateforme` | même dossier utilisé depuis Windows **et** WSL | recréation automatique ; éviter d'alterner |
| `Échec de la résolution des dépendances` | conflit de versions entre deux services | comparer les `services/*/requirements.txt` |

## Lancer les tests (module 7)

Les dépendances de test sont installées par `run_local.sh` (lancez-le une fois).
Ensuite, avec l'environnement activé :

```bash
source .venv/Scripts/activate      # Windows (Git Bash) — Linux/macOS : source .venv/bin/activate
cd services/control-api && python -m pytest    # idem pour les 3 autres services
```

Ou les 4 services d'un coup, depuis la racine :

```bash
for s in control-api telemetry green-score shop; do
  (cd services/$s && python -m pytest -q) || exit 1
done
```

27 tests fournis (8 + 5 + 7 + 7). Les élèves les **exécutent** et les branchent comme
*quality gate* dans le pipeline (module 8) — ils ne les écrivent pas.

## Structure

```
vertifarm/
├── README.md                ← ce fichier
├── run_local.sh             ← lance les 4 services en local (installe tout via uv)
├── requirements-dev.txt     ← dépendances de test (pytest)
├── .gitignore               ← exclut .venv, caches, secrets (.env), états Terraform…
├── .gitattributes           ← force les fins de ligne LF sur les scripts shell
├── data/                    ← jeux de données de référence (capteurs, catalogue)
└── services/
    ├── control-api/   (app/, tests/, requirements.txt, README.md)
    ├── telemetry/     (app/, tests/, requirements.txt, README.md)
    ├── green-score/   (app/, tests/, requirements.txt, README.md)
    └── shop/          (app/ + static/, tests/, requirements.txt, README.md)
```

## Ce qui n'est PAS fourni (= le travail des élèves)

Aucun fichier DevOps n'est livré : c'est l'objet de la formation. Au fil des modules,
les élèves produisent eux-mêmes :

- **Dockerfile** par service + `docker-compose` (module 5)
- **manifests Kubernetes** / Helm (module 5)
- **Terraform** + **Ansible** + **Vagrant** pour provisionner et configurer (module 6)
- scan **OWASP ZAP** sur la boutique (module 7)
- pipelines **Jenkins** et **Azure DevOps** (module 8)
- dashboards **Grafana** + alertes **Alertmanager** sur les `/metrics` (module 9)