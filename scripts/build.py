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
    "pdf_oxide",
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
    "src.main",
    "src.chunking",
    "src.chunking.__init__",
    "src.chunking.chunker",
    "src.image_extraction",
    "src.image_extraction.__init__",
    "src.image_extraction.docling_extractor",
    "src.image_extraction.pymu_extractor",
    "src.image_extraction.image_info",
    "src.image_extraction.extractor",
    "src.image_extraction.pdf_oxide_extractor",
    "src.image_extraction.docling.__init__",
    "src.image_extraction.docling.model",
    "src.image_extraction.docling.processor",
    "src.image_extraction.docling.document",
    "src.image_extraction.docling.extractor",
    "src.search",
    "src.search.__init__",
    "src.search.bm25",
    "src.search.engine",
    "src.sequence_chart",
    "src.sequence_chart.__init__",
    "src.sequence_chart.processor",
    "src.vectorization",
    "src.vectorization.__init",
    "src.vectorization.vector_store",
    "src.vectorization.faiss_store",
    "src.vectorization.vectorizer",
    "src.config",
    "src.config.__init__",
    "src.config.settings",
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
