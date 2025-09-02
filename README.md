🚀 Backend du Projet
====================

Bienvenue dans le backend de notre application ! Ce service est construit avec **FastAPI** et utilise **SQLite** comme base de données, gérée par **Alembic** pour les migrations. Ce README vous guidera à travers les étapes de configuration et d'exécution du projet en utilisant les commandes make pratiques fournies.
    

🛠️ Prérequis
-------------

Assurez-vous d'avoir les éléments suivants installés sur votre système :

*   **Python 3.8+**
    
*   **Make** (généralement préinstallé sur les systèmes Unix/Linux et macOS ; pour Windows, vous pouvez l'obtenir via [Chocolatey](https://chocolatey.org/packages/make) ou [WSL](https://learn.microsoft.com/fr-fr/windows/wsl/install)).
    

⚙️ Installation
---------------

Pour configurer l'environnement de développement, suivez ces étapes :

1.  `git clone git@github.com:JardinConnect/GardenBack.git`

2.  `cp .env.example .env` et renseignez ce fichier d'environnement
    
3.  `make install` Vous verrez des messages indiquant la création de l'environnement et l'installation des paquets.
    

🚀 Exécution du Serveur
-----------------------

Une fois l'installation terminée et les migrations appliquées (voir section suivante), vous pouvez lancer le serveur FastAPI :
`   make run   `

Le serveur : [http://localhost:8000]\
La documentation : [http://localhost:8000/docs]

🗄️ Gestion de la Base de Données (Alembic)
-------------------------------------------

Le projet utilise **Alembic** pour gérer les migrations de la base de données SQLite. Alembic nous aide à gérer les changements de schéma de notre base de données au fil du temps.

### Générer une Nouvelle Migration

Lorsqu'on modifie nos modèles de données (par exemple, ajoutez une nouvelle table ou colonne), on doit générer une nouvelle migration :\
`   make generate-migration MESSAGE="Ajout de la table utilisateurs"   `

Remplacez "Ajout de la table utilisateurs" par un message descriptif pour la migration. Alembic tentera de détecter automatiquement les changements. N'oubliez pas de **toujours vérifier le fichier de migration** généré dans alembic/versions/ pour s'assurer qu'il correspond aux attentes.

### Appliquer les Migrations

Pour appliquer toutes les migrations en attente à la base de données (ce qui est nécessaire pour créer les tables ou les modifier) : \
`   make upgrade   `

Cette commande mettra la base de données à jour vers la dernière version.

### Annuler la Dernière Migration

Si vous avez besoin d'annuler la dernière migration appliquée (attention, cela peut entraîner une perte de données si la migration a supprimé des colonnes ou tables) : \
`   make downgrade   `

### Historique des Migrations

Pour voir l'historique complet de toutes les migrations disponibles et appliquées : \
`   make history   `

🔧 Maintenance
--------------

Voici quelques commandes utiles pour la maintenance de votre environnement et de votre base de données.

### Nettoyer l'Environnement

Pour supprimer l'environnement virtuel et toutes les dépendances installées :\
`   make clean   `

### Réinitialiser la Base de Données

Cette commande supprime le fichier de la base de données SQLite (database.db). C'est utile pour repartir de zéro :\
`   make reset-db   `

### Reconstruire la Base de Données

Combine la suppression de la base de données et l'application de toutes les migrations. Utile pour une reconstruction propre :\
`   make rebuild   `

### Remplir la Base de Données (Seed)

Exécute un script pour remplir votre base de données avec des données initiales ou de test. Cette commande s'assure d'abord que toutes les migrations sont appliquées.\
`   make seed   `

### Mettre à Jour les Dépendances

Si vous avez ajouté ou supprimé manuellement des paquets Python et que vous souhaitez mettre à jour le fichier requirements.txt :\
`   make freeze   `

❓ Aide
------

Pour obtenir un aperçu de toutes les commandes make disponibles et leur description :
`   make help   `

🐳 Docker
--------------

Voici quelques commandes utiles pour la maintenance de votre environnement et de votre base de données.

### Développement
`docker-compose up --build`

### Production  
`docker-compose --profile production up -d fastapi-backend-prod`

### Voir les logs
`docker-compose logs -f`

### Arrêter
`docker-compose down`

### Tests
`docker-compose exec fastapi-backend python -m pytest`

### Migrations
`docker-compose exec fastapi-backend python -m alembic upgrade head`

### Shell
`docker-compose exec fastapi-backend bash`
