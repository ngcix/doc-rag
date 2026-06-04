"""
Configuration settings for the RAG system.
"""
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional, Union
import sys
import json


# Device detection removed - using CPU by default to avoid torch import overhead
# To use GPU, change device in ModelConfig to "cuda"


# Correct behaviour:
# Assume cwd is `/home/vancanh-ng/projects/SpecRag`
# then in these 3 cases, BASE_DIR should be:
# `specrag` -> `/home/vancanh-ng/projects/SpecRag`
# `python -m src.main` -> `/home/vancanh-ng/projects/SpecRag`
# `./dist/specrag/specrag` -> `/home/vancanh-ng/projects/SpecRag/dist/specrag`
if getattr(sys, "frozen", False):
    # Running as compiled exe
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    # Running from source
    BASE_DIR = Path(__file__).resolve().parents[2]


def _resolve_path(path_value: Optional[str], default: Path) -> Path:
    """Resolve a configured path, treating relative paths as BASE_DIR-relative."""
    if not path_value:
        return default
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    return (BASE_DIR / candidate).resolve()


def _load_path_overrides() -> dict:
    """Load path-related overrides early so module constants can use them."""
    config_path = BASE_DIR / "config" / "setting.json"
    if not config_path.exists():
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            external_data = json.load(f)
    except Exception:
        return {}

    path_data = external_data.get("paths", {})
    if not isinstance(path_data, dict):
        path_data = {}

    # Backward-compatible shorthand at root level
    if "database_dir" in external_data and "database_dir" not in path_data:
        path_data["database_dir"] = external_data["database_dir"]
    elif "data_dir" in external_data and "database_dir" not in path_data:
        path_data["database_dir"] = external_data["data_dir"]

    # Backward compatibility for legacy paths.data_dir key
    if "database_dir" not in path_data and "data_dir" in path_data:
        path_data["database_dir"] = path_data["data_dir"]

    return path_data


_PATH_OVERRIDES = _load_path_overrides()

DATA_DIR = _resolve_path(_PATH_OVERRIDES.get("database_dir"), BASE_DIR / "data")
DOCUMENTS_DIR = _resolve_path(_PATH_OVERRIDES.get("documents_dir"), DATA_DIR / "documents")
INPUT_DOCS_DIR = DOCUMENTS_DIR  # Input documents location (read directly from documents/)
EXTRACTED_IMAGES_DIR = _resolve_path(_PATH_OVERRIDES.get("extracted_images_dir"), DATA_DIR / "extracted_images")  # Extracted images output
VECTORDB_DIR = _resolve_path(_PATH_OVERRIDES.get("vectordb_dir"), DATA_DIR / "vectordb")
FAISS_INDEX_DIR = _resolve_path(_PATH_OVERRIDES.get("faiss_index_dir"), DATA_DIR / "faiss_index")
MODELS_DIR = _resolve_path(_PATH_OVERRIDES.get("models_dir"), BASE_DIR / "models")
PROCESS_DIR = _resolve_path(_PATH_OVERRIDES.get("process_dir"), BASE_DIR / "process")
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
    device: str = "cpu"  # Default CPU. Change to "cuda" manually if GPU needed.
    normalize_embeddings: bool = True


class ChunkingConfig(BaseModel):
    """Configuration for document chunking."""
    chunk_size: int = 512
    chunk_overlap: int = 150
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
    score_threshold: float = 0.7
    include_metadata: bool = True


class SequenceChartConfig(BaseModel):
    """Configuration for sequence chart processing."""
    export_format: str = "png"  # png, svg, pdf
    export_quality: int = 150  # DPI
    include_description: bool = True


class PerformanceConfig(BaseModel):
    """Configuration for CPU usage during processing."""
    max_workers: Union[int, str, None] = "auto"
    embedding_threads: Union[int, str, None] = "auto"
    embedding_batch_size: int = 16
    target_cpu_utilization: float = 0.8
    reserved_cpu_threads: int = 2


class ImageExtractionConfig(BaseModel):
    """Configuration for full-page PDF image extraction."""

    output_dir: Path = EXTRACTED_IMAGES_DIR
    image_format: str = "png"
    min_width: int = 150  # Minimum embedded image width used by -fp page selection.
    min_height: int = 150  # Minimum embedded image height used by -fp page selection.
    extract_tables: bool = True  # Let -fp capture pages that look like tables.
    extract_figures: bool = True  # Let -fp capture pages with drawings/figures.
    context_chars: int = 10000  # Number of page text characters stored with each image.
    min_drawing_size: int = 20  # Minimum vector drawing size used by -fp page selection.


class PathConfig(BaseModel):
    """Filesystem path configuration loaded from setting.json."""
    database_dir: Path = DATA_DIR
    documents_dir: Path = DOCUMENTS_DIR
    extracted_images_dir: Path = EXTRACTED_IMAGES_DIR
    vectordb_dir: Path = VECTORDB_DIR
    faiss_index_dir: Path = FAISS_INDEX_DIR
    models_dir: Path = MODELS_DIR
    process_dir: Path = PROCESS_DIR

    @property
    def data_dir(self) -> Path:
        """Backward-compatible alias for legacy code paths."""
        return self.database_dir


class Settings(BaseModel):
    """Main settings class combining all configurations."""
    paths: PathConfig = Field(default_factory=PathConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    vectordb: VectorDBConfig = Field(default_factory=VectorDBConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    sequence_chart: SequenceChartConfig = Field(default_factory=SequenceChartConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    image_extraction: ImageExtractionConfig = Field(default_factory=ImageExtractionConfig)

    def __init__(self, **data):
        super().__init__(**data)
        self._load_external_config()

    def _load_external_config(self):
        """Load external configuration for all modules if available."""
        import json
        config_path = BASE_DIR / "config" / "setting.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    external_data = json.load(f)

                sections = [
                    "paths", "model", "chunking", "vectordb", 
                    "search", "sequence_chart", "performance", "image_extraction"
                ]

                # 1. Update each section if provided
                for section in sections:
                    if section in external_data and isinstance(external_data[section], dict):
                        section_obj = getattr(self, section)
                        section_data = dict(external_data[section])

                        if section == "paths" and "database_dir" not in section_data and "data_dir" in section_data:
                            section_data["database_dir"] = section_data["data_dir"]
                        if section == "paths":
                            # Ignore legacy key in section assignment; mapped above.
                            section_data.pop("data_dir", None)

                        for key, value in section_data.items():
                            if hasattr(section_obj, key):
                                if section == "paths" and isinstance(value, str):
                                    default_path = getattr(section_obj, key)
                                    value = _resolve_path(value, Path(default_path))
                                setattr(section_obj, key, value)
                
                # 2. Legacy root level chunk settings for backward compatibility
                if "chunk_size" in external_data and "chunking" not in external_data:
                    self.chunking.chunk_size = external_data["chunk_size"]
                if "chunk_overlap" in external_data and "chunking" not in external_data:
                    self.chunking.chunk_overlap = external_data["chunk_overlap"]

            except Exception as e:
                import logging
                logging.warning(f"Failed to load external config from {config_path}: {e}")


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
