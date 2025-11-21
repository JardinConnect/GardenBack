# --- Variables de Couleurs ---
NO_COLOR = \033[0m
GREEN = \033[0;32m
YELLOW = \033[0;33m
BLUE = \033[0;34m
RED = \033[0;31m
CYAN = \033[0;36m
PURPLE = \033[0;35m

# --- Config ---
VENV = venv
# PYTHON_BIN = $(shell which python || which python3)
# PYTHON_BIN = $(VENV)/bin/python
VENV_DIR = venv
ifeq ($(OS),Windows_NT)
	PYTHON_BIN := $(VENV_DIR)/Scripts/python.exe # Chemin vers l'exécutable Python dans l'environnement virtuel Windows
else
	PYTHON_BIN := $(VENV_DIR)/bin/python3 # Chemin vers l'exécutable Python dans l'environnement virtuel Unix
endif

ALEMBIC_CMD = $(PYTHON_BIN) -m alembic

TEST_DIR = tests
PYTEST_CMD = $(PYTHON_BIN) -m pytest

.PHONY: test

# --- Aide ---
help:
	@echo ""
	@echo "Commandes de test :$(NO_COLOR)"
	@echo "  $(RED)make test$(NO_COLOR)            - Exécute tous les tests"
	@echo "  $(PURPLE)make test-coverage$(NO_COLOR)   - Exécute les tests avec couverture de code"

	@echo ""
	@echo "Commandes Alembic (Migrations de Base de Données) :$(NO_COLOR)"
	@echo "  $(CYAN)make generate-migration MESSAGE=\"titre\"$(NO_COLOR) - Génère une nouvelle migration Alembic"
	@echo "  $(GREEN)make upgrade$(NO_COLOR)         - Applique les migrations jusqu'à 'head'"
	@echo "  $(YELLOW)make downgrade$(NO_COLOR)      - Annule la dernière migration"
	@echo "  $(BLUE)make history$(NO_COLOR)          - Affiche l'historique des migrations"

	@echo ""
	@echo "Commandes Docker :$(NO_COLOR)"
	@echo "  $(GREEN)make up$(NO_COLOR)         	- Lancement de l'image docker backend "
	@echo "  $(YELLOW)make up-seed$(NO_COLOR)       	- Lancement de l'image docker backend avec remplissage de bd (idéal pour un 1er lancement avec seed)"
	@echo "  $(BLUE)make down$(NO_COLOR)          	- Stoppe et supprime les conteneurs, réseaux, volumes anonymes"

# --- Tests ---
test:
	@echo "🧪 $(GREEN)Exécution de tous les tests...$(NO_COLOR)"
	$(MAKE) $(TEST_TARGET)
	@echo "✅ $(GREEN)Tests terminés.$(NO_COLOR)"

test-coverage:
	@echo "🧪 $(GREEN)Exécution des tests avec rapport de couverture...$(NO_COLOR)"
	$(MAKE) $(TESTCOVERAGE_TARGET)
	@echo "✅ $(GREEN)Tests terminés avec rapport de couverture.$(NO_COLOR)"

# --- Alembic ---
generate-migration:
	@if [ -z "$(MESSAGE)" ]; then \
		echo "⚠️  $(RED)Veuillez spécifier un message : make generate-migration MESSAGE=\"texte\"$(NO_COLOR)"; \
		exit 1; \
	fi
	$(ALEMBIC_CMD) revision --autogenerate -m "$(MESSAGE)"
	@echo "✅ $(GREEN)Migration générée dans alembic/versions/$(NO_COLOR)"

upgrade:
	$(ALEMBIC_CMD) upgrade head
	@echo "🎉 $(GREEN)Migrations appliquées avec succès.$(NO_COLOR)"

downgrade:
	$(ALEMBIC_CMD) downgrade -1
	@echo "↩️ $(YELLOW)Dernière migration annulée.$(NO_COLOR)"

history:
	$(ALEMBIC_CMD) history

reset-db-history:
	$(ALEMBIC_CMD) stamp base
	@echo "✅ $(GREEN)Historique de migration de la base de données réinitialisé à 'base'.$(NO_COLOR)"

# --- Docker ---
up:
	@echo "🚀 $(GREEN)Lancement normal sans seed...$(NO_COLOR)"
	docker compose up --build fastapi-backend mosquitto

up-seed:
	@echo "🌱 $(YELLOW)Lancement avec seeding initial...$(NO_COLOR)"
	# Étape 1 : appliquer les migrations
	docker compose run --rm fastapi-backend sh -c "python -m alembic upgrade head"
	# Étape 2 : exécuter le seed
	docker compose run --rm seed-db
	# Étape 3 : lancer le backend et mosquitto
	docker compose up --build fastapi-backend mosquitto

# Stoppe et supprime les conteneurs, réseaux, volumes anonymes
down:
	@echo "🧹 $(RED)Arrêt et nettoyage des conteneurs...$(NO_COLOR)"
	docker compose down --remove-orphans --rmi all
	@echo "✅ $(GREEN)Tous les conteneurs ont été arrêtés et nettoyés.$(NO_COLOR)"


# -- CI --
REQUIREMENTS_FILE = requirements.txt

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


install:
	$(MAKE) $(INSTALL_TARGET)

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


clean:
	$(MAKE) $(CLEAN_TARGET)

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

test-coverage-powershell:
	@powershell -Command "\
if (Test-Path '$(TEST_DIR)') { \
	$$env:PYTHONPATH='.'; \
	& '$(PYTHON_BIN)' -m pytest --cov=services --cov-report=html --cov-report=term  \
} else { \
	$$env:PYTHONPATH='.'; \
	& '$(PYTHON_BIN)' -m pytest --cov=services --cov-report=html --cov-report=term --ignore=$(VENV_DIR)  \
}; \

test-coverage-unix:
	@echo "📊 $(GREEN)Exécution des tests avec couverture de code...$(NO_COLOR)"
	@if command -v $(PYTHON_BIN) -c "import pytest_cov" 2>/dev/null; then \
		if [ -d "$(TEST_DIR)" ]; then \
			$(PYTEST_CMD) $(TEST_DIR) --cov=services --cov-report=html --cov-report=term; \
		else \
			$(PYTEST_CMD) . --cov=services --cov-report=html --cov-report=term --ignore=$(VENV_DIR); \
		fi; \
		echo "📈 $(CYAN)Rapport de couverture généré dans htmlcov/index.html$(NO_COLOR)"; \
	else \
		echo "⚠️  $(YELLOW)pytest-cov n'est pas installé. Exécution des tests sans couverture...$(NO_COLOR)"; \
		make test; \
		echo "💡 $(CYAN)Pour activer la couverture, ajoutez 'pytest-cov' à $(REQUIREMENTS_FILE)$(NO_COLOR)"; \
	fi