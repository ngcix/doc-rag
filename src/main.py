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
    include_images: bool = True,
    fullpage_mode: bool = False
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
    
    
    # Collect all items to vectorize
    items_to_vectorize = []
    
    # 1. Process regular documents (text)
    print("\n[1/3] Processing documents...")
    chunks = chunker.chunk_directory(input_dir)
    print(f"  Extracted {len(chunks)} text chunks")
    
    # Prepare text chunks for vectorization
    for chunk in chunks:
        items_to_vectorize.append({
            "chunk_id": chunk.chunk_id,
            "content": chunk.content,
            "metadata": chunk.metadata,
            "source_file": chunk.source_file,
            "type": "text"
        })
    
    # 2. Extract images from PDFs
    if include_images:
        print("\n[2/3] Extracting images from PDFs...")
        for pdf_file in input_dir.glob("**/*.pdf"):
            try:
                extracted = image_extractor.extract_from_file(
                    pdf_file, 
                    fullpage_mode=fullpage_mode
                )
                if extracted:
                    total_images += len(extracted)
                    # Get image data
                    image_data = image_extractor.get_vectorization_data(extracted)
                    for data in image_data:
                        data["type"] = "image"
                        items_to_vectorize.append(data)
                        
                    print(f"  Extracted {len(extracted)} images from {pdf_file.name}")
            except Exception as e:
                print(f"  Error extracting images from {pdf_file}: {e}")
        print(f"  Total images processed: {total_images}")
    
    # 3. Process sequence charts
    if include_charts:
        print("\n[3/3] Processing sequence charts...")
        for md_file in input_dir.glob("**/*.md"):
            try:
                charts = chart_processor.process_file(md_file, export_images=True)
                if charts:
                    chart_data = chart_processor.get_vectorization_data(charts)
                    for data in chart_data:
                        data["type"] = "chart"
                        items_to_vectorize.append(data)
                        
                    print(f"  Added {len(charts)} charts from {md_file.name}")
            except Exception as e:
                print(f"  Error processing {md_file}: {e}")
    
    # 4. Vectorize and Store
    if items_to_vectorize:
        print(f"\n[4/4] Vectorizing and Storing {len(items_to_vectorize)} items...")
        
        # Extract contents for batch vectorization
        texts = [item["content"] for item in items_to_vectorize]
        
        # Vectorize in one go
        embeddings = vectorizer.vectorize(texts)
        
        # Attach embeddings back to items
        for item, embedding in zip(items_to_vectorize, embeddings):
            item["embedding"] = embedding.tolist()
            # Ensure metadata doesn't have 'type' conflict if it already exists
            if "metadata" not in item:
                item["metadata"] = {}
            item["metadata"]["content_type"] = item["type"]
            
        vector_store.add_chunks(items_to_vectorize)
    
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


def add_tag(doc_id: str, tag: str):
    """
    Add a tag to a document's metadata AND update its vector embedding.
    """
    vector_store = get_vector_store()
    
    try:
        # 1. Get current data
        current_metadata = vector_store.get_metadata(doc_id)
        if not current_metadata:
            print(f"Error: Document {doc_id} not found.")
            return

        current_content = vector_store.get_content(doc_id)
        if current_content is None:
            print(f"Error: Could not retrieve content for {doc_id}")
            return

        # 2. Update Metadata Tags
        current_tags = current_metadata.get("tags", "")
        if current_tags:
            new_tags = f"{current_tags},{tag}"
        else:
            new_tags = tag
        
        # 3. Update Content for Vectorization (Boost the tag)
        # We append the tag multiple times to boost its semantic weight
        tag_boost = f"\nTags: {tag}, {tag}, {tag}"
        new_content = current_content + tag_boost
        
        print("Re-calculating vector embedding...")
        
        # 4. Generate New Embedding
        # Lazy import to avoid circular dependency issues at top level if any
        from src.vectorization.vectorizer import vectorize_text
        new_embedding = vectorize_text(new_content)[0].tolist()
        
        # 5. Atomic-ish Update (Delete then Add)
        # Note: This effectively replaces the document
        vector_store.delete([doc_id])
        
        # Prepare metadata (ensure no type conflict)
        updated_metadata = current_metadata.copy()
        updated_metadata["tags"] = new_tags
        
        vector_store.add(
            ids=[doc_id],
            embeddings=[new_embedding],
            documents=[new_content],
            metadatas=[updated_metadata]
        )
            
        print(f"Successfully added tag '{tag}' to document '{doc_id}'")
        print(f"Updated Tags: {new_tags}")
        print("Vector embedding updated to include new tag.")
        
    except Exception as e:
        print(f"Error adding tag: {e}")


def list_tags(doc_id: str):
    """
    List tags for a document.
    """
    vector_store = get_vector_store()
    
    try:
        metadata = vector_store.get_metadata(doc_id)
        if not metadata:
            print(f"Document {doc_id} not found.")
            return

        tags = metadata.get("tags", "No tags found")
        print(f"Tags for {doc_id}: {tags}")
        
    except Exception as e:
        print(f"Error listing tags: {e}")


def list_docs():
    """List all documents in the vector store."""
    vector_store = get_vector_store()
    try:
        documents = vector_store.list_documents()
        print(f"Found {len(documents)} documents:")
        print("-" * 50)
        # Limit output if too many
        count = 0
        for doc_id, source in documents.items():
            print(f"ID: {doc_id} | Source: {source}")
            count += 1
            if count >= 10000:
                print(f"... and {len(documents) - 10000} more.")
                break
    except Exception as e:
        print(f"Error listing documents: {e}")


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
    # Image Extraction Strategy
    # We want to force choice unless --no-images is used.
    # Since argparse required=True is too strict, we validate manually.
    strategy_group = process_parser.add_mutually_exclusive_group(required=False)
    strategy_group.add_argument(
        "--fullpage", "-fp",
        action="store_true",
        help="Capture full pages as images (Context-rich, best for RAG)"
    )
    strategy_group.add_argument(
        "--pymupdf", "-pymu",
        action="store_true",
        help="Extract individual images using PyMuPDF (Precise, best for assets)"
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
    
    # List command
    subparsers.add_parser(
        "list",
        help="List all documents in the database"
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
    
    # Add Tag command
    tag_parser = subparsers.add_parser(
        "addtag",
        help="Add a tag to a document"
    )
    tag_parser.add_argument(
        "doc_id",
        type=str,
        help="Document ID"
    )
    tag_parser.add_argument(
        "tag",
        type=str,
        help="Tag to add"
    )
    
    # List Tag command
    list_tag_parser = subparsers.add_parser(
        "listtag",
        help="List tags for a document"
    )
    list_tag_parser.add_argument(
        "doc_id",
        type=str,
        help="Document ID"
    )
    
    
    args = parser.parse_args()
    
    # Ensure directories exist
    ensure_directories()
    
    if args.command == "process":
        # Manual Validation for Strategy
        if not args.no_images:
            if not (args.fullpage or args.pymupdf):
                parser.error("When processing images (default), you MUST specify an extraction strategy: --fullpage (-fp) OR --pymupdf (-pymu)")
        
        process_documents(
            input_dir=args.input,
            include_charts=not args.no_charts,
            include_images=not args.no_images,
            fullpage_mode=args.fullpage
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
    
    elif args.command == "list":
        list_docs()
    
    elif args.command == "clean":
        clean_data(
            include_models=args.all,
            skip_confirm=args.yes
        )
    
    elif args.command == "addtag":
        add_tag(args.doc_id, args.tag)
        
    elif args.command == "listtag":
        list_tags(args.doc_id)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
