"""
Simple RAG System - Main Entry Point

This module provides the main CLI interface for the RAG system.
"""
import argparse
import shutil
from pathlib import Path
from typing import Optional

from config import (
    settings, ensure_directories,
    DOCUMENTS_DIR, EXTRACTED_IMAGES_DIR,
    VECTORDB_DIR, FAISS_INDEX_DIR, PROCESS_INPUT_DIR, PROCESS_OUTPUT_DIR, MODELS_DIR
)
from src.chunking import DocumentChunker
from src.vectorization import get_vectorizer, get_vector_store
from src.search import get_search_engine
from src.sequence_chart import get_chart_processor
from src.image_extraction import get_image_extractor


def process_documents(
    input_dir: Optional[Path] = None,
    include_charts: bool = True,
    include_images: bool = True
):
    """
    Process all documents in the input directory.
    
    - Chunks documents (text)
    - Extracts images from PDFs
    - Extracts and processes sequence charts
    - Vectorizes content
    - Stores in vector database
    """
    input_dir = input_dir or DOCUMENTS_DIR
    input_dir = Path(input_dir)
    
    backend = settings.vectordb.backend
    print(f"Processing documents from: {input_dir}")
    print(f"Vector store backend: {backend}")
    if backend == "faiss":
        print(f"FAISS index location: {FAISS_INDEX_DIR}")
    else:
        print(f"ChromaDB location: {VECTORDB_DIR}")
    print("-" * 50)
    
    # Initialize components
    chunker = DocumentChunker()
    vectorizer = get_vectorizer()
    vector_store = get_vector_store()
    chart_processor = get_chart_processor()
    image_extractor = get_image_extractor()
    
    all_vectorized = []
    total_images = 0
    
    # 1. Process regular documents (text)
    print("\n[1/4] Chunking documents (text)...")
    chunks = chunker.chunk_directory(input_dir)
    print(f"Total text chunks: {len(chunks)}")
    
    if chunks:
        print("\n[2/4] Vectorizing text chunks...")
        vectorized_chunks = vectorizer.vectorize_chunks(chunks)
        all_vectorized.extend(vectorized_chunks)
    
    # 2. Extract images from PDFs
    if include_images:
        print("\n[3/4] Extracting images from PDFs...")
        for pdf_file in input_dir.glob("**/*.pdf"):
            try:
                extracted = image_extractor.extract_from_file(pdf_file)
                if extracted:
                    total_images += len(extracted)
                    # Vectorize image descriptions
                    image_data = image_extractor.get_vectorization_data(extracted)
                    for data in image_data:
                        embedding = vectorizer.vectorize(data["content"])[0].tolist()
                        data["embedding"] = embedding
                    all_vectorized.extend(image_data)
                    print(f"  Extracted {len(extracted)} images from {pdf_file.name}")
            except Exception as e:
                print(f"  Error extracting images from {pdf_file}: {e}")
        print(f"Total images extracted: {total_images}")
    
    # 3. Process sequence charts
    if include_charts:
        print("\n[3b/4] Processing sequence charts...")
        for md_file in input_dir.glob("**/*.md"):
            try:
                charts = chart_processor.process_file(md_file, export_images=True)
                if charts:
                    chart_data = chart_processor.get_vectorization_data(charts)
                    
                    # Vectorize chart descriptions
                    for data in chart_data:
                        embedding = vectorizer.vectorize(data["content"])[0].tolist()
                        data["embedding"] = embedding
                    
                    all_vectorized.extend(chart_data)
                    print(f"  Added {len(charts)} charts from {md_file.name}")
            except Exception as e:
                print(f"  Error processing {md_file}: {e}")
    
    # 4. Store in vector database
    if all_vectorized:
        print(f"\n[4/4] Storing {len(all_vectorized)} items in vector database...")
        vector_store.add_chunks(all_vectorized)
    
    print("\n" + "=" * 50)
    print("Processing complete!")
    print(f"  Text chunks: {len(chunks)}")
    print(f"  Images extracted: {total_images}")
    print(f"  Total items in database: {vector_store.count()}")


def search_documents(
    query: str,
    top_k: int = 5,
    save_results: bool = True
):
    """
    Search through vectorized documents.
    """
    print(f"Searching for: '{query}'")
    print(f"Using backend: {settings.vectordb.backend}")
    print("-" * 50)
    
    engine = get_search_engine()
    
    if save_results:
        results = engine.search_and_save(query, top_k=top_k)
    else:
        results = engine.search(query, top_k=top_k)
    
    # Display results
    print(engine.format_results(results, format_type="text"))
    
    return results


