.PHONY: up down logs test seed eval

up:
	cp -n .env.example .env || true
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f api worker

test:
	pytest -q

seed:
	python scripts/seed.py

eval:
	python scripts/run_evals.py
