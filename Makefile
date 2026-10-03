.PHONY: help up down restart logs test test-backend migrate seed clean

help:
	@echo "ASTRA Development Commands:"
	@echo "  make up           Start all Docker Compose services"
	@echo "  make down         Stop all Docker Compose services"
	@echo "  make restart      Restart all Docker Compose services"
	@echo "  make logs         Tail logs for all services"
	@echo "  make test-backend Run backend Pytest unit and integration tests"
	@echo "  make migrate      Run Alembic migrations head"
	@echo "  make clean        Remove build artifacts and cache files"

up:
	docker compose up --build -d

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

test-backend:
	cd backend && pytest -v

migrate:
	docker compose exec backend alembic upgrade head

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
