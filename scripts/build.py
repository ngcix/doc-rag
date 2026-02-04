# build.py
import PyInstaller.__main__
import time
import os
from datetime import timedelta
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
# Nếu bạn có my_modules → uncomment và định nghĩa trong mymodule.py
from mymodule import my_modules
hidden_imports += my_modules

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
