.PHONY: clean

PYTHON_INTERPRETER=python3

SOURCE_DIR=./src
SOURCE_PATH=./src/gdf
TESTS_DIR=./tests
PYTEST_LOG_LEVEL=DEBUG
PYTEST_COV_MIN=0

# Load all environment variables from .env
# so that they are preloaded before running any command here
ifneq (,$(wildcard ./.env))
include .env
export
endif

activate:
	@. .venv/bin/activate && echo "Your virtual environment is activated."

# +++++++ +++++++ +++++++
# Housekeeping
# +++++++ +++++++ +++++++
clean:
	find . -type f -name ".DS_Store" -exec rm -rf {} +
	find . -type f -name "*.py[cod]" -exec rm -rf {} +
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ipynb_checkpoints" -exec rm -rf {} +

isort:
	uv run isort .

black:
	uv run black .

flake8:
# Configuration cotrolled by .flake8
	uv run flake8

pylint:
# Configuration cotrolled by .pylintrc
	uv run pylint **/*.py

format: isort black flake8 pylint


# +++++++ +++++++ +++++++
# Local development setup
# +++++++ +++++++ +++++++
setup-local-dev:
	mkdir -p logs
	uv venv
	uv pip install -e .[dev]
	uv run pre-commit install