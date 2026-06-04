# build.py
import time
import os
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.cli_output import configure_cli_output

configure_cli_output()

import PyInstaller.__main__
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

start_time = time.perf_counter()

PROJECT_NAME = "specrag"


# ── Safe collect để tránh crash ─────────────────────────────────────────────
def safe_collect_all(pkg):
    try:
        d, b, h = collect_all(pkg)
        print(f"Collected {pkg}: {len(d)} datas, {len(b)} binaries, {len(h)} hidden")
        return d, b, h
    except Exception as e:
        print(f"Warning: collect_all({pkg}) failed: {e}")
        return [], [], []


datas = []
binaries = []
hidden_imports = []

packages = [
    "fitz",
    "torch",
    "pymupdf",
    "transformers",
    "transformers.models",
    "sentence_transformers",
]

for pkg in packages:
    d, b, h = safe_collect_all(pkg)
    datas += d
    binaries += b
    hidden_imports += h


datas = collect_data_files("chromadb")

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


hidden_imports += collect_submodules("transformers")

hidden_imports += [
    "src",
    "src.__init__",
    "src.cli_output",
    "src.main",
    "src.path_path_resolver",
    "src.chunking",
    "src.chunking.__init__",
    "src.chunking.chunker",
    "src.config",
    "src.config.__init__",
    "src.config.settings",
    "src.image_extraction",
    "src.image_extraction.__init__",
    "src.image_extraction.extractor",
    "src.image_extraction.image_info",
    "src.search",
    "src.search.__init__",
    "src.search.bm25",
    "src.search.engine",
    "src.sequence_chart",
    "src.sequence_chart.__init__",
    "src.sequence_chart.processor",
    "src.vectorization",
    "src.vectorization.__init__",
    "src.vectorization.vector_store",
    "src.vectorization.faiss_store",
    "src.vectorization.vectorizer",
]

metadata_packages = [
    "transformers",
    "sentence-transformers",
    "sentence_transformers",
    "torch",
    "tokenizers",
    "huggingface_hub",
    "safetensors",
    "langchain",
    "langchain-core",
    "langchain-text-splitters",
]

args = [
    "./scripts/rag_cli.py",
    "-D",
    f"-n={PROJECT_NAME}",
    "--clean",
    "-y",
    *[f"--copy-metadata={pkg}" for pkg in metadata_packages],
    *[f"--add-data={src}{os.pathsep}{dest}" for src, dest in datas],
    *[f"--add-binary={src}{os.pathsep}{dest}" for src, dest in binaries],
    *[f"--hidden-import={hi}" for hi in hidden_imports],
]

# Debug: uncomment khi test
# args += ["--debug", "imports", "--log-level", "DEBUG"]

PyInstaller.__main__.run(args)

end_time = time.perf_counter()
print(f"Build finished: {timedelta(seconds=int(end_time - start_time))}")
