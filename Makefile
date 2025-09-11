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
ifeq ($(OS),Windows_NT)
	PYTHON_BIN := $(VENV_DIR)/Scripts/python.exe # Chemin vers l'exécutable Python dans l'environnement virtuel Windows
else
	PYTHON_BIN := $(VENV_DIR)/bin/python3 # Chemin vers l'exécutable Python dans l'environnement virtuel Unix
endif

# Alembic command prefix: Exécuter Alembic via l'interpréteur Python comme un module
# C'est la méthode la plus robuste et compatible entre les systèmes d'exploitation.
ALEMBIC_CMD_PREFIX := $(PYTHON_BIN) -m alembic

SEED_SCRIPT := db/seed.py
DATABASE_FILE := database.db # <-- CHANGÉ ICI : Nom du fichier de base de données SQLite (doit correspondre à alembic.ini)

# Configuration des tests
TEST_DIR := test
PYTEST_CMD := $(PYTHON_BIN) -m pytest

# --- Cibles Phony (toujours exécutées, même si un fichier du même nom existe) ou pour des actions non-fichier
.PHONY: all help install clean uninstall freeze \
        run reset-db rebuild seed \
        generate-migration upgrade downgrade history \
        test test-coverage

#Run test
test-powershell:
	@powershell -Command "\
if (Test-Path '$(TEST_DIR)') { \
    $$env:PYTHONPATH='.'; \
    & '$(PYTHON_BIN)' -m pytest $(TEST_DIR) -q \
} else { \
    $$env:PYTHONPATH='.'; \
    & '$(PYTHON_BIN)' -m pytest . -q --ignore=$(VENV_DIR) \
}"

test-unix:
	@if [ -d "$(TEST_DIR)" ]; then \
	    PYTHONPATH=. $(PYTEST_CMD) $(TEST_DIR) -q; \
	else \
	    PYTHONPATH=. $(PYTEST_CMD) . -q --ignore=$(VENV_DIR); \
	fi

#Run test with coverage
test-coverage-powershell:
	@powershell -Command "\
if (Test-Path '$(TEST_DIR)') { \
	$$env:PYTHONPATH='.'; \
	& '$(PYTHON_BIN)' -m pytest --cov=. --cov-report=html --cov-report=term  \
} else { \
	$$env:PYTHONPATH='.'; \
	& '$(PYTHON_BIN)' -m pytest --cov=. --cov-report=html --cov-report=term --ignore=$(VENV_DIR)  \
}; \

test-coverage-unix:
	@echo "📊 $(GREEN)Exécution des tests avec couverture de code...$(NO_COLOR)"
	@if command -v $(PYTHON_BIN) -c "import pytest_cov" 2>/dev/null; then \
		if [ -d "$(TEST_DIR)" ]; then \
			$(PYTEST_CMD) $(TEST_DIR) --cov=. --cov-report=html --cov-report=term; \
		else \
			$(PYTEST_CMD) . --cov=. --cov-report=html --cov-report=term --ignore=$(VENV_DIR); \
		fi; \
		echo "📈 $(CYAN)Rapport de couverture généré dans htmlcov/index.html$(NO_COLOR)"; \
	else \
		echo "⚠️  $(YELLOW)pytest-cov n'est pas installé. Exécution des tests sans couverture...$(NO_COLOR)"; \
		make test; \
		echo "💡 $(CYAN)Pour activer la couverture, ajoutez 'pytest-cov' à $(REQUIREMENTS_FILE)$(NO_COLOR)"; \
	fi


#Install project
install-powershell:
	@powershell -Command "\
	if (-not (Test-Path '$(VENV_DIR)')) { \
	    & python -m venv $(VENV_DIR); \
	    Write-Host 'Environnement virtuel ''$(VENV_DIR)'' créé.'; \
	} else { \
	    Write-Host 'L''environnement virtuel ''$(VENV_DIR)'' existe déjà.'; \
	} \
	& '$(PYTHON_BIN)' -m pip install -r $(REQUIREMENTS_FILE)"

install-unix:
	@if [ ! -d "$(VENV_DIR)" ]; then \
	    python3 -m venv $(VENV_DIR); \
	    echo "Environnement virtuel '$(VENV_DIR)' créé."; \
	else \
	    echo "L'environnement virtuel '$(VENV_DIR)' existe déjà."; \
	fi

	@echo "Installation des dépendances à partir de $(REQUIREMENTS_FILE)..."
	$(PYTHON_BIN) -m pip install -r $(REQUIREMENTS_FILE)

#Clean project

clean-powershell:
	@powershell -Command "\
	if (Test-Path '$(VENV_DIR)') { \
	    Remove-Item -Recurse -Force $(VENV_DIR); \
	    Write-Host 'Environnement virtuel ''$(VENV_DIR)'' supprimé.'; \
	} else { \
	    Write-Host 'L''environnement virtuel ''$(VENV_DIR)'' n''existe pas.'; \
	}"

clean-unix:
	@echo "Suppression de l'environnement virtuel '$(VENV_DIR)'..."
	@if [ -d "$(VENV_DIR)" ]; then \
		rm -rf $(VENV_DIR); \
		echo "Environnement virtuel '$(VENV_DIR)' supprimé."; \
	else \
		echo "L'environnement virtuel '$(VENV_DIR)' n'existe pas."; \
	fi


ifeq ($(OS),Windows_NT)
TEST_TARGET := test-powershell
INSTALL_TARGET := install-powershell
CLEAN_TARGET := clean-powershell
TESTCOVERAGE_TARGET := test-coverage-powershell
else
TEST_TARGET := test-unix
INSTALL_TARGET := install-unix
CLEAN_TARGET := clean-unix
TESTCOVERAGE_TARGET := test-coverage-unix
endif

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
	@echo "$(BLUE)Commandes de Test :$(NO_COLOR)"
	@echo "  $(GREEN)make test$(NO_COLOR)          - Exécute tous les tests du projet."
	@echo "  $(GREEN)make test-coverage$(NO_COLOR) - Exécute les tests avec rapport de couverture de code."
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
	@echo "  make test"
	@echo "  make run"

# --- Cible pour installer les dépendances ---
# Crée un environnement virtuel si nécessaire et installe les paquets.
install:
	$(MAKE) $(INSTALL_TARGET)

# --- Cible pour nettoyer l'environnement virtuel ---
clean:
	$(MAKE) $(CLEAN_TARGET)

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

# --- Commandes de Test ---

# Exécute tous les tests du projet
test:
	@echo "🧪 $(GREEN)Exécution de tous les tests...$(NO_COLOR)"
	$(MAKE) $(TEST_TARGET)
	@echo "✅ $(GREEN)Tests terminés.$(NO_COLOR)"


# Exécute les tests avec rapport de couverture de code
# Note: Nécessite pytest-cov (ajouter à requirements.txt si souhaité)
test-coverage:
	@echo "🧪 $(GREEN)Exécution des tests avec rapport de couverture...$(NO_COLOR)"
	$(MAKE) $(TESTCOVERAGE_TARGET)
	@echo "✅ $(GREEN)Tests terminés avec rapport de couverture.$(NO_COLOR)"

#! --- Commandes Alembic ---
# Génère un nouveau script de migration
# Utilisation : make generate-migration MESSAGE="Ajouter la table des utilisateurs"
generate-migration:
	@echo "🔧 $(CYAN)Génération d'une migration Alembic...$(NO_COLOR)"
	@$(SHELL) -c '$(PYTHON_BIN) -m alembic revision --autogenerate -m "$(MESSAGE)"'
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