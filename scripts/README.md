# Scripts

This directory contains optional tools that are not part of the RAG request
path.

## `analyze_extracted_images.py`

Optional batch enrichment for rendered images. It calls a Gauss-compatible
vision endpoint, then writes descriptions/tags back through SpecRAG commands.

Use it only after documents have been indexed and `data/extracted_images/`
exists.

### Requirements

Install optional dependencies:

```bash
pip install -e ".[image-analysis]"
```

Set Gauss credentials:

```bash
# Windows PowerShell
$env:GAUSS_CLIENT_KEY="..."
$env:GAUSS_TOKEN="..."
$env:GAUSS_ENDPOINT_URL="..."
$env:GAUSS_USER_EMAIL="..."

# Linux/macOS
export GAUSS_CLIENT_KEY="..."
export GAUSS_TOKEN="..."
export GAUSS_ENDPOINT_URL="..."
export GAUSS_USER_EMAIL="..."
```

### Usage

```bash
python scripts/analyze_extracted_images.py --dry-run
python scripts/analyze_extracted_images.py --limit 10
python scripts/analyze_extracted_images.py --images-dir data/extracted_images
```

The script is intentionally optional. Search endpoints do not call it.

## Build notes

See [build.md](./build.md).
