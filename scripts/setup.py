from setuptools import setup, find_packages, Extension
from Cython.Build import cythonize
import glob
import os


def get_export_name(file_path):
    relative_path = os.path.relpath(file_path, SRC_DIR)
    module_name = os.path.splitext(relative_path)[0].replace(os.path.sep, ".")
    return f"specrag.{module_name}"


BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")

src_pattern = os.path.join(SRC_DIR, "**", "*.py")
all_py_files = glob.glob(src_pattern, recursive=True)

extensions = []
for file in all_py_files:
    module_name = get_export_name(file)
    if module_name.endswith("__main__"):
        if not module_name.count(".") == 1:  # Top-level __main__.py
            continue

    extensions.append(Extension(module_name, [file]))

setup(
    name="specrag",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            "language_level": "3",
            "embedsignature": True,
        },
        build_dir="build/cython",
    ),
    zip_safe=False,
)
