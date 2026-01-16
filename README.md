🚀 GardenBack - Le Cœur de JardinConnect
=========================================

> Bienvenue dans le backend de JardinConnect ! 🌱 Ce projet, propulsé par FastAPI, est le moteur qui gère les données de vos jardins connectés. Ce guide vous aidera à vous lancer en un rien de temps.

## 📋 Sommaire
- [✨ Fonctionnalités](#-fonctionnalités)
- [🏁 Pour commencer](#-pour-commencer)
- [🧑‍💻 Workflow de développement](#-workflow-de-développement)
- [🗄️ Base de Données](#-base-de-données)
- [🧪 Tests](#-tests)
- [❓ Aide](#-aide)

## ✨ Fonctionnalités
- API RESTful moderne avec **FastAPI**.
- Base de données **SQLite** avec gestion des migrations via **Alembic**.
- Intégration **MQTT** pour la communication en temps réel avec les capteurs.
- Environnement de développement conteneurisé avec **Docker**.
- Tâches de projet simplifiées grâce à un **Makefile**.

## 🏁 Pour commencer

Suivez ces étapes pour lancer le projet pour la première fois.

### 1. Prérequis
Assurez-vous d'avoir installé :
- [Docker](https://www.docker.com/get-started) & Docker Compose
- `make` (généralement préinstallé sur macOS/Linux)

### 2. Installation
```bash
# 1. Clonez le dépôt
git clone git@github.com:JardinConnect/GardenBack.git
cd GardenBack

# 2. Créez votre fichier d'environnement
#    (pas besoin de le modifier pour un démarrage rapide)
cp .env.example .env

# 3. Lancez tout avec une seule commande !
make up-seed
```
Cette commande (`make up-seed`) va :
1.  🗑️ Nettoyer l'ancienne base de données locale (si elle existe).
2.  🏗️ Construire les images Docker.
3.  ⬆️ Appliquer les migrations de la base de données.
4.  🌱 Remplir la base de données avec des données de test (seed).
5.  🚀 Démarrer l'application et les services.

### 3. C'est prêt !
Votre environnement est maintenant en ligne :
- **API & Documentation (Swagger)**: http://localhost:8000/docs
- **Documentation alternative (ReDoc)**: http://localhost:8000/redoc

## 🧑‍💻 Workflow de développement

### Commandes quotidiennes
- **Démarrer** les services : `make up`
- **Arrêter** les services et nettoyer : `make down`
- **Voir les logs** en direct : `docker-compose logs -f fastapi-backend`

### Gestion de la base de données (Migrations)
Quand vous modifiez les modèles dans `db/models.py`, suivez ce processus :
1.  **Générez un nouveau fichier de migration** :
    ```bash
    make generate-migration MESSAGE="Ajout du champ 'is_active' à User"
    ```
2.  **Appliquez la migration**. C'est automatique ! La prochaine fois que vous ferez `make up` ou `make up-seed`, Alembic appliquera les nouvelles migrations.

Pour des opérations plus avancées :
- **Annuler la dernière migration** : `make downgrade`
- **Voir l'historique** : `make history`

## 🗄️ Schéma de la Base de Données
Voici un aperçu de la structure de nos tables.

```mermaid
erDiagram
    User {
        int id PK
        string email
        string hashed_password
        string role
    }
    Area {
        int id PK
        string name
        string color
        int parent_id FK "Référence à elle-même (self-reference)"
        int level
    }
    Cell {
        int id PK
        string name
        int area_id FK
    }
    Sensor {
        int id PK
        string sensor_id "ID unique du capteur physique"
        string sensor_type
        int cell_id FK
    }
    Analytic {
        int id PK
        float value
        datetime occured_at
        string analytic_type "Enum"
        int sensor_id FK
    }
    Area ||--o{ Area : "contient (parent/enfant)"
    Area ||--o{ Cell : "contient"
    Cell ||--o{ Sensor : "contient"
    Sensor ||--o{ Analytic : "enregistre"
```

�🗄️ Gestion de la Base de Données (Alembic)
---

Le projet utilise Alembic pour gérer les migrations de la base de données.

### Générer une migration
`make generate-migration MESSAGE="Ajout de la table utilisateurs"`

### Appliquer les migrations
`make upgrade`

### Annuler la dernière migration
`make downgrade`

### Voir l’historique
`make history`

🧪 Tests
---

### Exécuter les tests :

`make test`


### Exécuter les tests avec couverture :

`make test-coverage`


### Ou directement dans Docker :

`docker-compose exec fastapi-backend python -m pytest`

❓ Aide
---

### Lister toutes les commandes disponibles dans le Makefile :

`make help`

🛠️ Workflow
---

### Exemple 1:  Démarrage initial via commande make

1. Démarrer tous les services
`make up`

    > _tips: si on lance le projet pour la première fois, on peut lancer le projet en 'seedant' la bdd avec la commande `make up-seed`_

---

### Exemple 2: Workflow pour nouvelles migrations (services tournant)

1. Modifier vos modèles dans models.py

2. Générer la migration

`docker-compose --profile tools run --rm db-setup python -m alembic revision --autogenerate -m "Add new field to User"`

3. Appliquer la migration

`docker-compose --profile tools run --rm db-setup python -m alembic upgrade head`

4. Redémarrer FastAPI pour prendre en compte les changements

`docker-compose restart fastapi-backend`


---

### Exemple 3:  Démarrage initial via docker

1. Démarrer tous les services
`docker-compose up --build`

2. Dans un autre terminal, setup initial de la DB

`docker-compose --profile tools run --rm db-setup python -m alembic revision --autogenerate -m "Initial migration"`

`docker-compose --profile tools run --rm db-setup python -m alembic upgrade head`

`docker-compose --profile tools run --rm db-setup python db/seed.py`