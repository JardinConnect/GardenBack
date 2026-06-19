# Couche données — Modèle relationnel

**Stack persistance :**
- **SQLAlchemy** — ORM (`db/models.py`)
- **Alembic** — migrations (`alembic/versions/`)
- **SQLite** — fichier `database.db` (volume `./data`)

```mermaid
erDiagram
    User ||--o{ RefreshToken : has
    User ||--o{ ActionLog : performs
    Area ||--o{ Area : "parent/enfant"
    Area ||--o{ Cell : contains
    Cell ||--o{ Sensor : contains
    Sensor ||--o{ Analytic : records
    Alert ||--o{ AlertEvent : triggers
    Farm {
        uuid id PK
        string name
        string address
    }
```
