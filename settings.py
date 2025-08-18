import os


DATABASE_FILE_NAME = "database.db"
# Construction du chemin absolu du fichier de base de données pour éviter les problèmes de répertoire de travail.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATABASE_PATH = os.path.join(PROJECT_ROOT, DATABASE_FILE_NAME)

DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

#TODO: À voir si on utilise le versionning de l'API
class Settings:
    PROJECT_NAME: str = "Modular Monolith API"
    VERSION: str = "1.0.0"

settings = Settings()

