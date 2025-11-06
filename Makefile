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
PYTHON_BIN = $(VENV)/bin/python
ALEMBIC_CMD = $(PYTHON_BIN) -m alembic

TEST_DIR = test
PYTEST_CMD = $(PYTHON_BIN) -m pytest

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
	@echo "🧪 $(GREEN)Exécution des tests...$(NO_COLOR)"
	@if [ -d "$(TEST_DIR)" ]; then \
	    PYTHONPATH=. $(PYTEST_CMD) $(TEST_DIR) -q; \
	else \
	    PYTHONPATH=. $(PYTEST_CMD) . -q; \
	fi
	@echo "✅ $(GREEN)Tests terminés.$(NO_COLOR)"

test-coverage:
	@echo "📊 $(GREEN)Exécution des tests avec couverture...$(NO_COLOR)"
	PYTHONPATH=. $(PYTEST_CMD) --cov=. --cov-report=html --cov-report=term
	@echo "📈 $(CYAN)Rapport généré dans htmlcov/index.html$(NO_COLOR)"

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
	docker compose down --remove-orphans
	@echo "✅ $(GREEN)Tous les conteneurs ont été arrêtés et nettoyés.$(NO_COLOR)"