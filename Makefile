.PHONY: dev test

dev:
	docker compose up --build

test:
	cd backend && pytest
	cd frontend && npm test
