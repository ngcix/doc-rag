"""Document ingestion application service."""

from specrag.ingestion.reindex import rebuild_index
from specrag.ingestion.service import IngestionReport, ingest_documents

__all__ = ["IngestionReport", "ingest_documents", "rebuild_index"]
