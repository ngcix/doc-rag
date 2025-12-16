"""
Configuration settings for the RAG system.
"""
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional


# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"
INPUT_DOCS_DIR = DOCUMENTS_DIR  # Input documents location (read directly from documents/)
EXTRACTED_IMAGES_DIR = DATA_DIR / "extracted_images"  # Extracted images output
VECTORDB_DIR = DATA_DIR / "vectordb"
FAISS_INDEX_DIR = DATA_DIR / "faiss_index"
MODELS_DIR = BASE_DIR / "models"
PROCESS_DIR = BASE_DIR / "process"
PROCESS_INPUT_DIR = PROCESS_DIR / "input"
PROCESS_OUTPUT_DIR = PROCESS_DIR / "output"


# Model snapshot for local/offline use
MODEL_SNAPSHOT_ID = "9bbca17d9273fd0d03d5725c7a4b0f6b45142062"

class ModelConfig(BaseModel):
    """Configuration for the embedding model."""
    # For online use: model_name: str = "Alibaba-NLP/gte-multilingual-base"
    # For local/offline use:
    model_name: str = str(MODELS_DIR / "models--Alibaba-NLP--gte-multilingual-base" / "snapshots" / MODEL_SNAPSHOT_ID)


    model_cache_dir: Path = MODELS_DIR
    max_seq_length: int = 8192
    device: str = "cpu"  # or "cuda" if GPU available
    normalize_embeddings: bool = True


class ChunkingConfig(BaseModel):
    """Configuration for document chunking."""
    chunk_size: int = 512
    chunk_overlap: int = 50
    separators: list[str] = Field(default=["\n\n", "\n", ". ", " ", ""])
    length_function: str = "len"  # or "tiktoken" for token-based


class VectorDBConfig(BaseModel):
    """Configuration for vector database."""
    backend: str = "faiss"  # "chromadb" or "faiss"
    collection_name: str = "documents"
    persist_directory: Path = VECTORDB_DIR
    faiss_index_dir: Path = FAISS_INDEX_DIR
    distance_metric: str = "cosine"  # cosine, l2, ip
    # FAISS specific options
    faiss_index_type: str = "Flat"  # Flat, IVF, HNSW


class SearchConfig(BaseModel):
    """Configuration for search."""
    top_k: int = 5
    score_threshold: float = 0.5
    include_metadata: bool = True


class SequenceChartConfig(BaseModel):
    """Configuration for sequence chart processing."""
    export_format: str = "png"  # png, svg, pdf
    export_quality: int = 150  # DPI
    include_description: bool = True


class ImageExtractionConfig(BaseModel):
    """Configuration for image extraction from documents.
    
    Supports two methods:
    - PyMuPDF (fitz): Fast, extracts embedded images and vector drawings
    - PP-Structure (PaddleOCR): AI-based layout analysis and context extraction
    """
    # Output settings
    output_dir: Path = EXTRACTED_IMAGES_DIR
    image_format: str = "png"
    
    # Size filters
    min_width: int = 150  # Minimum width to consider as valid image
    min_height: int = 150  # Minimum height
    
    # Quality filters (to avoid black/empty images)
    min_brightness: float = 30.0  # Minimum mean brightness (0-255)
    min_std_dev: float = 15.0  # Minimum standard deviation
    max_dark_pixel_ratio: float = 0.85  # Maximum ratio of dark pixels
    
    # Extraction options
    extract_tables: bool = True  # Extract table regions
    extract_figures: bool = True  # Extract figure/image regions
    context_chars: int = 500  # Number of characters to extract around image
    
    # PP-Structure settings
    use_ppstructure: bool = False  # Enable PP-Structure for layout analysis
    ppstructure_max_pages: int = 20  # Max pages to analyze with PP-Structure
    
    # PyMuPDF vector drawings clustering
    cluster_merge_distance: int = 50  # Pixels to merge nearby drawings
    min_drawing_size: int = 20  # Minimum size for a drawing path
    min_diagram_size: int = 100  # Minimum size for a clustered diagram
    
    # GPU settings (for PP-Structure)
    use_gpu: bool = False  # Use GPU for PP-Structure (if available)


class Settings(BaseModel):
    """Main settings class combining all configurations."""
    model: ModelConfig = Field(default_factory=ModelConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    vectordb: VectorDBConfig = Field(default_factory=VectorDBConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    sequence_chart: SequenceChartConfig = Field(default_factory=SequenceChartConfig)
    image_extraction: ImageExtractionConfig = Field(default_factory=ImageExtractionConfig)


# Global settings instance
settings = Settings()


def ensure_directories():
    """Create all required directories if they don't exist."""
    directories = [
        DOCUMENTS_DIR,
        EXTRACTED_IMAGES_DIR,
        VECTORDB_DIR,
        FAISS_INDEX_DIR,
        MODELS_DIR,
        PROCESS_INPUT_DIR,
        PROCESS_OUTPUT_DIR,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
