# =============================================================================
# VOYAGER - Makefile
# =============================================================================
# Common commands for Docker Compose management
#
# Usage:
#   make build        Build all images
#   make up           Start all services
#   make down         Stop all services
#   make logs         View logs
#   make migrate      Run Django migrations
#   make test         Run tests
#   make vault-init   Initialize Vault
#   make keycloak-import  Import Keycloak realm
# =============================================================================

# Configuration
COMPOSE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
PROJECT_ROOT := $(abspath $(COMPOSE_DIR)/..)
ENV_FILE := $(PROJECT_ROOT)/.env
COMPOSE_BASE := $(COMPOSE_DIR)/docker-compose.yml
COMPOSE_PROD := $(COMPOSE_DIR)/docker-compose.prod.yml
COMPOSE_CMD := docker compose --file $(COMPOSE_BASE) --env-file $(ENV_FILE)
COMPOSE_PROD_CMD := docker compose --file $(COMPOSE_BASE) --file $(COMPOSE_PROD) --env-file $(ENV_FILE)

# Colors
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

# Default target
.DEFAULT_GOAL := help

# =============================================================================
# HELP
# =============================================================================
.PHONY: help
help: ## Show this help message
	@echo ""
	@echo -e "$(BLUE)╔══════════════════════════════════════════════════════════════╗$(RESET)"
	@echo -e "$(BLUE)║              Voyager - Docker Compose Commands               ║$(RESET)"
	@echo -e "$(BLUE)╚══════════════════════════════════════════════════════════════╝$(RESET)"
	@echo ""
	@echo -e "$(GREEN)Build & Deploy:$(RESET)"
	@echo "  make build            Build all Docker images"
	@echo "  make build-nc         Build all images (no cache)"
	@echo "  make up               Start all services (detached)"
	@echo "  make up-fg            Start all services (foreground)"
	@echo "  make up-prod          Start with production overrides"
	@echo "  make down             Stop all services"
	@echo "  make down-v           Stop all services and remove volumes"
	@echo "  make restart          Restart all services"
	@echo "  make pull             Pull latest images"
	@echo ""
	@echo -e "$(GREEN)Status & Logs:$(RESET)"
	@echo "  make logs             View logs (all services)"
	@echo "  make logs-api         View voyager-api logs"
	@echo "  make logs-worker      View celery-worker logs"
	@echo "  make logs-db          View postgres logs"
	@echo "  make ps               Show running containers"
	@echo "  make top              Show resource usage"
	@echo ""
	@echo -e "$(GREEN)Django Operations:$(RESET)"
	@echo "  make migrate          Run Django migrations"
	@echo "  make makemigrations   Create new migrations"
	@echo "  make shell            Open Django shell"
	@echo "  make dbshell          Open PostgreSQL shell"
	@echo "  make createsuperuser  Create Django superuser"
	@echo "  make collectstatic    Collect static files"
	@echo ""
	@echo -e "$(GREEN)Testing & Quality:$(RESET)"
	@echo "  make test             Run all tests"
	@echo "  make test-rbac        Run RBAC tests"
	@echo "  make test-audit       Run audit tests"
	@echo "  make lint             Run ruff linter"
	@echo "  make lint-fix         Run ruff linter (auto-fix)"
	@echo "  make format           Run ruff formatter"
	@echo "  make check            Run all quality checks (lint + format + test)"
	@echo "  make typecheck        Run mypy type checking"
	@echo ""
	@echo -e "$(GREEN)Vault & Keycloak:$(RESET)"
	@echo "  make vault-init       Initialize Vault with Voyager secrets"
	@echo "  make vault-shell      Open Vault shell"
	@echo "  make vault-status     Check Vault status"
	@echo "  make keycloak-import  Import Keycloak realm"
	@echo "  make keycloak-shell   Open Keycloak admin CLI"
	@echo ""
	@echo -e "$(GREEN)Maintenance:$(RESET)"
	@echo "  make clean            Remove stopped containers, unused images"
	@echo "  make clean-all        Full cleanup (containers, volumes, networks, images)"
	@echo "  make prune            Docker system prune"
	@echo "  make backup-db        Backup PostgreSQL database"
	@echo "  make backup-vault     Backup Vault data"
	@echo "  make health           Check health of all services"
	@echo ""

