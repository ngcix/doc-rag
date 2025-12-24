""" 2nd generation build with Cython """

from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules = cythonize(
        "src/main.py",
        compiler_directives={'language_level': "3"}
    )
)

# command
# python setup.py build_ext --inplace