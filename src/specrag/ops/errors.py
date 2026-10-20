"""Typed errors for ops layer (mapped to HTTP by the API)."""


class OpsError(Exception):
    """Base error for SpecRAG operations."""


class ChunkNotFoundError(OpsError):
    """Chunk / document id was not found in the vector store."""


class DocumentNotFoundError(OpsError):
    """No indexed chunks or stored file match the document source."""


class DuplicateTagError(OpsError):
    """User tag already exists on the chunk."""


class TagNotFoundError(OpsError):
    """Requested user tag was not found."""


class TagImmutableError(OpsError):
    """Attempt to remove an original (auto-extracted) tag."""


class NodeNotFoundError(OpsError):
    """No structure-graph node matches the requested clause, table or figure."""
