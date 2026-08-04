.PHONY: install lint test run compose-up compose-down

install:
	python -m pip install -e ".[dev]"

lint:
	ruff check .

test:
	pytest

run:
	uvicorn energy_flex_trust.api:app --reload

compose-up:
	docker compose up --build

compose-down:
	docker compose down

