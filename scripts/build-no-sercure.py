import PyInstaller.__main__
import time
import os

from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_all,
    collect_submodules,
)
from datetime import timedelta


start_time = time.perf_counter()
PROJECT_NAME = "simpleRAG"

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

args = [
    "./src/main.py",
    "-D",
    f"-n={PROJECT_NAME}",
    "--clean",
    "-y",
    "--noupx",  # Disable UPX (faster build, optional)
    "--optimize=2",
    *[f"--copy-metadata={pkg}" for pkg in metadata_packages],
    *[f"--add-data={src}{os.pathsep}{dest}" for src, dest in datas],
    *[f"--add-binary={src}{os.pathsep}{dest}" for src, dest in binaries],
    *[f"--hidden-import={hi}" for hi in hidden_imports],
]

print("PyInstaller command:")
for arg in args:
    print(f"  {arg}")

PyInstaller.__main__.run(args)


end_time = time.perf_counter()
execution_time = end_time - start_time
time_str = str(timedelta(seconds=int(execution_time)))
print(f"Build time: {time_str}")
