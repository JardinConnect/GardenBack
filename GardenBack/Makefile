# --- Variables de Couleurs ---
NO_COLOR = \033[0m
GREEN = \033[0;32m
YELLOW = \033[0;33m
BLUE = \033[0;34m
RED = \033[0;31m
CYAN = \033[0;36m
PURPLE = \033[0;35m

# --- Configuration des Chemins et Fichiers ---
REQUIREMENTS_FILE = requirements.txt
VENV_DIR = venv
PYTHON_BIN := $(VENV_DIR)/bin/python3 # Chemin vers l'exécutable Python dans l'environnement virtuel

# Alembic command prefix: Exécuter Alembic via l'interpréteur Python comme un module
# C'est la méthode la plus robuste et compatible entre les systèmes d'exploitation.
ALEMBIC_CMD_PREFIX := $(PYTHON_BIN) -m alembic

SEED_SCRIPT := db/seed.py
DATABASE_FILE := database.db # <-- CHANGÉ ICI : Nom du fichier de base de données SQLite (doit correspondre à alembic.ini)

# --- Variables Alembic ---
MIGRATE_MESSAGE ?= "Auto-generated migration" # Message par défaut si non spécifié

# --- Cibles Phony (toujours exécutées, même si un fichier du même nom existe) ou pour des actions non-fichier
.PHONY: all help install clean uninstall freeze \
        run reset-db rebuild seed \
        generate-migration upgrade downgrade history

# --- Commande par défaut (affiche l'aide si rien n'est spécifié) ---
all: help

# --- Aide Générale ---
help:
	@echo "$(BLUE)Utilisation des commandes Make :$(NO_COLOR)"
	@echo "  $(CYAN)make install$(NO_COLOR)       - Crée l'environnement virtuel et installe les dépendances du $(REQUIREMENTS_FILE)."
	@echo "  $(CYAN)make clean$(NO_COLOR)         - Supprime l'environnement virtuel ($(VENV_DIR))."
	@echo "  $(CYAN)make uninstall$(NO_COLOR)     - Désinstalle les dépendances listées dans $(REQUIREMENTS_FILE)."
	@echo "  $(CYAN)make freeze$(NO_COLOR)        - Régénère le fichier $(REQUIREMENTS_FILE) à partir des paquets installés."
	@echo ""
	@echo "  $(CYAN)make run$(NO_COLOR)           - Lance le serveur FastAPI."
	@echo "  $(RED)make reset-db$(NO_COLOR)       - Supprime le fichier de la base de données SQLite."
	@echo "  $(PURPLE)make rebuild$(NO_COLOR)     - Supprime la base de données et applique toutes les migrations."
	@echo "  $(PURPLE)make seed$(NO_COLOR)        - Exécute le script de remplissage de la base de données (assure les migrations appliquées)."
	@echo ""
	@echo "$(BLUE)Commandes Alembic (Migrations de Base de Données) :$(NO_COLOR)"
	@echo "  $(CYAN)make generate-migration [MESSAGE=\"titre de la migration\"]$(NO_COLOR)  - Génère un nouveau script de migration."
	@echo "  $(GREEN)make upgrade$(NO_COLOR)       - Applique toutes les migrations en attente (vers 'head')."
	@echo "  $(YELLOW)make downgrade$(NO_COLOR)    - Annule la dernière migration appliquée."
	@echo "  $(BLUE)make history$(NO_COLOR)        - Affiche l'historique des migrations."
	@echo ""
	@echo "Exemples :"
	@echo "  make install"
	@echo "  make generate-migration MESSAGE=\"Add users and spaces tables\""
	@echo "  make upgrade"
	@echo "  make seed"
	@echo "  make run"

# --- Cible pour installer les dépendances ---
# Crée un environnement virtuel si nécessaire et installe les paquets.
install:
	@echo "Vérification et création de l'environnement virtuel..."
	@if [ ! -d "$(VENV_DIR)" ]; then \
		python3 -m venv $(VENV_DIR); \
		echo "Environnement virtuel '$(VENV_DIR)' créé."; \
	else \
		echo "Environnement virtuel '$(VENV_DIR)' existe déjà."; \
	fi

	@echo "Installation des dépendances avec $(PYTHON_BIN) ..."
	$(PYTHON_BIN) -m pip install -r $(REQUIREMENTS_FILE)
	@echo "Dépendances installées avec succès."

# --- Cible pour nettoyer l'environnement virtuel ---
clean:
	@echo "Suppression de l'environnement virtuel '$(VENV_DIR)'..."
	@if [ -d "$(VENV_DIR)" ]; then \
		rm -rf $(VENV_DIR); \
		echo "Environnement virtuel '$(VENV_DIR)' supprimé."; \
	else \
		echo "L'environnement virtuel '$(VENV_DIR)' n'existe pas."; \
	fi

# --- Cible pour désinstaller tous les paquets du requirements.txt ---
# (Attention: cela peut désinstaller des paquets utilisés par d'autres projets si l'environnement n'est pas isolé)
uninstall:
	@echo "Désinstallation des dépendances listées dans $(REQUIREMENTS_FILE)..."
	$(PYTHON_BIN) -m pip uninstall -y -r $(REQUIREMENTS_FILE)
	@echo "Dépendances désinstallées."

# --- Cible pour régénérer le requirements.txt (utile si vous ajoutez/supprimez des paquets manuellement) ---
freeze:
	@echo "Génération de $(REQUIREMENTS_FILE)..."
	$(PYTHON_BIN) -m pip freeze > $(REQUIREMENTS_FILE)
	@echo "$(REQUIREMENTS_FILE) généré."

# --- Commandes de l'Application ---

# Lancer le serveur FastAPI
run:
	@echo "🚀 $(BLUE)Lancement de FastAPI sur http://localhost:8000 ...$(NO_COLOR)"
	$(PYTHON_BIN) -m uvicorn main:app --reload

# Supprimer la base SQLite
reset-db:
	@echo "🗑️  $(RED)Suppression de la base SQLite ($(DATABASE_FILE))...$(NO_COLOR)"
	rm -f $(DATABASE_FILE)

# Regénérer la base complète (supprime et applique les migrations)
rebuild: reset-db upgrade
	@echo "♻️  $(GREEN)Base de données reconstruite avec succès.$(NO_COLOR)"

# Exécute le script de remplissage de la base de données
# Dépend de 'upgrade' pour s'assurer que les tables sont créées.
seed: upgrade
	@echo "🌱 $(PURPLE)Exécution du script de remplissage de la base de données ($(SEED_SCRIPT))...$(NO_COLOR)"
	$(PYTHON_BIN) $(SEED_SCRIPT)
	@echo "✅ $(GREEN)Base de données remplie avec des données initiales/de test.$(NO_COLOR)"


#! --- Commandes Alembic ---
# Génère un nouveau script de migration
# Utilisation : make generate-migration MESSAGE="Ajouter la table des utilisateurs"
generate-migration:
	@echo "🔧 $(CYAN)Génération d'une migration Alembic...$(NO_COLOR)"
	@$(SHELL) -c '$(ALEMBIC_CMD_PREFIX) revision --autogenerate -m "$(MIGRATE_MESSAGE)"'
	@echo "✅ $(GREEN)Migration générée. Vérifiez le nouveau fichier dans alembic/versions/.$(NO_COLOR)"

# Applique toutes les migrations en attente jusqu'à la dernière version (head)
upgrade:
	@echo "⬆️ $(GREEN)Application des migrations en attente...$(NO_COLOR)"
	@$(SHELL) -c '$(ALEMBIC_CMD_PREFIX) upgrade head'
	@echo "🎉 $(GREEN)Migrations appliquées avec succès.$(NO_COLOR)"

# Annule la dernière migration appliquée
downgrade:
	@echo "⬇️ $(YELLOW)Annulation de la dernière migration...$(NO_COLOR)"
	@$(SHELL) -c '$(ALEMBIC_CMD_PREFIX) downgrade -1'
	@echo "↩️ $(YELLOW)Dernière migration annulée.$(NO_COLOR)"

# Affiche l'historique des migrations
history:
	@echo "📚 $(BLUE)Historique des migrations Alembic :$(NO_COLOR)"
	@$(SHELL) -c '$(ALEMBIC_CMD_PREFIX) history'
