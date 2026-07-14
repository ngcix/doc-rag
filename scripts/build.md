# Build Guide

This guide explains how to build and package SpecRAG. We use a `Makefile` to automate the complex build process, including Cython compilation and PyInstaller bundling.

## 🚀 Quick Start

If you have `make` installed, you can perform all build operations with a single command:

```bash
# 1. Setup environment and install dependencies
make setup-env

# 2. Compile Python files to Cython binaries (Performance & Protection)
make compile

# 3. Create a distributable standalone executable
make build-exec

# 4. Run the executable
./dist/specrag/specrag
```

---

## 🛠️ Detailed Build Pipeline

### 1. Environment Setup (`make setup-env`)
Creates a virtual environment and installs the project in editable mode along with development dependencies.

### 2. Cython Compilation (`make compile`)
Compiles all `.py` files in the `src/` directory into optimized binary extensions (`.so` on Linux, `.pyd` on Windows).

**Why use Cython?**
- **Performance**: Provides significant speedups for compute-intensive tasks.
- **Source Protection**: Converts human-readable Python code into compiled binaries, making casual reverse-engineering much harder.

### 3. Wheel Distribution (`make build`)
Uses the standard `build` package to create `.whl` and `.tar.gz` files in the `dist/` directory. This is the standard way to distribute Python packages.

### 4. Standalone Executable (`make build-exec`)
Uses PyInstaller and `specrag.spec` to bundle the entire application, including the Python interpreter and all dependencies (torch, transformers, etc.), into a single folder in `dist/specrag/`.

The build process automatically handles:
- **Heavy Dependencies**: Uses `collect_all` to ensure `torch` and `transformers` are fully bundled.
- **Metadata**: Copies required package metadata for runtime compatibility.
- **Hidden Imports**: Resolves complex dynamic imports from `langchain` and `chromadb`.

---

## 🧹 Cleaning Up

To remove build artifacts and start fresh:

- `make clean-src`: Remove only compiled Cython files and `__pycache__`.
- `make clean-exec`: Remove only `build/` and `dist/` directories.
- `make clean`: Full nuclear clean (remove everything).