# =============================================================================
# BUILD & DEPLOY
# =============================================================================
.PHONY: build
build: ## Build all Docker images
	@echo -e "$(BLUE)[BUILD]$(RESET) Building Voyager images..."
	$(COMPOSE_CMD) build

.PHONY: build-nc
build-nc: ## Build all images (no cache)
	@echo -e "$(BLUE)[BUILD]$(RESET) Building Voyager images (no cache)..."
	$(COMPOSE_CMD) build --no-cache

.PHONY: up
up: ## Start all services (detached)
	@echo -e "$(GREEN)[UP]$(RESET) Starting Voyager stack..."
	$(COMPOSE_CMD) up -d
	@echo -e "$(GREEN)[UP]$(RESET) Services starting. Run 'make logs' to view logs."
	@echo -e "$(YELLOW)[INFO]$(RESET) API: http://localhost:8000"
	@echo -e "$(YELLOW)[INFO]$(RESET) Keycloak: http://localhost:8080"
	@echo -e "$(YELLOW)[INFO]$(RESET) MinIO Console: http://localhost:9001"

.PHONY: up-fg
up-fg: ## Start all services (foreground)
	@echo -e "$(GREEN)[UP]$(RESET) Starting Voyager stack (foreground)..."
	$(COMPOSE_CMD) up

.PHONY: up-prod
up-prod: ## Start with production overrides
	@echo -e "$(YELLOW)[PROD]$(RESET) Starting Voyager in production mode..."
	$(COMPOSE_PROD_CMD) up -d

.PHONY: down
down: ## Stop all services
	@echo -e "$(RED)[DOWN]$(RESET) Stopping Voyager stack..."
	$(COMPOSE_CMD) down

.PHONY: down-v
down-v: ## Stop all services and remove volumes
	@echo -e "$(RED)[DOWN]$(RESET) Stopping Voyager stack and removing volumes..."
	$(COMPOSE_CMD) down -v

.PHONY: restart
restart: ## Restart all services
	@echo -e "$(YELLOW)[RESTART]$(RESET) Restarting Voyager stack..."
	$(COMPOSE_CMD) restart

.PHONY: pull
pull: ## Pull latest images
	@echo -e "$(BLUE)[PULL]$(RESET) Pulling latest images..."
	$(COMPOSE_CMD) pull

# =============================================================================
# STATUS & LOGS
# =============================================================================
.PHONY: logs
logs: ## View logs (all services)
	$(COMPOSE_CMD) logs -f

.PHONY: logs-api
logs-api: ## View voyager-api logs
	$(COMPOSE_CMD) logs -f voyager-api

.PHONY: logs-worker
logs-worker: ## View celery-worker logs
	$(COMPOSE_CMD) logs -f celery-worker

.PHONY: logs-beat
logs-beat: ## View celery-beat logs
	$(COMPOSE_CMD) logs -f celery-beat

.PHONY: logs-db
logs-db: ## View postgres logs
	$(COMPOSE_CMD) logs -f voyager_postgres

.PHONY: logs-redis
logs-redis: ## View redis logs
	$(COMPOSE_CMD) logs -f voyager_redis

.PHONY: logs-kafka
logs-kafka: ## View kafka logs
	$(COMPOSE_CMD) logs -f voyager_kafka

.PHONY: ps
ps: ## Show running containers
	@echo -e "$(BLUE)[STATUS]$(RESET) Running containers:"
	$(COMPOSE_CMD) ps

.PHONY: top
top: ## Show resource usage
	@echo -e "$(BLUE)[TOP]$(RESET) Resource usage:"
	$(COMPOSE_CMD) top

