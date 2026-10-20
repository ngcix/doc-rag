"""
Document Chunking Module

This module provides functionality to split documents into smaller chunks
for efficient vectorization and retrieval.
"""

from pathlib import Path
from typing import Optional

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
from pydantic import BaseModel

from specrag.config import ChunkingConfig, settings


class DocumentChunk(BaseModel):
    """Represents a single chunk of a document."""

    chunk_id: str
    content: str
    metadata: dict
    start_index: int
    end_index: int
    source_file: str | None = None


class DocumentChunker:
    """
    Handles document chunking with configurable parameters.

    Supports multiple chunking strategies:
    - Character-based chunking
    - Token-based chunking
    - Semantic chunking (paragraph/sentence aware)
    """

    def __init__(self, config: ChunkingConfig | None = None):
        """
        Initialize the DocumentChunker.

        Args:
            config: Chunking configuration. Uses default settings if not provided.
        """
        self.config = config or settings.chunking
        self._text_splitter = self._create_text_splitter()

    def _create_text_splitter(self) -> RecursiveCharacterTextSplitter:
        """Create the text splitter based on configuration."""
        return RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            separators=self.config.separators,
            length_function=len,
            is_separator_regex=False,
        )

    def chunk_text(self, text: str, source_file: str | None = None, metadata: dict | None = None) -> list[DocumentChunk]:
        """
        Split text into chunks.

        Args:
            text: The text content to chunk.
            source_file: Optional source file path for metadata.
            metadata: Additional metadata to attach to chunks.

        Returns:
            List of DocumentChunk objects.
        """
        if not text.strip():
            return []

        # Use langchain's text splitter
        chunks = self._text_splitter.split_text(text)

        result = []
        current_index = 0

        for i, chunk_content in enumerate(chunks):
            # Find the actual position in the original text
            start_idx = text.find(chunk_content, current_index)
            if start_idx == -1:
                start_idx = current_index
            end_idx = start_idx + len(chunk_content)

            chunk_metadata = {"chunk_index": i, "total_chunks": len(chunks), **(metadata or {})}

            chunk = DocumentChunk(
                chunk_id=f"{source_file or 'unknown'}_{i}", content=chunk_content, metadata=chunk_metadata, start_index=start_idx, end_index=end_idx, source_file=source_file
            )
            result.append(chunk)
            current_index = start_idx + 1

        return result

    def chunk_file(self, file_path: Path) -> list[DocumentChunk]:
        """
        Read and chunk a file.

        Args:
            file_path: Path to the file to chunk.

        Returns:
            List of DocumentChunk objects.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        metadata = {
            "file_name": file_path.name,
            "file_extension": file_path.suffix,
            "file_size": file_path.stat().st_size,
        }

        if file_path.suffix.lower() == ".pdf":
            from specrag.chunking.pdf import annotate_chunks, read_pdf

            pdf = read_pdf(file_path)
            chunks = self.chunk_text(text=pdf.text, source_file=str(file_path), metadata=metadata)
            annotate_chunks(chunks, pdf)
            return chunks

        from specrag.tables import SPREADSHEET_EXTENSIONS

        if file_path.suffix.lower() in SPREADSHEET_EXTENSIONS:
            return self._chunk_spreadsheet(file_path, metadata)

        content = self._read_file(file_path)
        return self.chunk_text(text=content, source_file=str(file_path), metadata=metadata)

    def _chunk_spreadsheet(self, file_path: Path, metadata: dict) -> list[DocumentChunk]:
        """One chunk per table record, each repeating its row label and header path."""
        from specrag.tables import spreadsheet_chunks

        pieces = spreadsheet_chunks(file_path)
        chunks, offset = [], 0
        for index, piece in enumerate(pieces):
            chunk_metadata = {"chunk_index": index, "total_chunks": len(pieces), **metadata, **piece.metadata}
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{file_path}_{index}",
                    content=piece.content,
                    metadata=chunk_metadata,
                    start_index=offset,
                    end_index=offset + len(piece.content),
                    source_file=str(file_path),
                )
            )
            offset += len(piece.content)
        return chunks

    def _read_file(self, file_path: Path) -> str:
        from specrag.chunking.readers import read_document

        return read_document(file_path)

    def chunk_directory(self, directory: Path, extensions: list[str] | None = None, exclude_patterns: list[str] | None = None, recursive: bool = True) -> list[DocumentChunk]:
        """
        Chunk all documents in a directory.

        Args:
            directory: Path to the directory.
            extensions: List of file extensions to process. Default: all supported.
            exclude_patterns: List of glob patterns to exclude (e.g. ["**/*.pdf"]).
            recursive: Whether to process subdirectories.

        Returns:
            List of all DocumentChunk objects from the directory.
        """
        directory = Path(directory)

        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        extensions = extensions or [".txt", ".md", ".pdf", ".docx", ".markdown", ".xlsx", ".xls", ".pptx", ".csv"]
        pattern = "**/*" if recursive else "*"
        exclude_patterns = exclude_patterns or []

        all_chunks = []

        for file_path in directory.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                # Check exclusions
                if any(file_path.match(p) for p in exclude_patterns):
                    continue

                try:
                    chunks = self.chunk_file(file_path)
                    all_chunks.extend(chunks)
                    print(f"Chunked: {file_path.name} -> {len(chunks)} chunks")
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")

        return all_chunks


# Convenience function
def chunk_documents(
    source: str | Path,
    config: ChunkingConfig | None = None,
) -> list[DocumentChunk]:
    """
    Chunk documents from a file or directory.

    Args:
        source: Path to file or directory.
        config: Optional chunking configuration.

    Returns:
        List of DocumentChunk objects.
    """
    chunker = DocumentChunker(config)
    source_path = Path(source)

    if source_path.is_file():
        return chunker.chunk_file(source_path)
    elif source_path.is_dir():
        return chunker.chunk_directory(source_path)
    else:
        raise ValueError(f"Invalid source path: {source}")
