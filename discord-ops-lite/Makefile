lint:
	python -m ruff check .
	python -m ruff format --check .

test:
	python -m pytest -q

build:
	docker compose build dayz-discord-bot

deploy:
	docker compose up -d mysql dayz-discord-bot

logs:
	docker compose logs -f dayz-discord-bot

down:
	docker compose down
