"""
Simple RAG System - Main Entry Point

This module provides the main CLI interface for the RAG system.
"""
import argparse
import shutil
import time
from pathlib import Path
from typing import Optional
import concurrent.futures
from tqdm import tqdm


def _format_duration(seconds: float) -> str:
    """Format duration in human readable format."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"


def log(message: str = "", newline: bool = True):
    """Print message with timestamp prefix."""
    from datetime import datetime
    timestamp = datetime.now().strftime("%H:%M:%S")
    if message:
        output = f"{timestamp} | {message}"
    else:
        output = ""
    if newline:
        print(output)
    else:
        print(output, end="", flush=True)

from config import (
    settings, ensure_directories,
    DOCUMENTS_DIR, EXTRACTED_IMAGES_DIR,
    VECTORDB_DIR, FAISS_INDEX_DIR, PROCESS_INPUT_DIR, PROCESS_OUTPUT_DIR, MODELS_DIR
)
from src.chunking import DocumentChunker, chunk_documents
from src.vectorization import get_vectorizer, get_vector_store
from src.search import get_search_engine, HybridSearchEngine
from src.sequence_chart import get_chart_processor
from src.image_extraction import get_image_extractor, get_vectorization_data


def _process_chunking(file_path: Path) -> list:
    """Helper for parallel chunking."""
    try:
        # Re-instantiate chunker in each process to avoid pickling issues
        # or use the convenience function which does it internally
        return chunk_documents(file_path)
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return []


def _process_extraction(args) -> list:
    """Helper for parallel image extraction."""
    pdf_file, mode, fullpage_mode = args
    if not pdf_file.exists():
        return []
    
    try:
        extractor = get_image_extractor(mode)
        # Avoid print in parallel process or it might get messy, 
        # but for now let's keep it minimal or just return results
        return extractor.extract_from_file(pdf_file, fullpage_mode=fullpage_mode)
    except Exception as e:
        # print(f"Error extracting images from {pdf_file}: {e}")
        # Return empty list on error
        return []



def process_documents(
    mode = "",
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
    log(f"Processing documents from: {input_dir}")
    log(f"Vector store backend: {backend}")
    if backend == "faiss":
        log(f"FAISS index location: {FAISS_INDEX_DIR}")
    else:
        log(f"ChromaDB location: {VECTORDB_DIR}")
    print("-" * 50)
    
    # Initialize components
    chunker = DocumentChunker()
    vectorizer = get_vectorizer()
    vector_store = get_vector_store()
    chart_processor = get_chart_processor()
    image_extractor = get_image_extractor(mode)
    
    all_vectorized = []
    total_images = 0
    
    
    # Collect all items to vectorize
    items_to_vectorize = []
    
    # 1. Process regular documents (text)
    log("[1/3] Processing documents (Parallel)...")
    step_start = time.perf_counter()
    
    # Collect files
    extensions = ['.txt', '.md', '.pdf', '.docx', '.markdown']
    files_to_chunk = []
    # Use set to avoid duplicates if glob matches multiple patterns (though unlikely with these extensions)
    # But glob is case sensitive on some OS. Windows is usually case insensitive.
    # Let's simple iterate. 
    for ext in extensions:
        files_to_chunk.extend(list(input_dir.glob(f"**/*{ext}")))
    
    # Remove duplicates just in case
    files_to_chunk = list(set(files_to_chunk))
    
    chunks = []
    if files_to_chunk:
        print(f"  Found {len(files_to_chunk)} files to chunk.")
        with concurrent.futures.ProcessPoolExecutor() as executor:
            # chunk_documents helper fits perfectly here
            results = list(tqdm(
                executor.map(_process_chunking, files_to_chunk), 
                total=len(files_to_chunk), 
                desc="  Chunking files"
            ))
            for res in results:
                chunks.extend(res)

    chunking_time = time.perf_counter() - step_start
    log(f"  Extracted {len(chunks)} text chunks (took {_format_duration(chunking_time)})")
    
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
    extraction_time = 0
    if include_images:
        log("[2/3] Extracting images from PDFs (Parallel)...")
        step_start = time.perf_counter()
        pdf_files = list(input_dir.glob("**/*.pdf"))
        
        if pdf_files:
            extract_args = [(p, mode, fullpage_mode) for p in pdf_files]
            
            with concurrent.futures.ProcessPoolExecutor() as executor:
                results = list(tqdm(
                    executor.map(_process_extraction, extract_args), 
                    total=len(pdf_files), 
                    desc="  Extracting from PDFs"
                ))
                
                for i, extracted in enumerate(results):
                    if extracted:
                        total_images += len(extracted)
                        image_data = get_vectorization_data(extracted)
                        for data in image_data:
                            data["type"] = "image"
                            items_to_vectorize.append(data)
        
        extraction_time = time.perf_counter() - step_start
        log(f"  Total images processed: {total_images} (took {_format_duration(extraction_time)})")
    
    # 3. Process sequence charts
    chart_time = 0
    if include_charts:
        log("[3/3] Processing sequence charts...")
        step_start = time.perf_counter()
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
        chart_time = time.perf_counter() - step_start
        log(f"  Charts processing completed (took {_format_duration(chart_time)})")
    
    # 4. Vectorize and Store
    vectorize_time = 0
    if items_to_vectorize:
        log(f"[4/4] Vectorizing and Storing {len(items_to_vectorize)} items...")
        step_start = time.perf_counter()
        
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
        vectorize_time = time.perf_counter() - step_start
        log(f"  Vectorization completed (took {_format_duration(vectorize_time)})")
    
    # Calculate total time
    total_time = chunking_time + extraction_time + chart_time + vectorize_time
    
    print("\n" + "=" * 50)
    log("Processing complete!")
    log(f"  Text chunks: {len(chunks)}")
    log(f"  Images extracted: {total_images}")
    log(f"  Total items in database: {vector_store.count()}")
    log("⏱️  Time Report:")
    log(f"  Chunking:      {_format_duration(chunking_time)}")
    if include_images:
        log(f"  Image Extract: {_format_duration(extraction_time)}")
    if include_charts:
        log(f"  Charts:        {_format_duration(chart_time)}")
    log(f"  Vectorization: {_format_duration(vectorize_time)}")
    log(f"  ─────────────────")
    log(f"  Total:         {_format_duration(total_time)}")


def search_documents(
    query: str,
    top_k: int = 5,
    save_results: bool = True,
    images_only: bool = False,
    use_hybrid: bool = False
):
    """
    Search through vectorized documents.
    
    Args:
        query: Search query text.
        top_k: Number of results to return.
        save_results: Whether to save search input/output.
        images_only: If True, only return image results.
        use_hybrid: If True, use BM25+Vector hybrid search.
    """
    start_time = time.perf_counter()
    
    log(f"Searching for: '{query}'")
    log(f"Using backend: {settings.vectordb.backend}")
    if use_hybrid:
        print("Mode: Hybrid (BM25 + Vector)")
    if images_only:
        print("Filter: Images only")
    print("-" * 50)
    
    # Fetch more results if filtering, to ensure we get enough after filter
    # For image-only search, fetch many more since images may have lower similarity than text
    fetch_k = 1000 if images_only else top_k
    search_threshold = 0.5 if images_only else None
    
    # Use hybrid or regular search
    if use_hybrid:
        vectorizer = get_vectorizer()
        vector_store = get_vector_store()
        hybrid_engine = HybridSearchEngine(vector_store, vectorizer)
        raw_results = hybrid_engine.search(
            query, 
            top_k=fetch_k, 
            vector_weight=0.4,  # Give more weight to BM25 for exact-match
            bm25_weight=0.6,
            threshold=search_threshold
        )
        # Convert to SearchResult-like objects for compatibility
        from src.search import SearchResult
        results = [
            SearchResult(
                rank=r["rank"],
                document=r["document"],
                similarity=r.get("rrf_score", r.get("similarity", 0)),
                metadata=r["metadata"],
                chunk_id=r["id"]
            )
            for r in raw_results
        ]
    else:
        engine = get_search_engine()
        if save_results:
            results = engine.search_and_save(query, top_k=fetch_k, threshold=search_threshold)
        else:
            results = engine.search(query, top_k=fetch_k, threshold=search_threshold)
    
    # Filter for images only if requested
    if images_only:
        image_types = ["image", "extracted_image", "fullpage"]
        results = [
            r for r in results 
            if r.metadata.get("content_type") in image_types 
            or r.metadata.get("type") in image_types
            or r.metadata.get("region_type") in ["fullpage", "figure", "table", "chart"]
        ][:top_k]  # Limit to top_k after filtering
        
        # Re-rank after filtering
        for i, r in enumerate(results):
            r.rank = i + 1
    
    search_time = time.perf_counter() - start_time
    
    # Display results
    if images_only and results:
        print(f"Found {len(results)} image results:\n")
        for r in results:
            image_path = r.metadata.get("image_path", "N/A")
            source = r.metadata.get("source_file", "Unknown")
            page = r.metadata.get("page_number", "?")
            print(f"[{r.rank}] Score: {r.similarity:.4f}")
            print(f"    Image: {image_path}")
            print(f"    Source: {source}, Page {page}")
            print(f"    ID: {r.chunk_id}")
            print()
    elif images_only and not results:
        print("No image results found.")
    elif results:
        # Format results using engine or manual formatting
        if not use_hybrid:
            print(engine.format_results(results, format_type="text"))
        else:
            # Manual formatting for hybrid results
            print(f"Found {len(results)} results:\n")
            for r in results:
                print(f"[{r.rank}] Score: {r.similarity:.4f}")
                print(f"    ID: {r.chunk_id}")
                print(f"    Source: {r.metadata.get('source_file', 'Unknown')}")
                print(f"    Content: {r.document[:200] if r.document else 'N/A'}...")
                print()
    else:
        print("No results found.")
    
    print(f"\n⏱️  Search completed in {_format_duration(search_time)}")
    
    return results


def multi_search(
    queries: list[str],
    top_k: int = 5,
    images_only: bool = False,
    use_hybrid: bool = False
):
    """
    Search with multiple queries and merge results using RRF.
    
    This improves recall by searching with different phrasings of the same concept.
    
    Args:
        queries: List of search queries (2-5 recommended)
        top_k: Number of final results to return
        images_only: If True, only return image results
        use_hybrid: If True, use BM25+Vector hybrid search
    """
    start_time = time.perf_counter()
    
    print(f"Multi-Query Search ({len(queries)} queries)")
    print(f"Using backend: {settings.vectordb.backend}")
    if use_hybrid:
        print("Mode: Hybrid (BM25 + Vector)")
    if images_only:
        print("Filter: Images only")
    print("-" * 50)
    
    for i, q in enumerate(queries, 1):
        print(f"  [{i}] {q}")
    print("-" * 50)
    
    # Collect results from all queries
    all_results = {}  # chunk_id -> (best_score, result_obj, query_hits)
    rrf_k = 60  # RRF parameter
    
    for query_idx, query in enumerate(queries):
        # Search with lower threshold to get more candidates
        fetch_k = top_k * 3
        search_threshold = 0.4 if images_only else 0.5
        
        if use_hybrid:
            vectorizer = get_vectorizer()
            vector_store = get_vector_store()
            hybrid_engine = HybridSearchEngine(vector_store, vectorizer)
            raw_results = hybrid_engine.search(
                query, 
                top_k=fetch_k, 
                vector_weight=0.4,
                bm25_weight=0.6,
                threshold=search_threshold
            )
            from src.search import SearchResult
            results = [
                SearchResult(
                    rank=r["rank"],
                    document=r["document"],
                    similarity=r.get("rrf_score", r.get("similarity", 0)),
                    metadata=r["metadata"],
                    chunk_id=r["id"]
                )
                for r in raw_results
            ]
        else:
            engine = get_search_engine()
            results = engine.search(query, top_k=fetch_k, threshold=search_threshold)
        
        # Apply image filter if needed
        if images_only:
            image_types = ["image", "extracted_image", "fullpage"]
            results = [
                r for r in results 
                if r.metadata.get("content_type") in image_types 
                or r.metadata.get("type") in image_types
                or r.metadata.get("region_type") in ["fullpage", "figure", "table", "chart"]
            ]
        
        # Add to all_results with RRF scoring
        for rank, result in enumerate(results, 1):
            chunk_id = result.chunk_id
            rrf_score = 1.0 / (rrf_k + rank)
            
            if chunk_id in all_results:
                # Update: add RRF score, keep best similarity, track hit count
                prev_score, prev_result, hit_count = all_results[chunk_id]
                new_score = prev_score + rrf_score
                best_result = prev_result if prev_result.similarity > result.similarity else result
                all_results[chunk_id] = (new_score, best_result, hit_count + 1)
            else:
                all_results[chunk_id] = (rrf_score, result, 1)
    
    # Sort by RRF score (higher = better, appeared in more queries with higher rank)
    sorted_results = sorted(all_results.values(), key=lambda x: x[0], reverse=True)
    
    # Build final results
    final_results = []
    for rank, (rrf_score, result, hit_count) in enumerate(sorted_results[:top_k], 1):
        result.rank = rank
        result.similarity = rrf_score  # Override with RRF score for display
        final_results.append((result, hit_count))
    
    search_time = time.perf_counter() - start_time
    
    # Display results
    if not final_results:
        print("No results found.")
    elif images_only:
        print(f"\nFound {len(final_results)} merged image results:\n")
        for result, hit_count in final_results:
            image_path = result.metadata.get("image_path", "N/A")
            source = result.metadata.get("source_file", "Unknown")
            page = result.metadata.get("page_number", "?")
            print(f"[{result.rank}] RRF Score: {result.similarity:.4f} (matched {hit_count}/{len(queries)} queries)")
            print(f"    Image: {image_path}")
            print(f"    Source: {source}, Page {page}")
            print(f"    ID: {result.chunk_id}")
            print()
    else:
        print(f"\nFound {len(final_results)} merged results:\n")
        for result, hit_count in final_results:
            print(f"[{result.rank}] RRF Score: {result.similarity:.4f} (matched {hit_count}/{len(queries)} queries)")
            print(f"    ID: {result.chunk_id}")
            print(f"    Source: {result.metadata.get('source_file', 'Unknown')}")
            print(f"    Content: {result.document[:150] if result.document else 'N/A'}...")
            print()
    
    print(f"⏱️  Multi-search completed in {_format_duration(search_time)}")
    
    return [r for r, _ in final_results]


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
    start_time = time.perf_counter()
    
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
    
    clean_time = time.perf_counter() - start_time
    
    # Recreate directories
    ensure_directories()
    print(f"\nClean completed! (took {_format_duration(clean_time)})")


def add_tag(doc_id: str, tag: str):
    """
    Add a tag to a document's metadata AND update its vector embedding.
    """
    start_time = time.perf_counter()
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
        embedding_start = time.perf_counter()
        new_embedding = vectorize_text(new_content)[0].tolist()
        embedding_time = time.perf_counter() - embedding_start
        
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
        
        total_time = time.perf_counter() - start_time
        
        print(f"Successfully added tag '{tag}' to document '{doc_id}'")
        print(f"Updated Tags: {new_tags}")
        print("Vector embedding updated to include new tag.")
        print(f"\n⏱️  Time Report:")
        print(f"  Embedding:  {_format_duration(embedding_time)}")
        print(f"  Total:      {_format_duration(total_time)}")
        
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
    strategy_group.add_argument(
        "--docling", "-dl",
        action="store_true",
        help="Extract individual images using Docling"
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
    search_parser.add_argument(
        "--pic", "-pic",
        action="store_true",
        help="Only return image results (filter by content_type)"
    )
    search_parser.add_argument(
        "--hybrid", "-hy",
        action="store_true",
        help="Use hybrid search (BM25 + Vector) for better exact-match ranking"
    )
    
    # Multi-Search command
    msearch_parser = subparsers.add_parser(
        "msearch",
        help="Search with multiple queries and merge results (improves recall)"
    )
    msearch_parser.add_argument(
        "queries",
        nargs="+",
        type=str,
        help="Multiple search queries (2-5 recommended)"
    )
    msearch_parser.add_argument(
        "--top-k", "-k",
        type=int,
        default=5,
        help="Number of merged results (default: 5)"
    )
    msearch_parser.add_argument(
        "--pic", "-pic",
        action="store_true",
        help="Only return image results"
    )
    msearch_parser.add_argument(
        "--hybrid", "-hy",
        action="store_true",
        help="Use hybrid search (BM25 + Vector)"
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

    # Eval command
    eval_parser = subparsers.add_parser(
        "eval",
        help="Run retrieval evaluation"
    )
    eval_parser.add_argument(
        "--dataset",
        type=str,
        default="tests/data/golden_dataset.json",
        help="Path to golden dataset"
    )
    eval_parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Top K results to check"
    )
    
    
    args = parser.parse_args()
    
    # Ensure directories exist
    ensure_directories()
    
    if args.command == "process":
        # Manual Validation for Strategy
        if not args.no_images:
            if not (args.fullpage or args.pymupdf or args.docling):
                parser.error("When processing images (default), you MUST specify an extraction strategy: --fullpage (-fp) OR --pymupdf (-pymu) OR --docling (-dl)")
                
        mode = "fp"
        if args.pymupdf:
            mode = "pymu"
        elif args.docling:
            mode = "dl"
        
        process_documents(
            mode,
            input_dir=args.input,
            include_charts=not args.no_charts,
            include_images=not args.no_images,
            fullpage_mode=args.fullpage
        )
    
    elif args.command == "search":
        search_documents(
            query=args.query,
            top_k=args.top_k,
            save_results=not args.no_save,
            images_only=args.pic,
            use_hybrid=args.hybrid
        )
    
    elif args.command == "msearch":
        multi_search(
            queries=args.queries,
            top_k=args.top_k,
            images_only=args.pic,
            use_hybrid=args.hybrid
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

    elif args.command == "eval":
        import sys
        # Import dynamically to avoid requirement if not used
        try:
            from tests.eval_retrieval import main as eval_main
            # Override sys.argv for the called script
            sys.argv = [sys.argv[0], "--dataset", args.dataset, "--top-k", str(args.top_k)]
            eval_main()
        except ImportError:
            print("Could not import tests.eval_retrieval. Make sure to run from project root.")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
