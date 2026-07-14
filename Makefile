.PHONY: setup-env test compile run run-exec build build-only build-exec install clean clean-exec clean-src help

help:
	@echo "Available targets:"
	@echo "  setup-env    - Create virtual environment and install dependencies"
	@echo "  test         - Run project tests"
	@echo "  compile      - Compile Cython extensions in-place (development)"
	@echo "  run          - Run the application"
	@echo "  run-exec     - Run the bundled executable"
	@echo "  build        - Full build: build wheel + pip install"
	@echo "  build-only   - Build wheel only (standard)"
	@echo "  build-exec   - Build and run PyInstaller executable"
	@echo "  install      - Install built wheel via pip"
	@echo "  clean        - Nuclear clean: remove everything"
	@echo "  clean-exec   - Light clean: remove only build output and dist"
	@echo "  clean-src    - Clean only compiled extensions (.c, .so, .pyd)"
	@echo "  help         - Show this help message"

setup-env:
	python3 -m venv .venv
	./.venv/bin/pip install --upgrade pip
	./.venv/bin/pip install .
	./.venv/bin/pip install pytest

test:
	PYTHONPATH=src ./.venv/bin/pytest tests/

compile: clean-src
	python setup.py build_ext --inplace

run:
	PYTHONPATH=src python -m specrag $(ARGS)

run-exec:
	./dist/specrag/specrag

build: build-only install

build-only: clean
	python -m build

build-exec:
	pyinstaller specrag.spec

install:
	./.venv/bin/pip install dist/*.whl

clean:
	rm -rf build/ dist/ *.egg-info
	find src -name "__pycache__" -type d -exec rm -rf {} +
	find src -name "*.egg-info" -type d -exec rm -rf {} +

clean-exec:
	rm -rf build/ dist/

clean-src:
	find src -name "*.c" -type f -delete
	find src -name "*.so" -type f -delete
	find src -name "*.pyd" -type f -delete
	find src -name "__pycache__" -type d -exec rm -rf {} +
