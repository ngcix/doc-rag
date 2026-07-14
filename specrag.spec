# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_data_files, copy_metadata

# Packages that require full collection of data, binaries and hidden imports

packages_to_collect = [
    'fitz',
    'torch',
    'pymupdf',
    'transformers',
    'sentence_transformers',
]
all_datas = []
all_binaries = []
all_hidden = []

for pkg in packages_to_collect:
    d, b, h = collect_all(pkg)
    all_datas.extend(d)
    all_binaries.extend(b)
    all_hidden.extend(h)

# Special collection for chromadb
all_datas.extend(collect_data_files('chromadb'))

# Copy metadata for heavy packages
metadata_packages = [
    'transformers',
    'torch',
    'sentence-transformers',
    'tokenizers',
    'huggingface_hub',
    'safetensors',
    'langchain',
    'langchain-core',
    'langchain-text-splitters',
]
for pkg in metadata_packages:
    all_datas.extend(copy_metadata(pkg))

# Additional critical hidden imports
all_hidden.extend([
    'langchain.text_splitter',
    'langchain_core.documents',
    'langchain.schema',
    'langchain.docstore',
    'langchain.docstore.document',
    'sentence_transformers.SentenceTransformer',
    'transformers.integrations',
    'transformers.utils',
])

a = Analysis(
    ['src/specrag/__main__.py'],
    pathex=[],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='specrag',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='specrag',
)
