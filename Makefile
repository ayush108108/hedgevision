# ==============================================================================
# HedgeVision — Makefile  (Single Source of Truth)
# ==============================================================================
#
#  Local (no Docker):       make install && make dev
#  Docker:                  make up
#  Quick start from zero:   make quickstart
#
# ==============================================================================

.PHONY: help quickstart \
        install install-python install-node \
        dev backend-dev frontend-dev \
        db-init db-bootstrap db-status db-reset db-sync \
        test test-python test-frontend test-coverage \
        lint lint-python lint-frontend format format-python format-frontend \
        clean clean-python clean-node \
        build up down logs restart shell health status \
        build-backend build-frontend build-prod build-no-cache \
        up-attached up-prod down-prod down-volumes \
        logs-backend logs-frontend logs-redis \
        restart-backend restart-frontend shell-frontend \
        docker-clean check-ports stop

# ========================= Variables =========================

PYTHON       ?= python3
PIP          ?= pip
NPM          ?= npm
COMPOSE      := docker compose
COMPOSE_PROD := $(COMPOSE) -f docker-compose.yml -f docker-compose.prod.yml
BACKEND_PORT ?= 8000
FRONTEND_PORT?= 3000

# ========================= Help =========================

help: ## Show available commands
@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
@echo "  HedgeVision — Statistical Arbitrage Platform"
@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
@echo ""
@echo "Quick start (no Docker):"
@echo "  make quickstart       Install deps + seed DB + launch"
@echo ""
@echo "Quick start (Docker):"
@echo "  make up               Build & start all containers"
@echo ""
@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
@echo ""

# ========================= Quick Start =========================

quickstart: install db-init db-bootstrap dev ## One-command setup: install, seed DB, start

# ========================= Installation =========================

install: install-python install-node ## Install all dependencies

install-python: ## Install Python deps (editable)
$(PIP) install -e ".[all]"

install-node: ## Install Node deps
cd frontend-v2 && $(NPM) install

# ========================= Development (local, no Docker) =========================

dev: check-ports ## Start backend + frontend locally (Ctrl+C stops both)
@echo "Backend:  http://localhost:$(BACKEND_PORT)"
@echo "Frontend: http://localhost:$(FRONTEND_PORT)"
@echo "API docs: http://localhost:$(BACKEND_PORT)/docs"
@echo ""
@trap 'kill 0' EXIT; \
$(MAKE) backend-dev & \
$(MAKE) frontend-dev & \
wait

backend-dev: ## Start FastAPI dev server
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT)

frontend-dev: ## Start Vite dev server
cd frontend-v2 && $(NPM) run dev

backend: backend-dev
frontend: frontend-dev

check-ports: ## Ensure dev ports are free
@if lsof -i :$(BACKEND_PORT) -sTCP:LISTEN >/dev/null 2>&1; then \
echo "ERROR: Port $(BACKEND_PORT) is already in use."; \
echo "  Run:  make stop  or  kill $$(lsof -ti :$(BACKEND_PORT))"; \
exit 1; \
fi

stop: ## Kill local dev servers occupying app ports
@-kill $$(lsof -ti :$(BACKEND_PORT)) 2>/dev/null || true
@-kill $$(lsof -ti :$(FRONTEND_PORT)) 2>/dev/null || true
@echo "Ports freed."

# ========================= Database (SQLite) =========================

db-init: ## Create SQLite schema (safe to re-run)
$(PYTHON) scripts/setup/init_db.py

db-bootstrap: ## Seed 2 years of market data + metrics
$(PYTHON) scripts/bootstrap_local_data.py

db-status: ## Show DB tables and row counts
@$(PYTHON) -c "\
import sqlite3, os; \
p = os.environ.get('DB_PATH', 'backend/prices.db'); \
c = sqlite3.connect(p); \
tables = [r[0] for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]; \
[print(f'{t}: {c.execute(f\"SELECT COUNT(*) FROM {t}\").fetchone()[0]}') for t in tables]; \
r = c.execute('SELECT MIN(timestamp), MAX(timestamp) FROM price_history').fetchone(); \
print(f'date range: {r[0]} -> {r[1]}') if r[0] else print('(empty)')"

