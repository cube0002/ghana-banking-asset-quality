.PHONY: install install-dev test lint format clean notebooks help

help:
	@echo "Available commands:"
	@echo "  make install       - Install package in production mode"
	@echo "  make install-dev   - Install package with dev dependencies"
	@echo "  make test          - Run test suite with coverage"
	@echo "  make lint          - Run linters (flake8, mypy)"
	@echo "  make format        - Auto-format code with black"
	@echo "  make clean         - Remove cache, build artifacts"
	@echo "  make notebooks     - Start Jupyter Lab"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --cov=src/ghana_banking --cov-report=html

lint:
	flake8 src/ tests/
	mypy src/ || true

format:
	black src/ tests/ notebooks/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache htmlcov build dist *.egg-info

notebooks:
	jupyter lab notebooks/
