from setuptools import setup, Extension, find_packages
from Cython.Build import cythonize
import glob
import os

all_py_files = glob.glob("src/**/*.py", recursive=True)

exclude_files = {
    "src/main.py",
}

modules_to_compile = [
    f for f in all_py_files if os.path.normpath(f) not in exclude_files
]

print("Modules compile by Cython:")
for m in modules_to_compile:
    print("  ", m)
print("Modules exclude:")
for e in exclude_files:
    if os.path.exists(e):
        print("  ", e)

ext_modules = cythonize(
    modules_to_compile,
    compiler_directives={
        "language_level": "3",  # Python 3 syntax
        "embedsignature": True,  # Keep docstring (optional)
    },
    build_dir="build_cython",  # tempfolder
)

setup(
    name="simple_rag",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    ext_modules=ext_modules,
    zip_safe=False,  # Important PyInstaller
    include_package_data=True,
)
