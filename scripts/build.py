import PyInstaller.__main__
import time
import os
import sys
import shutil
import tempfile
from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_all,
    collect_submodules,
)
from datetime import timedelta
import Cython.Build
import setuptools


def compile_with_cython(source_dir, build_dir=None):
    """
    Compile Python files to C extensions using Cython for obfuscation
    """
    print("Compiling Python files with Cython for obfuscation...")

    if build_dir is None:
        build_dir = tempfile.mkdtemp(prefix="cython_build_")

    source_path = Path(source_dir)
    build_path = Path(build_dir)

    # Find all Python files to compile (exclude main.py and __init__.py)
    py_files = []
    for py_file in source_path.rglob("*.py"):
        # Skip main.py (entry point) and __init__.py files
        if py_file.name not in ["main.py", "__init__.py"]:
            # Calculate relative path
            rel_path = py_file.relative_to(source_path)
            py_files.append(str(py_file))
            print(f"  Found module to compile: {rel_path}")

    if not py_files:
        print("No Python files found for Cython compilation")
        return build_dir

    print(f"Found {len(py_files)} Python modules to compile (excluding main.py)")

    # Cython compilation options for security
    ext_modules = Cython.Build.cythonize(
        py_files,
        compiler_directives={
            "language_level": 3,
            "boundscheck": False,
            "wraparound": False,
            "initializedcheck": False,
            "cdivision": True,
            "embedsignature": False,  # Hide function signatures
            "annotation_typing": False,
        },
        force=True,
        quiet=False,
        build_dir=str(build_path / "cython_build"),
    )

    # Build the extensions
    setuptools.setup(
        script_args=[
            "build_ext",
            "--inplace",
            "--build-temp=" + str(build_path / "build_temp"),
        ],
        ext_modules=ext_modules,
        script_name="setup.py",
    )

    print("Cython compilation completed")
    return build_dir


