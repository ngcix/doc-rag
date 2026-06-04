"""
Simple RAG System Source Package
"""
from pathlib import Path
import sys

from .cli_output import configure_cli_output

configure_cli_output()

# Ensure package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

__version__ = "0.3.1"
__author__ = "Simple RAG"
