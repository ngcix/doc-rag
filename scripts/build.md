# Build

> [!NOTE]
> To workaround encrypted documents in windows, we will rename `specrag.exe` to `python.exe`
>
> Currently only built successfully on windows.
> The dependencies for Linux currently is too large (over 7.5G) and we don't know why, so packaging will failed.

The script `setup.py` will compile the packages inside `src` into binary library.

## 0. TLDR

For windows powershell, run these 

```pwsh
. .venv/scripts/Activate.ps1
python scripts/setup.py build_ext
cp -r build/lib.win-amd64-cpython-313/src .venv/Lib/site-packages
python scripts/build.py
```

## 1. Setup

```sh
python scripts/setup.py build_ext
cp -r build/lib.linux-x86_64-cpython-313/src .venv/lib/python3.13/site-packages/ # Linux
cp -r build/lib.win-amd64-cpython-313/src .venv/Lib/site-packages # Windows (pwsh)
```

Binary output will locate in a folder like `./build/lib.win-amd64-cpython-311`.

This compiles all Python files in the `src` directory into optimized Cython extensions, which can provide performance improvements over pure Python code.

**Security Note**: Cython compilation helps protect source code by converting Python files into compiled binary extensions (.pyd files on Windows, .so files on Linux/Mac). While not completely secure (determined reverse engineers could potentially extract some information), it provides a reasonable level of protection against casual inspection of the source code.

**Update Procedure**: Before building, copy the compiled library folder to the `.venv/Lib/site-packages/` folder to update the library in your virtual environment. For standalone applications, also copy to the `_internal` folder.

## 2. PyInstaller

The script `build.py` creates a standalone executable using PyInstaller.

```sh
python scripts/build.py
```

This will generate a standalone executable in the `dist/` directory named `RagCLI.exe` (on Windows) or `RagCLI` (on Linux/Mac).

The build process includes:

- Bundling all dependencies
- Including required data files
- Packaging the specrag application
- Creating a distributable executable

## 3. Test

To run the built executable:

```sh
# Windows
dist/specrag/specrag.exe

# Linux/Mac
./dist/specrag/specrag
```

The executable includes everything needed to run the RAG system without requiring a Python installation or virtual environment.