def create_secure_build():
    """
    Create a secure build using PyInstaller with Cython obfuscation
    """
    start_time = time.perf_counter()
    PROJECT_NAME = "simpleRAG"

    # Create temporary directory for Cython compilation
    cython_build_dir = tempfile.mkdtemp(prefix="secure_build_")

    try:
        # Step 1: Compile source code with Cython
        print("Step 1: Compiling source code with Cython...")
        compile_dir = compile_with_cython("./src", cython_build_dir)

        # Step 2: Prepare PyInstaller arguments with security options
        print("Step 2: Preparing PyInstaller build with security options...")

        packages = [
            "docling",
            "docling_core",
            "docling_ibm_models",
            "docling_parse",
            "transformers",
            "sentence_transformers",
        ]

        datas = []
        binaries = []
        hidden_imports = []

        for pkg in packages:
            try:
                d, b, h = collect_all(pkg)
                datas += d
                binaries += b
                hidden_imports += h
                print(
                    f"Collected from {pkg}: {len(d)} datas, {len(b)} binaries, {len(h)} hidden imports"
                )
            except Exception as e:
                print(f"Warning: collect_all failed for {pkg}: {e}")

        # Auto-detect and add hidden imports for all local modules in src directory
        src_modules = []
        src_path = Path("./src")

        for py_file in src_path.rglob("*.py"):
            if py_file.name not in ["main.py", "__init__.py"]:
                # Convert file path to module import path
                rel_path = py_file.relative_to(src_path)
                module_path = str(rel_path.with_suffix("")).replace(os.sep, ".")
                src_modules.append(module_path)

        hidden_imports += src_modules
        print(f"Auto-detected {len(src_modules)} local module hidden imports:")
        for module in src_modules:
            print(f"  - {module}")

        hidden_imports += [
            "langchain.text_splitter",
            "langchain_core.documents",
            "langchain.schema",
            "langchain.docstore",
            "langchain.docstore.document",
            "sentence_transformers.SentenceTransformer",
            "transformers.integrations",
            "transformers.utils",
        ]

        try:
            import docling_parse

            res_src = Path(docling_parse.__file__).parent / "pdf_resources_v2"
            if res_src.exists():
                datas.append((str(res_src), "docling_parse/pdf_resources_v2"))
                print("Added pdf_resources_v2 manually")
        except ImportError:
            print("Warning: docling_parse not found – skipping pdf_resources_v2")

        hidden_imports += collect_submodules("transformers")

        metadata_packages = [
            "docling",
            "docling-core",
            "docling-ibm-models",
            "docling-parse",
            "transformers",
            "sentence-transformers",
            "sentence_transformers",
            "torch",
            "tokenizers",
            "huggingface_hub",
            "safetensors",
            "langchain",
            "langchain-core",
            "langchain-community",
            "langchain-text-splitters",
        ]

        # Step 3: Build with PyInstaller with security options
        print("Step 3: Building with PyInstaller...")

        args = [
            "./src/main.py",
            "-D",  # Directory mode (more secure than single file)
            f"-n={PROJECT_NAME}",
            "--clean",
            "-y",
            "--noupx",  # Disable UPX (faster build, optional)
            "--optimize=2",
            # Security options
            "--noconfirm",  # Don't ask for confirmation
            "--strip",  # Strip debug information
            "--exclude-module=tkinter",  # Exclude unused modules
            "--exclude-module=matplotlib",
            "--exclude-module=PIL",
            *[f"--copy-metadata={pkg}" for pkg in metadata_packages],
            *[f"--add-data={src}{os.pathsep}{dest}" for src, dest in datas],
            *[f"--add-binary={src}{os.pathsep}{dest}" for src, dest in binaries],
            *[f"--hidden-import={hi}" for hi in hidden_imports],
        ]

        print("PyInstaller command:")
        for arg in args:
            print(f"  {arg}")

        PyInstaller.__main__.run(args)

        # Step 4: Post-build security enhancements
        print("Step 4: Applying post-build security enhancements...")

        dist_dir = Path(f"./dist/{PROJECT_NAME}")
        if dist_dir.exists():
            # Remove .py files if any exist in the distribution
            for py_file in dist_dir.rglob("*.py"):
                try:
                    py_file.unlink()
                    print(f"Removed source file: {py_file}")
                except Exception as e:
                    print(f"Warning: Could not remove {py_file}: {e}")

            # Set restrictive permissions on Unix-like systems
            if os.name != "nt":
                try:
                    os.chmod(dist_dir, 0o755)
                    for item in dist_dir.rglob("*"):
                        if item.is_file():
                            os.chmod(item, 0o644)
                        elif item.is_dir():
                            os.chmod(item, 0o755)
                    print("Set restrictive file permissions")
                except Exception as e:
                    print(f"Warning: Could not set permissions: {e}")

        print("Secure build completed successfully!")

    except Exception as e:
        print(f"Build failed: {e}")
        raise
    finally:
        # Clean up temporary directories
        try:
            if os.path.exists(cython_build_dir):
                shutil.rmtree(cython_build_dir)
                print("Cleaned up temporary build directories")
        except Exception as e:
            print(f"Warning: Could not clean up temp directory: {e}")

    end_time = time.perf_counter()
    execution_time = end_time - start_time
    time_str = str(timedelta(seconds=int(execution_time)))
    print(f"Total secure build time: {time_str}")


def check_dependencies():
    """
    Check if required dependencies are installed
    """
    required_packages = ["PyInstaller", "Cython", "setuptools"]
    missing_packages = []

    for package in required_packages:
        try:
            __import__(package.lower())
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"Missing required packages: {', '.join(missing_packages)}")
        print("Please install them using: pip install " + " ".join(missing_packages))
        return False

    return True


if __name__ == "__main__":
    print("Starting secure build process...")
    print("=" * 50)

    # if not check_dependencies():
    #     sys.exit(1)

    try:
        create_secure_build()
        print("=" * 50)
        print("Secure build completed successfully!")
        print(
            "The application has been obfuscated using Cython and packaged with PyInstaller."
        )
        print("This provides enhanced code protection against reverse engineering.")
    except KeyboardInterrupt:
        print("\nBuild interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nBuild failed with error: {e}")
        sys.exit(1)
