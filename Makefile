# ==============================================================================
# HedgeVision — Unified Makefile (Local + Docker)
# ==============================================================================
# Quick Start:
#   make install       # Install Python + Node dependencies
#   make dev           # Start backend + frontend in dev mode
#   make test          # Run all tests
#   make lint          # Lint and format all code
# ==============================================================================

.PHONY: help install dev clean test lint format \
        backend frontend backend-dev frontend-dev \
        db-init db-status db-reset db-sync \
        build up down logs restart shell health \
        build-backend build-frontend up-prod down-prod

# ========================= Help & Info =========================

help: ## Show available commands
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  HedgeVision - Statistical Arbitrage Platform"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  make install    - Install all dependencies"
	@echo "  make dev        - Start backend + frontend"
	@echo "  make test       - Run test suite"
	@echo ""
	@echo "📋 All Commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ========================= Installation =========================

install: install-python install-node ## Install all dependencies (Python + Node)
	@echo "✅ All dependencies installed. Run 'make dev' to start."

install-python: ## Install Python dependencies
	@echo "📦 Installing Python dependencies..."
	pip install -e ".[all]"
	@echo "✅ Python dependencies installed."

install-node: ## Install Node dependencies
	@echo "📦 Installing Node dependencies..."
	cd frontend-v2 && npm install
	@echo "✅ Node dependencies installed."

# ========================= Development =========================

dev: ## Start backend + frontend in parallel (Ctrl+C to stop both)
	@echo "🚀 Starting HedgeVision in development mode..."
	@echo "   Backend:  http://localhost:8000"
	@echo "   Frontend: http://localhost:3000"
	@echo "   Docs:     http://localhost:8000/docs"
	@echo ""
	@trap 'kill 0' EXIT; \
	$(MAKE) backend-dev & \
	$(MAKE) frontend-dev & \
	wait

backend-dev: ## Start backend API server (FastAPI)
	@echo "🔧 Starting backend on http://localhost:8000 ..."
	uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000

frontend-dev: ## Start frontend dev server (Vite)
	@echo "🎨 Starting frontend on http://localhost:3000 ..."
	cd frontend-v2 && npm run dev

backend: backend-dev ## Alias for backend-dev
frontend: frontend-dev ## Alias for frontend-dev

# ========================= Database =========================

db-init: ## Initialize SQLite database schema
	@echo "🗄️  Initializing database..."
	python scripts/setup/init_db.py
	@echo "✅ Database initialized."

db-status: ## Check database status
	@echo "📊 Database Status:"
	sqlite3 backend/prices.db "SELECT name FROM sqlite_master WHERE type='table';" | head -10
	@echo ""
	@echo "Asset count:"
	sqlite3 backend/prices.db "SELECT COUNT(*) FROM assets;"
	@echo "Price history records:"
	sqlite3 backend/prices.db "SELECT COUNT(*) FROM price_history;"

db-reset: ## Reset database (⚠️  WARNING: Deletes all data)
	@echo "⚠️  Resetting database..."
	@read -p "Are you sure? This will delete all data. [y/N] " confirm; \
	if [ "$$confirm" = "y" ]; then \
		rm -f backend/prices.db; \
		python scripts/setup/init_db.py; \
		echo "✅ Database reset complete."; \
	else \
		echo "❌ Cancelled."; \
	fi

db-sync: ## Sync latest market data
	@echo "📈 Syncing market data..."
	hedgevision-cli sync
	@echo "✅ Sync complete."

# ========================= Testing =========================

test: test-python test-frontend ## Run all tests (Python + Frontend)

test-python: ## Run Python tests
	@echo "🧪 Running Python tests..."
	pytest tests/ -v --cov=hedgevision --cov-report=term-missing

test-frontend: ## Run frontend tests
	@echo "🧪 Running frontend tests..."
	cd frontend-v2 && npm test

test-coverage: ## Generate test coverage report
	@echo "📊 Generating coverage report..."
	pytest tests/ --cov=hedgevision --cov-report=html
	@echo "✅ Coverage report: htmlcov/index.html"

# ========================= Linting & Formatting =========================

lint: lint-python lint-frontend ## Lint all code

lint-python: ## Lint Python code
	@echo "🔍 Linting Python..."
	black --check --line-length 100 .
	isort --check --profile black --line-length 100 .
	flake8 hedgevision backend tests
	@echo "✅ Python linting passed."

lint-frontend: ## Lint frontend code
	@echo "🔍 Linting frontend..."
	cd frontend-v2 && npm run lint
	@echo "✅ Frontend linting passed."

format: format-python format-frontend ## Format all code

format-python: ## Format Python code with Black + isort
	@echo "🎨 Formatting Python..."
	black --line-length 100 .
	isort --profile black --line-length 100 .
	@echo "✅ Python formatted."

format-frontend: ## Format frontend code
	@echo "🎨 Formatting frontend..."
	cd frontend-v2 && npm run lint -- --fix
	@echo "✅ Frontend formatted."

