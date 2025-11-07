🚀 Backend du Projet
====================

Bienvenue dans le backend de Garden Connect 🌱
Ce service est construit avec **FastAPI** et utilise **SQLite** comme base de données, gérée par **Alembic** pour les migrations.

Ce README vous guidera à travers les étapes de configuration et d’exécution du projet.

🛠️ Prérequis
---

Assurez-vous d’avoir les éléments suivants installés :

*   **Docker & Docker Compose**

*   **Make** (généralement préinstallé sur Unix/macOS ; sous Windows, utilisez [Chocolatey](https://chocolatey.org/packages/make) ou [WSL](https://learn.microsoft.com/fr-fr/windows/wsl/install)).

⚙️ Installation & Lancement
---

1. Clonez le projet

    `git clone git@github.com:JardinConnect/GardenBack.git`
    
    `cd GardenBack`


2. Configurez vos variables d’environnement

    `cp .env.example .env`


3. Lancez le projet avec Docker :

    `docker-compose up --build`


Le serveur sera disponible sur :

API : http://localhost:8000

Documentation Swagger : http://localhost:8000/docs

🐳 Docker – Commandes utiles
---

### Développement
`docker-compose up --build`

### Production
`docker-compose --profile production up -d fastapi-backend-prod`

### Logs
`docker-compose logs -f`

### Arrêter
`docker-compose down`

### Shell dans le conteneur
`docker-compose exec fastapi-backend bash`

🗄️ Gestion de la Base de Données (Alembic)
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