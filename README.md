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

Pré-requis : Python 3.10+.

```bash
# 1) installer les dépendances de chaque service
for s in control-api telemetry green-score shop; do
  pip install -r services/$s/requirements.txt
done

# 2) tout lancer
./run_local.sh
```

Puis ouvrir la boutique : http://localhost:8000 — et les API : http://localhost:8001/docs, etc.

## Lancer les tests (module 7)

```bash
pip install -r requirements-dev.txt
cd services/control-api && python -m pytest    # idem pour les 3 autres services
```

27 tests fournis (8 + 5 + 7 + 7). Les élèves les **exécutent** et les branchent comme
*quality gate* dans le pipeline (module 8) — ils ne les écrivent pas.

## Structure

```
vertifarm/
├── README.md                ← ce fichier
├── run_local.sh             ← lance les 4 services en local
├── requirements-dev.txt     ← dépendances de test (pytest)
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


