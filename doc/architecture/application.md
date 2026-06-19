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

    SERVICES[services/<br/>routers + domaines métier]

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
    MAIN --> SERVICES
    SERVICES --> Layers
    SERVICES --> JWT
    JWT --> AUTH_MOD
    Layers --> DB[(db/models.py + get_db)]
    MAIN --> MQTT_MOD
    MQTT_MOD --> ASYNC
    MQTT_MOD --> AUDIT_SVC
```

Chaque domaine dans `services/` expose ses routes via un `router.py` et suit le pattern **Router → Service → Repository**. Voir [folder-structure.md](./folder-structure.md) pour le détail des modules.