db-reset: ## Reset database (WARNING: deletes all data)
@read -p "Delete all data and recreate? [y/N] " confirm; \
if [ "$$confirm" = "y" ]; then \
rm -f backend/prices.db; \
$(MAKE) db-init; \
echo "Database reset. Run 'make db-bootstrap' to re-seed."; \
else \
echo "Cancelled."; \
fi

db-sync: ## Fetch latest market data
hedgevision-cli sync

# ========================= Tests =========================

test: test-python test-frontend ## Run all tests

test-python: ## Run Python tests with coverage
pytest tests/ -v --cov=hedgevision --cov-report=term-missing

test-frontend: ## Run frontend tests
cd frontend-v2 && $(NPM) test

test-coverage: ## HTML coverage report
pytest tests/ --cov=hedgevision --cov-report=html
@echo "Report: htmlcov/index.html"

# ========================= Lint & Format =========================

lint: lint-python lint-frontend ## Lint all code

lint-python: ## Lint Python (black + isort + flake8)
black --check --line-length 100 .
isort --check --profile black --line-length 100 .
flake8 hedgevision backend tests

lint-frontend: ## Lint frontend (eslint)
cd frontend-v2 && $(NPM) run lint

format: format-python format-frontend ## Auto-format all code

format-python: ## Format Python (black + isort)
black --line-length 100 .
isort --profile black --line-length 100 .

format-frontend: ## Format frontend
cd frontend-v2 && $(NPM) run lint -- --fix

# ========================= Clean =========================

clean: clean-python clean-node ## Remove build artifacts

clean-python:
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
rm -rf .pytest_cache dist build htmlcov .coverage *.egg-info

clean-node:
rm -rf frontend-v2/node_modules frontend-v2/dist frontend-v2/.vite

# ========================= Docker =========================

build: ## Build all Docker images
$(COMPOSE) build

build-backend: ## Build backend image
$(COMPOSE) build backend

build-frontend: ## Build frontend image
$(COMPOSE) build frontend

build-prod: ## Build production images
$(COMPOSE_PROD) build

build-no-cache: ## Build without cache
$(COMPOSE) build --no-cache

up: ## Start all services (Docker, detached)
$(COMPOSE) up -d

up-attached: ## Start all services (foreground)
$(COMPOSE) up

up-prod: ## Start in production mode
$(COMPOSE_PROD) up -d

down: ## Stop all services
$(COMPOSE) down

down-prod: ## Stop production services
$(COMPOSE_PROD) down

down-volumes: ## Stop and delete volumes (WARNING: data loss)
$(COMPOSE) down -v

logs: ## Tail all container logs
$(COMPOSE) logs -f

logs-backend:
$(COMPOSE) logs -f backend

logs-frontend:
$(COMPOSE) logs -f frontend

logs-redis:
$(COMPOSE) logs -f redis

restart: ## Restart all containers
$(COMPOSE) restart

restart-backend:
$(COMPOSE) restart backend

restart-frontend:
$(COMPOSE) restart frontend

shell: ## Shell into backend container
$(COMPOSE) exec backend /bin/bash

shell-frontend:
$(COMPOSE) exec frontend /bin/sh

status: ## Show container status
$(COMPOSE) ps

health: ## Check service health
@curl -sf http://localhost:$(BACKEND_PORT)/health && echo " Backend OK" || echo "Backend unreachable"
@curl -sf http://localhost:$(FRONTEND_PORT)/ >/dev/null && echo "Frontend OK" || echo "Frontend unreachable"

docker-clean: ## Stop containers + prune Docker artifacts
$(COMPOSE) down -v --remove-orphans
docker system prune -f

# ========================= Default =========================

.DEFAULT_GOAL := help
