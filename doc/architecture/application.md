# Architecture applicative — Monolithe modulaire

Le point d'entrée est `main.py`, qui monte tous les routers et démarre MQTT + tâches de fond au lifespan.

```mermaid
flowchart TB
    MAIN[main.py]

    subgraph Middleware
        CORS[CORSMiddleware]
        ERR[HTTPException handler]
        JWT[JWTBearer — routes protégées]
    end

    subgraph Routers["services/*/router.py"]
        AUTH["/api/auth"]
        FARM_PUB["/api/farm — public"]
        NET["/api/network"]
        ALERT["/api/alert"]
        AUDIT["/api/action-logs"]
        DATA["/api/data"]
        AREA["/api/area"]
        USER["/api/user"]
        FARM["/api/farm — protégé"]
        CELL["/api/cell"]
        SYS["/api/system"]
    end

    subgraph Layers["Pattern par domaine"]
        R[Router]
        S[Service — logique métier]
        REPO[Repository — accès DB]
        SCH[Schemas Pydantic]
        R --> S --> REPO
        R --> SCH
    end

    subgraph CrossCutting["Transversal"]
        AUTH_MOD[services/auth]
        MQTT_MOD[services/mqtt]
        ASYNC[services/async_loop]
        AUDIT_SVC[audit.service — log_action]
    end

    MAIN --> CORS
    MAIN --> Routers
    Routers --> Layers
    Routers --> JWT
    JWT --> AUTH_MOD
    Layers --> DB[(db/models.py + get_db)]
    MAIN --> MQTT_MOD
    MQTT_MOD --> ASYNC
    MQTT_MOD --> AUDIT_SVC
```

## Modules métier

| Module | Rôle | Couches |
|--------|------|---------|
| `auth` | Login, JWT, refresh tokens | router, auth, bearer, dependencies |
| `user` | CRUD utilisateurs | router → service → repository |
| `area` | Zones hiérarchiques (arborescence) | idem |
| `cell` | Cellules + capteurs + pairing | idem |
| `analytics` | Lecture/agrégation des mesures | idem |
| `alerts` | Règles d'alerte + SSE temps réel | service + event_broadcast |
| `audit` | Journal des actions + purge auto | service, purge (background task) |
| `farm_state` | Config ferme (setup public + CRUD) | idem |
| `network` | Wi-Fi via provider abstrait | service → providers |
| `system` | Infos système | router |
| `mqtt` | Client Paho, handlers, pending_acks | client, handlers, subscriber |
