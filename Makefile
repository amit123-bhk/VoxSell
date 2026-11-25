.PHONY: help up down build logs restart test migrate run-local

help:
	@echo "VoxSell Developer Commands:"
	@echo "  make up          - Start all docker containers (backend, postgres, redis, chromadb)"
	@echo "  make down        - Stop and tear down all containers"
	@echo "  make build       - Build docker images from scratch"
	@echo "  make logs        - Tail backend logs in Docker"
	@echo "  make restart     - Restart backend container"
	@echo "  make migrate     - Run database migrations via Alembic"
	@echo "  make test        - Run backend test suite"
	@echo "  make run-local   - Run backend locally with uvicorn (outside docker)"

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f backend

restart:
	docker compose restart backend

migrate:
	cd backend && alembic upgrade head

test:
	cd backend && pytest -v

run-local:
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

dashboard-dev:
	cd frontend && npm run dev

dashboard-build:
	cd frontend && npm run build