def show_stats():
    """Show vector database statistics."""
    vector_store = get_vector_store()
    stats = vector_store.get_stats()
    
    print("Vector Database Statistics")
    print("-" * 50)
    for key, value in stats.items():
        print(f"  {key}: {value}")


def clean_data(include_models: bool = False, skip_confirm: bool = False):
    """
    Clean extracted data.
    
    Args:
        include_models: If True, also delete downloaded models.
        skip_confirm: If True, skip confirmation prompt.
    """
    dirs_to_clean = [
        (VECTORDB_DIR, "ChromaDB database"),
        (FAISS_INDEX_DIR, "FAISS index"),
        (EXTRACTED_IMAGES_DIR, "Extracted images"),
        (PROCESS_INPUT_DIR, "Process input"),
        (PROCESS_OUTPUT_DIR, "Process output"),
    ]
    
    if include_models:
        dirs_to_clean.append((MODELS_DIR, "Downloaded models"))
    
    # Show what will be deleted
    print("The following directories will be cleaned:")
    total_size = 0
    for dir_path, name in dirs_to_clean:
        if dir_path.exists():
            # Calculate size
            size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
            total_size += size
            size_mb = size / (1024 * 1024)
            print(f"  {name}: {dir_path} ({size_mb:.2f} MB)")
        else:
            print(f"  {name}: {dir_path} (not exists)")
    
    print(f"\nTotal: {total_size / (1024 * 1024):.2f} MB")
    
    # Confirm
    if not skip_confirm:
        response = input("\nAre you sure you want to delete these? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("Cancelled.")
            return
    
    # Clean directories
    print("\nCleaning...")
    for dir_path, name in dirs_to_clean:
        if dir_path.exists():
            try:
                # Remove all contents but keep the directory
                for item in dir_path.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                print(f"  ✓ Cleaned {name}")
            except Exception as e:
                print(f"  ✗ Error cleaning {name}: {e}")
        else:
            print(f"  - {name} not exists, skipped")
    
    # Recreate directories
    ensure_directories()
    print("\nClean completed!")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Simple RAG System - Document Processing and Search"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Process command
    process_parser = subparsers.add_parser(
        "process",
        help="Process and vectorize documents"
    )
    process_parser.add_argument(
        "--input", "-i",
        type=Path,
        default=DOCUMENTS_DIR,
        help=f"Input directory (default: {DOCUMENTS_DIR})"
    )
    process_parser.add_argument(
        "--no-charts",
        action="store_true",
        help="Skip sequence chart processing"
    )
    process_parser.add_argument(
        "--no-images",
        action="store_true",
        help="Skip image extraction from PDFs"
    )
    
    # Search command
    search_parser = subparsers.add_parser(
        "search",
        help="Search through documents"
    )
    search_parser.add_argument(
        "query",
        type=str,
        help="Search query"
    )
    search_parser.add_argument(
        "--top-k", "-k",
        type=int,
        default=5,
        help="Number of results (default: 5)"
    )
    search_parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save search input/output"
    )
    
    # Stats command
    subparsers.add_parser(
        "stats",
        help="Show vector database statistics"
    )
    
    # Init command
    subparsers.add_parser(
        "init",
        help="Initialize directory structure"
    )
    
    # Clean command
    clean_parser = subparsers.add_parser(
        "clean",
        help="Clean extracted data (vectordb, process input/output)"
    )
    clean_parser.add_argument(
        "--all",
        action="store_true",
        help="Also clean downloaded models"
    )
    clean_parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    
    args = parser.parse_args()
    
    # Ensure directories exist
    ensure_directories()
    
    if args.command == "process":
        process_documents(
            input_dir=args.input,
            include_charts=not args.no_charts,
            include_images=not args.no_images
        )
    
    elif args.command == "search":
        search_documents(
            query=args.query,
            top_k=args.top_k,
            save_results=not args.no_save
        )
    
    elif args.command == "stats":
        show_stats()
    
    elif args.command == "init":
        print("Directory structure initialized:")
        print(f"  Documents: {DOCUMENTS_DIR}")
        print(f"  Vector DB: {VECTORDB_DIR}")
        print(f"  Process Input: {PROCESS_INPUT_DIR}")
        print(f"  Process Output: {PROCESS_OUTPUT_DIR}")
    
    elif args.command == "clean":
        clean_data(
            include_models=args.all,
            skip_confirm=args.yes
        )
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
