"""Build a fresh FAISS index and swap it into place after success."""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

from specrag.config import settings
from specrag.graph import get_graph_store
from specrag.ingestion.service import IngestionReport, ingest_documents
from specrag.vectorization import close_vector_store
from specrag.vectorization.faiss_store import FaissVectorStore
from specrag.vectorization.writer_lease import WriterLease


def rebuild_index(
    input_dir: Path | None = None,
    **ingestion_options,
) -> IngestionReport:
    """Re-index into a staging directory, then replace the live directory."""
    if settings.vectordb.backend.lower() != "faiss":
        raise ValueError("Staged re-index currently supports only the FAISS backend")

    live = settings.vectordb.faiss_index_dir
    backup = live.parent / f".{live.name}.backup"
    if backup.exists() and not live.exists():
        os.replace(backup, live)
    elif backup.exists():
        shutil.rmtree(backup)
    live_lease = WriterLease(live.parent / f".{live.name}.{settings.vectordb.collection_name}.writer.lock")
    live_lease.acquire()
    staging = live.parent / f".{live.name}.staging-{uuid.uuid4().hex}"
    staging_config = settings.vectordb.model_copy(update={"faiss_index_dir": staging})
    try:
        staging_store = FaissVectorStore(staging_config)
    except Exception:
        live_lease.release()
        raise
    try:
        report = ingest_documents(
            input_dir,
            vector_store=staging_store,
            graph_store=get_graph_store(staging_config),
            **ingestion_options,
        )
    except Exception:
        staging_store.close()
        shutil.rmtree(staging, ignore_errors=True)
        live_lease.release()
        raise
    staging_store.close()

    close_vector_store()
    moved_live = False
    try:
        if live.exists():
            os.replace(live, backup)
            moved_live = True
        os.replace(staging, live)
    except Exception:
        if moved_live and backup.exists() and not live.exists():
            os.replace(backup, live)
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        live_lease.release()
    shutil.rmtree(backup, ignore_errors=True)
    return report
