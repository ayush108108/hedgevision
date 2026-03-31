# ==============================================================================
# HedgeVision — Docker Makefile
# ==============================================================================

.PHONY: help build up down logs restart clean test shell \
        build-backend build-frontend up-prod down-prod \
        logs-backend logs-frontend logs-redis status health

COMPOSE       := docker compose
COMPOSE_PROD  := $(COMPOSE) -f docker-compose.yml -f docker-compose.prod.yml

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ========================= Build =========================

build: ## Build all containers
	$(COMPOSE) build

build-backend: ## Build backend only
	$(COMPOSE) build backend

build-frontend: ## Build frontend only
	$(COMPOSE) build frontend

build-prod: ## Build for production
	$(COMPOSE_PROD) build

build-no-cache: ## Build without layer cache
	$(COMPOSE) build --no-cache

# ========================= Run =========================

up: ## Start all services (detached)
	$(COMPOSE) up -d

up-attached: ## Start all services (foreground)
	$(COMPOSE) up

up-prod: ## Start in production mode
	$(COMPOSE_PROD) up -d

# ========================= Stop =========================

down: ## Stop all services
	$(COMPOSE) down

down-prod: ## Stop production services
	$(COMPOSE_PROD) down

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
