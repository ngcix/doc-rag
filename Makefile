.PHONY: setup-env test lint run build install clean help

help:
	@echo "Available targets:"
	@echo "  setup-env    - Create virtual environment and install dependencies"
	@echo "  test         - Run project tests"
	@echo "  lint         - Run Ruff checks"
	@echo "  run          - Run the application"
	@echo "  build        - Full build: build wheel + pip install"
	@echo "  install      - Install built wheel via pip"
	@echo "  clean        - Remove build and test artifacts"
	@echo "  help         - Show this help message"

setup-env:
	python3 -m venv .venv
	./.venv/bin/pip install --upgrade pip
	./.venv/bin/pip install -e ".[dev]"

test:
	PYTHONPATH=src ./.venv/bin/pytest tests/

lint:
	./.venv/bin/ruff check src tests services tools scripts
	./.venv/bin/ruff format --check src tests services tools scripts
	./.venv/bin/pyright src
	./.venv/bin/python tools/check_file_lengths.py

run:
	PYTHONPATH=src python -m specrag $(ARGS)

build: clean
	python -m build

install:
	./.venv/bin/pip install dist/*.whl

clean:
	rm -rf build/ dist/ *.egg-info
	find src -name "__pycache__" -type d -exec rm -rf {} +
	find src -name "*.egg-info" -type d -exec rm -rf {} +
