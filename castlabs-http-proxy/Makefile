.PHONY: build run test

build:
	docker compose build

run:
	HTTP_PORT=$${HTTP_PORT:-8000} docker compose up

test:
	pytest -v