# =============================================================================
# DJANGO OPERATIONS
# =============================================================================
.PHONY: migrate
migrate: ## Run Django migrations
	@echo -e "$(BLUE)[DJANGO]$(RESET) Running migrations..."
	$(COMPOSE_CMD) exec voyager-api python manage.py migrate

.PHONY: makemigrations
makemigrations: ## Create new migrations
	@echo -e "$(BLUE)[DJANGO]$(RESET) Creating migrations..."
	$(COMPOSE_CMD) exec voyager-api python manage.py makemigrations

.PHONY: shell
shell: ## Open Django shell
	@echo -e "$(BLUE)[DJANGO]$(RESET) Opening Django shell..."
	$(COMPOSE_CMD) exec voyager-api python manage.py shell

.PHONY: dbshell
dbshell: ## Open PostgreSQL shell
	@echo -e "$(BLUE)[DB]$(RESET) Opening PostgreSQL shell..."
	$(COMPOSE_CMD) exec voyager_postgres psql -U voyager -d voyager

.PHONY: createsuperuser
createsuperuser: ## Create Django superuser
	@echo -e "$(BLUE)[DJANGO]$(RESET) Creating superuser..."
	$(COMPOSE_CMD) exec voyager-api python manage.py createsuperuser

.PHONY: collectstatic
collectstatic: ## Collect static files
	@echo -e "$(BLUE)[DJANGO]$(RESET) Collecting static files..."
	$(COMPOSE_CMD) exec voyager-api python manage.py collectstatic --noinput

# =============================================================================
# TESTING & QUALITY
# =============================================================================
.PHONY: test
test: ## Run all tests
	@echo -e "$(GREEN)[TEST]$(RESET) Running all tests..."
	$(COMPOSE_CMD) exec voyager-api pytest apps/ -v --tb=short

.PHONY: test-rbac
test-rbac: ## Run RBAC tests
	@echo -e "$(GREEN)[TEST]$(RESET) Running RBAC tests..."
	$(COMPOSE_CMD) exec voyager-api pytest apps/rbac/tests -v --tb=short

.PHONY: test-audit
test-audit: ## Run audit tests
	@echo -e "$(GREEN)[TEST]$(RESET) Running audit tests..."
	$(COMPOSE_CMD) exec voyager-api pytest apps/audit/tests -v --tb=short

.PHONY: lint
lint: ## Run ruff linter
	@echo -e "$(GREEN)[LINT]$(RESET) Running ruff linter..."
	$(COMPOSE_CMD) exec voyager-api ruff check apps/

.PHONY: lint-fix
lint-fix: ## Run ruff linter (auto-fix)
	@echo -e "$(GREEN)[LINT]$(RESET) Running ruff linter (auto-fix)..."
	$(COMPOSE_CMD) exec voyager-api ruff check apps/ --fix

.PHONY: format
format: ## Run ruff formatter
	@echo -e "$(GREEN)[FORMAT]$(RESET) Running ruff formatter..."
	$(COMPOSE_CMD) exec voyager-api ruff format apps/

.PHONY: typecheck
typecheck: ## Run mypy type checking
	@echo -e "$(GREEN)[TYPE]$(RESET) Running mypy type checking..."
	$(COMPOSE_CMD) exec voyager-api mypy --strict apps/

.PHONY: check
check: lint format test ## Run all quality checks
	@echo -e "$(GREEN)[CHECK]$(RESET) All quality checks passed!"

# =============================================================================
# VAULT & KEYCLOAK
# =============================================================================
.PHONY: vault-init
vault-init: ## Initialize Vault with Voyager secrets
	@echo -e "$(BLUE)[VAULT]$(RESET) Initializing Vault..."
	$(COMPOSE_CMD) exec voyager_vault sh -c "cd /vault/init && chmod +x vault-init.sh && ./vault-init.sh"

.PHONY: vault-shell
vault-shell: ## Open Vault shell
	@echo -e "$(BLUE)[VAULT]$(RESET) Opening Vault shell..."
	$(COMPOSE_CMD) exec -e VAULT_ADDR=http://127.0.0.1:8200 -e VAULT_TOKEN=dev-root-token voyager_vault vault

