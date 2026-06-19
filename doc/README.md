# Documentation — GardenBack

Architecture et schémas du backend JardinConnect.

## Schémas

| # | Fichier | Description |
|---|---------|-------------|
| 1 | [infrastructure.md](./architecture/infrastructure.md) | Vue d'ensemble — infrastructure Docker, MQTT, SQLite |
| 2 | [application.md](./architecture/application.md) | Architecture applicative — monolithe modulaire FastAPI |
| 3 | [rest-flow.md](./architecture/rest-flow.md) | Flux REST (client → API) |
| 4 | [mqtt-flow.md](./architecture/mqtt-flow.md) | Flux MQTT (capteurs → backend) |
| 5 | [data-model.md](./architecture/data-model.md) | Couche données — modèle relationnel |
| 6 | [security-routes.md](./architecture/security-routes.md) | Sécurité — routes publiques vs protégées |
| 7 | [folder-structure.md](./architecture/folder-structure.md) | Structure des dossiers du dépôt |

Les diagrammes sont au format [Mermaid](https://mermaid.js.org/). Ils s'affichent nativement sur GitHub et peuvent être exportés via [mermaid.live](https://mermaid.live).
