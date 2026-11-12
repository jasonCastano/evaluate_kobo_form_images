# =============================================================================
# Evaluate Kobo Form Images — task automation
# =============================================================================

SHELL := /bin/bash

# Always use the project's own virtual environment, even if a global
# UV_PROJECT_ENVIRONMENT points somewhere else on this machine.
export UV_PROJECT_ENVIRONMENT := .venv

.DEFAULT_GOAL := help
.PHONY: help install dev run pre-commit-install pre-commit lint format format-check typecheck test check build clean clean-cache

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Sync the virtual environment and install dependencies
	uv sync

dev: install pre-commit-install ## Prepare the development environment (sync + hooks)

run: ## Start the image evaluation app (Streamlit)
	uv run evaluate-kobo-images

pre-commit-install: ## Install the pre-commit hooks in the local repository
	uv run pre-commit install

pre-commit: ## Run every pre-commit hook on the repository
	uv run pre-commit run --all-files

lint: ## Run Ruff (lint)
	uv run ruff check .

format: ## Format the code with Ruff
	uv run ruff format .

format-check: ## Check formatting without changing files
	uv run ruff format --check .

typecheck: ## Type-check with ty (Astral)
	uv run ty check

test: ## Run the test suite
	uv run pytest

check: lint format-check typecheck test ## Full verification (lint + format + types + tests)

build: ## Build the package (sdist + wheel)
	uv build

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache dist build htmlcov .coverage
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

clean-cache: ## Remove the downloaded image cache
	rm -rf .cache/images