.PHONY: vault-status
vault-status: ## Check Vault status
	@echo -e "$(BLUE)[VAULT]$(RESET) Checking Vault status..."
	$(COMPOSE_CMD) exec voyager_vault vault status

.PHONY: keycloak-import
keycloak-import: ## Import Keycloak realm (auto-imported on start-dev)
	@echo -e "$(BLUE)[KEYCLOAK]$(RESET) Realm is auto-imported on startup."
	@echo -e "$(YELLOW)[INFO]$(RESET) If you need to re-import:"
	@echo -e "  1. docker compose exec voyager_keycloak /opt/keycloak/bin/kc.sh import --file /opt/keycloak/data/import/voyager-realm.json --override true"

.PHONY: keycloak-shell
keycloak-shell: ## Open Keycloak admin CLI
	@echo -e "$(BLUE)[KEYCLOAK]$(RESET) Opening Keycloak admin CLI..."
	$(COMPOSE_CMD) exec voyager_keycloak /opt/keycloak/bin/kc.sh

# =============================================================================
# MAINTENANCE
# =============================================================================
.PHONY: clean
clean: ## Remove stopped containers, unused images
	@echo -e "$(YELLOW)[CLEAN]$(RESET) Cleaning up..."
	docker container prune -f
	docker image prune -f

.PHONY: clean-all
clean-all: ## Full cleanup (containers, volumes, networks, images)
	@echo -e "$(RED)[CLEAN-ALL]$(RESET) Full cleanup - removing everything..."
	$(COMPOSE_CMD) down -v --rmi all --remove-orphans

.PHONY: prune
prune: ## Docker system prune
	@echo -e "$(YELLOW)[PRUNE]$(RESET) Pruning Docker system..."
	docker system prune -f

.PHONY: backup-db
backup-db: ## Backup PostgreSQL database
	@echo -e "$(BLUE)[BACKUP]$(RESET) Backing up PostgreSQL database..."
	@mkdir -p $(PROJECT_ROOT)/backups
	$(COMPOSE_CMD) exec -T voyager_postgres pg_dump -U voyager voyager | gzip > $(PROJECT_ROOT)/backups/voyager_db_$$(date +%Y%m%d_%H%M%S).sql.gz
	@echo -e "$(GREEN)[BACKUP]$(RESET) Database backup complete"

.PHONY: backup-vault
backup-vault: ## Backup Vault data
	@echo -e "$(BLUE)[BACKUP]$(RESET) Backing up Vault data..."
	@mkdir -p $(PROJECT_ROOT)/backups
	$(COMPOSE_CMD) exec voyager_vault vault operator raft snapshot save /tmp/vault_snapshot.snap
	$(COMPOSE_CMD) cp voyager_vault:/tmp/vault_snapshot.snap $(PROJECT_ROOT)/backups/vault_snapshot_$$(date +%Y%m%d_%H%M%S).snap
	@echo -e "$(GREEN)[BACKUP]$(RESET) Vault backup complete"

.PHONY: health
health: ## Check health of all services
	@echo -e "$(BLUE)[HEALTH]$(RESET) Checking service health..."
	@bash -c '\
	SERVICES="voyager-api voyager_postgres voyager_redis voyager_vault voyager_keycloak voyager_kafka voyager_minio voyager_clickhouse voyager_elasticsearch voyager_qdrant voyager_nginx"; \
	for svc in $$SERVICES; do \
		STATUS=$$($(COMPOSE_CMD) ps -q $$svc | xargs docker inspect -f "{{.State.Health.Status}}" 2>/dev/null || echo "N/A"); \
		if [ "$$STATUS" = "healthy" ]; then \
			echo -e "  $(GREEN)✓$(RESET) $$svc: $$STATUS"; \
		elif [ "$$STATUS" = "N/A" ]; then \
			echo -e "  $(YELLOW)?$(RESET) $$svc: $$STATUS"; \
		else \
			echo -e "  $(RED)✗$(RESET) $$svc: $$STATUS"; \
		fi; \
	done'
