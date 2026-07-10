.PHONY: dev test lint

dev:
	docker compose up --build

test:
	cd backend && .venv/Scripts/python.exe -m pytest -q
	cd frontend && npm test

lint:
	cd backend && .venv/Scripts/python.exe -m ruff check app tests
	cd frontend && npm run typecheck
	cd frontend && npm run lint