# ========================= Cleanup =========================

clean: clean-python clean-node ## Clean all build artifacts

clean-python: ## Clean Python cache and build files
	@echo "🧹 Cleaning Python artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache dist build htmlcov .coverage
	@echo "✅ Python artifacts cleaned."

clean-node: ## Clean Node modules and build files
	@echo "🧹 Cleaning Node artifacts..."
	rm -rf frontend-v2/node_modules frontend-v2/dist frontend-v2/.vite
	@echo "✅ Node artifacts cleaned."

# ========================= Docker Commands =========================

COMPOSE       := docker compose
COMPOSE_PROD  := $(COMPOSE) -f docker-compose.yml -f docker-compose.prod.yml

docker-help: ## Show Docker-specific commands
	@echo "🐳 Docker Commands:"
	@grep -E '^(build|up|down|logs|restart|shell|health|docker-).*:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ========================= Build =========================

build: ## Build all Docker containers
	$(COMPOSE) build

build-backend: ## Build backend Docker container only
	$(COMPOSE) build backend

build-frontend: ## Build frontend Docker container only
	$(COMPOSE) build frontend

build-prod: ## Build for production
	$(COMPOSE_PROD) build

build-no-cache: ## Build without layer cache
	$(COMPOSE) build --no-cache

# ========================= Docker Run =========================

up: ## Start all Docker services (detached)
	$(COMPOSE) up -d

up-attached: ## Start all Docker services (foreground)
	$(COMPOSE) up

up-prod: ## Start in production mode
	$(COMPOSE_PROD) up -d

# ========================= Docker Stop =========================

down: ## Stop all Docker services
	$(COMPOSE) down

down-prod: ## Stop production services
	$(COMPOSE_PROD) down

down-volumes: ## Stop and remove volumes (⚠️  deletes data)
	$(COMPOSE) down -v

# ========================= Docker Logs =========================

logs: ## Tail all container logs
	$(COMPOSE) logs -f

logs-backend: ## Tail backend logs
	$(COMPOSE) logs -f backend

logs-frontend: ## Tail frontend logs
	$(COMPOSE) logs -f frontend

logs-redis: ## Tail Redis logs
	$(COMPOSE) logs -f redis

# ========================= Docker Management =========================

restart: ## Restart all services
	$(COMPOSE) restart

restart-backend: ## Restart backend only
	$(COMPOSE) restart backend

restart-frontend: ## Restart frontend only
	$(COMPOSE) restart frontend

shell: ## Open shell in backend container
	$(COMPOSE) exec backend /bin/bash

shell-frontend: ## Open shell in frontend container
	$(COMPOSE) exec frontend /bin/sh

status: ## Show running containers
	$(COMPOSE) ps

health: ## Check service health
	@echo "🏥 Checking service health..."
	@curl -sf http://localhost:8000/health || echo "❌ Backend unreachable"
	@curl -sf http://localhost:3000/ > /dev/null && echo "✅ Frontend healthy" || echo "❌ Frontend unreachable"

docker-clean: ## Stop containers and clean Docker artifacts
	$(COMPOSE) down -v --remove-orphans
	docker system prune -f

# ========================= End =========================

.DEFAULT_GOAL := help


down-volumes: ## Stop and remove volumes (WARNING: deletes data)
	$(COMPOSE) down -v

# ========================= Logs =========================

logs: ## Tail all logs
	$(COMPOSE) logs -f

logs-backend: ## Tail backend logs
	$(COMPOSE) logs -f backend

logs-frontend: ## Tail frontend logs
	$(COMPOSE) logs -f frontend

logs-redis: ## Tail Redis logs
	$(COMPOSE) logs -f redis

# ========================= Status =========================

status: ## Show service status
	$(COMPOSE) ps

health: ## Check health of running services
	@printf "Backend:  " && curl -sf http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "unavailable"
	@printf "Frontend: " && curl -so /dev/null -w "HTTP %{http_code}\n" http://localhost:8080/ 2>/dev/null || echo "unavailable"
	@printf "Redis:    " && docker exec hedgevision-redis redis-cli ping 2>/dev/null || echo "unavailable"

# ========================= Debug =========================

shell: ## Shell into backend container
	$(COMPOSE) exec backend /bin/bash

shell-frontend: ## Shell into frontend container
	$(COMPOSE) exec frontend /bin/sh

# ========================= Maintenance =========================

restart: ## Restart all services
	$(COMPOSE) restart

restart-backend: ## Restart backend only
	$(COMPOSE) restart backend

clean: ## Prune stopped containers and dangling images
	docker system prune -f
	$(COMPOSE) down --rmi local --remove-orphans

# ========================= Local Dev (no Docker) =========================

dev-backend: ## Run backend locally (no Docker)
	uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Run frontend locally (no Docker)
	cd frontend-v2 && npm run dev
