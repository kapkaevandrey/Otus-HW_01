## ---------------------------------------------------------------
## Logviewer-backend
## ---------------------------------------------------------------
## Local environment commands:
## ---------------------------------------------------------------

.DEFAULT_GOAL := run_tests

## run:       start app in docker
run:
	docker-compose up

down:
	docker-compose down --remove-orphans


## pytest:    run pytest
pytest: down
	docker-compose run app ./docker-entrypoint.sh pytest

## coverage: Check coverage
coverage:
	docker-compose run --rm app ./docker-entrypoint.sh coverage


## check_code        Checks code with linter
check_code:
	docker-compose run app ./docker-entrypoint.sh check_code

## format_code:      Apply formatters
format_code:
	docker-compose run app ./docker-entrypoint.sh format_code


## migration: create alembic migration with revision name in {num_by_day}_{revision_comment} format
migration:
	@read -p "Enter revision name in {num_by_day}_{revision_comment} format: " revision_name; \
	docker-compose run app alembic revision --autogenerate -m $$revision_name

## revision:
revision:
	 @read -p "Enter revision name in {num_by_day}_{revision_comment} format: " revision_name; \
 	docker-compose run app alembic revision -m $$revision_name

## upgrade:   upgrade alembic migrations
upgrade:
	docker-compose run app alembic upgrade head

## downgrade: downgrade alembic migrations
downgrade:
	docker-compose run app alembic downgrade base


## ---------------------------------------------------------------
## Requirements managing: uv required to be installed
## ---------------------------------------------------------------

install:
	uv sync --group dev

update:
	uv sync --upgrade --group dev

help:
	@sed -ne '/@sed/!s/## //p' $(MAKEFILE_LIST)
