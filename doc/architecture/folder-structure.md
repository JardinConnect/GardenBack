# Structure des dossiers

```mermaid
flowchart TB
    ROOT[GardenBack/]

    ROOT --> MAIN[main.py]
    ROOT --> SETTINGS[settings.py]
    ROOT --> DB[db/]
    ROOT --> SERVICES[services/]
    ROOT --> ALEMBIC[alembic/]
    ROOT --> MOSQ[mosquitto/config/]
    ROOT --> DOCKER[docker-compose.yml + Dockerfile]
    ROOT --> MAKE[Makefile]

    DB --> DB1[database.py]
    DB --> DB2[models.py]
    DB --> DB3[seed.py]

    SERVICES --> AUTH[auth/]
    SERVICES --> USER[user/]
    SERVICES --> AREA[area/]
    SERVICES --> CELL[cell/]
    SERVICES --> ANALYTICS[analytics/]
    SERVICES --> ALERTS[alerts/]
    SERVICES --> AUDIT[audit/]
    SERVICES --> FARM[farm_state/]
    SERVICES --> NETWORK[network/]
    SERVICES --> SYSTEM[system/]
    SERVICES --> MQTT[mqtt/]

    NETWORK --> PROVIDERS[providers/<br/>linux_nmcli, tailscale…]
```

## Arborescence texte

```
GardenBack/
├── main.py                 # Point d'entrée FastAPI
├── settings.py             # Config (DB, MQTT, Tailscale…)
├── db/
│   ├── database.py         # Engine + SessionLocal + get_db
│   ├── models.py           # Modèles SQLAlchemy
│   └── seed.py             # Données de test
├── services/               # Domaines métier (monolithe modulaire)
│   ├── auth/
│   ├── user/
│   ├── area/
│   ├── cell/
│   ├── analytics/
│   ├── alerts/
│   ├── audit/
│   ├── farm_state/
│   ├── network/
│   │   └── providers/      # linux_nmcli, tailscale…
│   ├── system/
│   └── mqtt/               # Client + handlers MQTT
├── alembic/                # Migrations DB
├── mosquitto/config/       # Broker MQTT
├── docker-compose.yml
├── Dockerfile
└── Makefile                # up, test, migrations…
```
