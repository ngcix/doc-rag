"""
Simple RAG System - Main Entry Point

This module provides the main CLI interface for the RAG system.
"""
import argparse
import os
import shutil
import time
from pathlib import Path
from typing import Optional
import concurrent.futures

from specrag.config import(
    settings, ensure_directories,
    DOCUMENTS_DIR, EXTRACTED_IMAGES_DIR,
    VECTORDB_DIR, FAISS_INDEX_DIR, PROCESS_INPUT_DIR, PROCESS_OUTPUT_DIR, MODELS_DIR
)
from specrag.performance import (
    _is_auto_cpu_value,
    _coerce_positive_int,
    _coerce_non_negative_int,
    _coerce_cpu_target,
    _logical_cpu_count,
    _resolve_cpu_limit,
    configure_embedding_threads,
)


def _get_chunk_documents():
    from specrag.chunking import chunk_documents
    return chunk_documents


def _get_vectorizer():
    from specrag.vectorization import get_vectorizer
    return get_vectorizer()


def _get_vector_store():
    from specrag.vectorization import get_vector_store
    return get_vector_store()


def _get_search_engine():
    from specrag.search import get_search_engine
    return get_search_engine()


def _get_hybrid_search_engine():
    from specrag.search import HybridSearchEngine
    return HybridSearchEngine


def _get_chart_processor():
    from specrag.sequence_chart import get_chart_processor
    return get_chart_processor()


def _get_image_extractor(force_new: bool = False, image_format: Optional[str] = None):
    from specrag.image_extraction import get_image_extractor
    return get_image_extractor(force_new=force_new, image_format=image_format)


def _get_vectorization_data(images):
    from specrag.image_extraction import get_vectorization_data
    return get_vectorization_data(images)


def _resolve_worker_count(
    value,
    item_count: Optional[int] = None,
    target_cpu_utilization: Optional[float] = None,
    reserved_cpu_threads: Optional[int] = None,
) -> int:
    worker_count = _resolve_cpu_limit(
        value,
        target_cpu_utilization=target_cpu_utilization,
        reserved_cpu_threads=reserved_cpu_threads,
    )
    if item_count is not None:
        worker_count = min(worker_count, max(1, item_count))
    return max(1, worker_count)


def _apply_cpu_thread_limit(
    value,
    target_cpu_utilization: Optional[float] = None,
    reserved_cpu_threads: Optional[int] = None,
) -> int:
    return configure_embedding_threads(
        value,
        target_cpu_utilization=target_cpu_utilization,
        reserved_cpu_threads=reserved_cpu_threads,
    )


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

def _process_chunking(args) -> list:
    """Helper for parallel chunking."""
    file_path = args
    try:
        return _get_chunk_documents()(file_path)
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return []


def _process_extraction(args) -> list:
    """Helper for parallel image extraction."""
    pdf_file, image_format = args
    if not pdf_file.exists():
        return []
    
    try:
        extractor = _get_image_extractor(force_new=True, image_format=image_format)
        return extractor.extract_from_file(pdf_file)
    except Exception as e:
        return []



def process_documents(
    input_dir: Optional[Path] = None,
    include_charts: bool = True,
    include_images: bool = True,
    image_format: str = "png",
    max_workers: int | str | None = None,
    embedding_threads: int | str | None = None,
    embedding_batch_size: Optional[int] = None,
):
    """
    Process all documents in the input directory.
    
    - Chunks documents (text)
    - Extracts images from PDFs
    - Extracts and processes sequence charts
    - Vectorizes content
    - Stores in vector database
    """
    # Prefer configured path from setting.json (paths.documents_dir).
    # Falls back to module constant if not provided.
    input_dir = input_dir or settings.paths.documents_dir or DOCUMENTS_DIR
    input_dir = Path(input_dir)
    from tqdm import tqdm
    
    backend = settings.vectordb.backend
    configured_workers = max_workers if max_workers is not None else settings.performance.max_workers
    configured_embedding_threads = (
        embedding_threads if embedding_threads is not None else settings.performance.embedding_threads
    )
    configured_embedding_batch_size = (
        embedding_batch_size
        if embedding_batch_size is not None
        else settings.performance.embedding_batch_size
    )
    target_cpu_utilization = settings.performance.target_cpu_utilization
    reserved_cpu_threads = settings.performance.reserved_cpu_threads
    resolved_worker_count = _resolve_worker_count(
        configured_workers,
        target_cpu_utilization=target_cpu_utilization,
        reserved_cpu_threads=reserved_cpu_threads,
    )
    embedding_batch_size_value = _coerce_positive_int(configured_embedding_batch_size) or 16
    embedding_thread_count = _apply_cpu_thread_limit(
        configured_embedding_threads,
        target_cpu_utilization=target_cpu_utilization,
        reserved_cpu_threads=reserved_cpu_threads,
    )

    log(f"Processing documents from: {input_dir}")
    log(f"Vector store backend: {backend}")
    log(
        "CPU controls: "
        f"logical_cpus={_logical_cpu_count()}, "
        f"target_cpu={_coerce_cpu_target(target_cpu_utilization):.0%}, "
        f"reserved_threads={_coerce_non_negative_int(reserved_cpu_threads, 2)}, "
        f"max_workers={resolved_worker_count}, "
        f"embedding_threads={embedding_thread_count}, "
        f"embedding_batch_size={embedding_batch_size_value}"
    )
    if backend == "faiss":
        log(f"FAISS index location: {FAISS_INDEX_DIR}")
    else:
        log(f"ChromaDB location: {VECTORDB_DIR}")
    print("-" * 50)
    
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
        chunk_args = files_to_chunk
        chunk_workers = min(resolved_worker_count, len(files_to_chunk))
        print(f"  Using {chunk_workers} worker(s) for chunking.")
        with concurrent.futures.ThreadPoolExecutor(max_workers=chunk_workers) as executor:
            # chunk_documents helper fits perfectly here
            results = list(tqdm(
                executor.map(_process_chunking, chunk_args), 
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
    image_format_override = image_format if image_format and image_format != "png" else None
    if include_images:
        log("[2/3] Extracting images from PDFs (Parallel)...")
        step_start = time.perf_counter()
        pdf_files = list(input_dir.glob("**/*.pdf"))
        
        if pdf_files:
            extract_args = [
                (p, image_format_override)
                for p in pdf_files
            ]
            
            extract_workers = min(resolved_worker_count, len(pdf_files))
            print(f"  Using {extract_workers} worker(s) for image extraction.")
            with concurrent.futures.ThreadPoolExecutor(max_workers=extract_workers) as executor:
                results = list(tqdm(
                    executor.map(_process_extraction, extract_args), 
                    total=len(pdf_files), 
                    desc="  Extracting from PDFs"
                ))
                
                for i, extracted in enumerate(results):
                    if extracted:
                        total_images += len(extracted)
                        image_data = _get_vectorization_data(extracted)
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
        chart_processor = _get_chart_processor()
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
    vector_store = None
    if items_to_vectorize:
        log(f"[4/4] Vectorizing and Storing {len(items_to_vectorize)} items...")
        step_start = time.perf_counter()

        vectorizer = _get_vectorizer()
        vector_store = _get_vector_store()
        
        # Extract contents for batch vectorization
        texts = [item["content"] for item in items_to_vectorize]
        
        # Vectorize in one go
        embeddings = vectorizer.vectorize(texts, batch_size=embedding_batch_size_value)
        
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
    if vector_store is not None:
        log(f"  Total items in database: {vector_store.count()}")
    elif items_to_vectorize:
        log(f"  Total items in database: {len(items_to_vectorize)}")
    log("[TIME] Time Report:")
    log(f"  Chunking:      {_format_duration(chunking_time)}")
    if include_images:
        log(f"  Image Extract: {_format_duration(extraction_time)}")
    if include_charts:
        log(f"  Charts:        {_format_duration(chart_time)}")
    log(f"  Vectorization: {_format_duration(vectorize_time)}")
    log(f"  -----------------")
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
    from specrag.ops import search_documents as _ops_search

    start_time = time.perf_counter()
    log(f"Searching for: '{query}'")
    log(f"Using backend: {settings.vectordb.backend}")
    if use_hybrid:
        print("Mode: Hybrid (BM25 + Vector)")
    if images_only:
        print("Filter: Images only")
    print("-" * 50)

    results = _ops_search(
        query=query,
        top_k=top_k,
        save_results=save_results,
        images_only=images_only,
        use_hybrid=use_hybrid,
    )
    search_time = time.perf_counter() - start_time

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
        if not use_hybrid:
            engine = _get_search_engine()
            print(engine.format_results(results, format_type="text"))
        else:
            print(f"Found {len(results)} results:\n")
            for r in results:
                print(f"[{r.rank}] Score: {r.similarity:.4f}")
                print(f"    ID: {r.chunk_id}")
                print(f"    Source: {r.metadata.get('source_file', 'Unknown')}")
                print(f"    Content: {r.document[:200] if r.document else 'N/A'}...")
                print()
    else:
        print("No results found.")

    print(f"\n[TIME] Search completed in {_format_duration(search_time)}")
    return results


def multi_search(
    queries: list[str],
    top_k: int = 5,
    images_only: bool = False,
    use_hybrid: bool = False,
    save_results: bool = True
):
    """
    Search with multiple queries and merge results using RRF.
    
    This improves recall by searching with different phrasings of the same concept.
    
    Args:
        queries: List of search queries (2-5 recommended)
        top_k: Number of final results to return
        images_only: If True, only return image results
        use_hybrid: If True, use BM25+Vector hybrid search
        save_results: If True, save merged results to file
    """
    from specrag.ops import multi_search as _ops_multi_search

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

    final_results = _ops_multi_search(
        queries=queries,
        top_k=top_k,
        images_only=images_only,
        use_hybrid=use_hybrid,
        save_results=save_results,
    )
    search_time = time.perf_counter() - start_time

    if not final_results:
        print("No results found.")
    elif images_only:
        print(f"\nFound {len(final_results)} merged image results:\n")
        for result in final_results:
            image_path = result.metadata.get("image_path", "N/A")
            source = result.metadata.get("source_file", "Unknown")
            page = result.metadata.get("page_number", "?")
            print(f"[{result.rank}] RRF Score: {result.similarity:.4f}")
            print(f"    Image: {image_path}")
            print(f"    Source: {source}, Page {page}")
            print(f"    ID: {result.chunk_id}")
            print()
    else:
        print(f"\nFound {len(final_results)} merged results:\n")
        for result in final_results:
            print(f"[{result.rank}] RRF Score: {result.similarity:.4f}")
            print(f"    ID: {result.chunk_id}")
            print(f"    Source: {result.metadata.get('source_file', 'Unknown')}")
            print(f"    Content: {result.document[:150] if result.document else 'N/A'}...")
            print()

    print(f"[TIME] Multi-search completed in {_format_duration(search_time)}")
    return final_results


def show_stats():
    """Show vector database statistics."""
    from specrag.ops import get_stats

    stats = get_stats()
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
                print(f"  [OK] Cleaned {name}")
            except Exception as e:
                print(f"  [ERROR] Error cleaning {name}: {e}")
        else:
            print(f"  - {name} not exists, skipped")
    
    clean_time = time.perf_counter() - start_time
    
    # Recreate directories
    ensure_directories()
    print(f"\nClean completed! (took {_format_duration(clean_time)})")


def _normalize_doc_id(doc_id: str) -> str:
    """Normalize document ID by removing image file extensions."""
    from specrag.ops import normalize_doc_id

    return normalize_doc_id(doc_id)


def _rebuild_combined_tags(original_tags: str, user_tags: str) -> str:
    """Helper to combine original and user tags into single string."""
    from specrag.ops._helpers import rebuild_combined_tags

    return rebuild_combined_tags(original_tags, user_tags)


def _rebuild_content_with_tags(base_content: str, all_tags: str) -> str:
    """Helper to rebuild content with proper tag boosting."""
    from specrag.ops._helpers import rebuild_content_with_tags

    return rebuild_content_with_tags(base_content, all_tags)


def add_tag(doc_id: str, tag: str):
    """
    Add a user tag to a document's metadata AND update its vector embedding.
    User tags are stored separately from original (auto-extracted) tags.
    """
    from specrag.ops import add_tag as _ops_add_tag
    from specrag.ops.errors import ChunkNotFoundError, DuplicateTagError, OpsError

    try:
        result = _ops_add_tag(doc_id, tag)
        print("Re-calculating vector embedding...")
        print(f"Successfully added tag '{tag}' to document '{result['chunk_id']}'")
        print(f"  Original tags: {result['original_tags'] or '(none)'}")
        print(f"  User tags:     {result['user_tags']}")
        print(f"  Combined:      {result['combined_tags']}")
        print("Vector embedding updated.")
        print(f"\n[TIME] Time Report:")
        print(f"  Embedding:  {_format_duration(result['embedding_seconds'])}")
        print(f"  Total:      {_format_duration(result['total_seconds'])}")
    except DuplicateTagError as e:
        print(str(e))
    except ChunkNotFoundError as e:
        print(f"Error: {e}")
    except OpsError as e:
        print(f"Error adding tag: {e}")
    except Exception as e:
        print(f"Error adding tag: {e}")


def remove_tag(doc_id: str, tag: str):
    """
    Remove a user-added tag from a document.
    Only user tags can be removed; original tags are immutable.
    """
    from specrag.ops import remove_tag as _ops_remove_tag
    from specrag.ops.errors import (
        ChunkNotFoundError,
        OpsError,
        TagImmutableError,
        TagNotFoundError,
    )

    try:
        result = _ops_remove_tag(doc_id, tag)
        print("Re-calculating vector embedding...")
        print(f"Successfully removed tag '{tag}' from document '{result['chunk_id']}'")
        print(f"  Original tags: {result['original_tags'] or '(none)'}")
        print(f"  User tags:     {result['user_tags'] or '(none)'}")
        print(f"  Combined:      {result['combined_tags'] or '(none)'}")
        print("Vector embedding updated.")
        print("\n[TIME] Time Report:")
        print(f"  Embedding:  {_format_duration(result['embedding_seconds'])}")
        print(f"  Total:      {_format_duration(result['total_seconds'])}")
    except TagImmutableError as e:
        print(f"Error: {e}")
        print("Use 'resettags' to restore only original tags.")
    except TagNotFoundError as e:
        print(f"Error: {e}")
    except ChunkNotFoundError as e:
        print(f"Error: {e}")
    except OpsError as e:
        print(f"Error removing tag: {e}")
    except Exception as e:
        print(f"Error removing tag: {e}")


def reset_tags(doc_id: str):
    """
    Reset tags to original (auto-extracted) tags, removing all user-added tags.
    """
    from specrag.ops import reset_tags as _ops_reset_tags
    from specrag.ops.errors import ChunkNotFoundError, OpsError

    try:
        result = _ops_reset_tags(doc_id)
        if not result.get("changed", True):
            print(result.get("message", f"No user tags to reset for document '{doc_id}'."))
            print(f"Current tags: {result.get('original_tags') or '(none)'}")
            return

        print("Re-calculating vector embedding...")
        print(f"Successfully reset tags for document '{result['chunk_id']}'")
        print(f"  Removed user tags: {result.get('removed_user_tags', '')}")
        print(f"  Restored to:       {result['original_tags'] or '(none)'}")
        print("Vector embedding updated.")
        print("\n[TIME] Time Report:")
        print(f"  Embedding:  {_format_duration(result['embedding_seconds'])}")
        print(f"  Total:      {_format_duration(result['total_seconds'])}")
    except ChunkNotFoundError as e:
        print(f"Error: {e}")
    except OpsError as e:
        print(f"Error resetting tags: {e}")
    except Exception as e:
        print(f"Error resetting tags: {e}")


def list_tags(doc_id: str):
    """
    List tags for a document, showing original and user-added tags separately.
    """
    from specrag.ops import list_tags as _ops_list_tags
    from specrag.ops.errors import ChunkNotFoundError

    try:
        result = _ops_list_tags(doc_id)
        print(f"Tags for {result['chunk_id']}:")
        print(f"  Original (auto-extracted): {result['original_tags'] or '(none)'}")
        print(f"  User-added:                {result['user_tags'] or '(none)'}")
        print(f"  Combined:                  {result['combined_tags'] or '(none)'}")
    except ChunkNotFoundError as e:
        print(str(e))
    except Exception as e:
        print(f"Error listing tags: {e}")


def resolve_chunk_id(identifier: str) -> str:
    """
    Resolve an identifier (chunk_id or image_path) to a chunk_id.
    
    Args:
        identifier: Either a chunk_id (e.g., "HID_SPEC_V10.pdf_p42") 
                    or an image_path (e.g., "data/extracted/HID_SPEC_V10.pdf_p42.png")
    
    Returns:
        The resolved chunk_id, or the original identifier if no match found.
    """
    from specrag.ops import resolve_chunk_id as _ops_resolve

    return _ops_resolve(identifier)


def add_knowledge(identifier: str, knowledge_text: str):
    """
    Add knowledge to a document's metadata AND update its vector embedding.
    Knowledge is appended to existing knowledge.
    
    Args:
        identifier: chunk_id or image_path
        knowledge_text: The knowledge text to add (markdown supported)
    """
    from specrag.ops import add_knowledge as _ops_add_knowledge
    from specrag.ops.errors import ChunkNotFoundError, OpsError

    try:
        result = _ops_add_knowledge(identifier, knowledge_text)
        print("Re-calculating vector embedding...")
        print(f"Successfully added knowledge to document '{result['chunk_id']}'")
        print(f"Knowledge preview: {knowledge_text[:100]}...")
        print("\n[TIME] Time Report:")
        print(f"  Embedding:  {_format_duration(result['embedding_seconds'])}")
        print(f"  Total:      {_format_duration(result['total_seconds'])}")
    except ChunkNotFoundError as e:
        print(f"Error: {e}")
    except OpsError as e:
        print(f"Error adding knowledge: {e}")
    except Exception as e:
        print(f"Error adding knowledge: {e}")
        import traceback
        traceback.print_exc()


def update_knowledge(identifier: str, knowledge_text: str):
    """
    Replace existing knowledge with new knowledge.
    
    Args:
        identifier: chunk_id or image_path
        knowledge_text: The new knowledge text (replaces existing)
    """
    from specrag.ops import update_knowledge as _ops_update_knowledge
    from specrag.ops.errors import ChunkNotFoundError, OpsError

    try:
        result = _ops_update_knowledge(identifier, knowledge_text)
        print("Re-calculating vector embedding...")
        print(f"Successfully updated knowledge for document '{result['chunk_id']}'")
        print(f"New knowledge: {knowledge_text[:100]}...")
        print("\n[TIME] Time Report:")
        print(f"  Embedding:  {_format_duration(result['embedding_seconds'])}")
        print(f"  Total:      {_format_duration(result['total_seconds'])}")
    except ChunkNotFoundError as e:
        print(f"Error: {e}")
    except OpsError as e:
        print(f"Error updating knowledge: {e}")
    except Exception as e:
        print(f"Error updating knowledge: {e}")
        import traceback
        traceback.print_exc()


def get_knowledge(identifier: str):
    """
    Get knowledge for a document.
    
    Args:
        identifier: chunk_id or image_path
    """
    from specrag.ops import get_knowledge as _ops_get_knowledge
    from specrag.ops.errors import ChunkNotFoundError

    try:
        result = _ops_get_knowledge(identifier)
        if result["has_knowledge"]:
            print(f"Knowledge for {result['chunk_id']}:")
            print("-" * 50)
            print(result["knowledge"])
            print("-" * 50)
        else:
            print(f"No knowledge found for {result['chunk_id']}")
    except ChunkNotFoundError as e:
        print(str(e))
    except Exception as e:
        print(f"Error getting knowledge: {e}")


def list_docs():
    """List source files that have been vectorized."""
    from specrag.ops import list_documents

    try:
        docs = list_documents()
        print(f"Found {len(docs)} files:")
        print("-" * 50)
        for i, item in enumerate(docs):
            print(f"Source: {item['source']} | Chunks: {item['chunk_count']}")
            if i + 1 >= 10000:
                print(f"... and {len(docs) - 10000} more.")
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
        default=settings.paths.documents_dir,
        help=f"Input directory (default from setting.json: {settings.paths.documents_dir})"
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
    process_parser.add_argument(
        "--fullpage", "-fp",
        action="store_true",
        help="Capture full pages as images (Context-rich, best for RAG)"
    )
    process_parser.add_argument(
        "--format", "-fmt",
        type=str,
        choices=["png", "jpeg", "jpg"],
        default="png",
        help="Image format for fullpage mode (default: png, use jpeg for smaller files)"
    )
    process_parser.add_argument(
        "--workers", "-w",
        type=str,
        default=settings.performance.max_workers,
        help=f"Max parallel workers for chunking and extraction (default: {settings.performance.max_workers})"
    )
    process_parser.add_argument(
        "--embedding-threads",
        type=str,
        default=settings.performance.embedding_threads,
        help=f"CPU threads for embedding/vectorization (default: {settings.performance.embedding_threads})"
    )
    process_parser.add_argument(
        "--embedding-batch-size",
        type=int,
        default=settings.performance.embedding_batch_size,
        help=f"Embedding batch size (default: {settings.performance.embedding_batch_size})"
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
    msearch_parser.add_argument(
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
        help="List tags for a document (shows original vs user-added)"
    )
    list_tag_parser.add_argument(
        "doc_id",
        type=str,
        help="Document ID"
    )

    # Remove Tag command
    remove_tag_parser = subparsers.add_parser(
        "removetag",
        help="Remove a user-added tag from a document"
    )
    remove_tag_parser.add_argument(
        "doc_id",
        type=str,
        help="Document ID"
    )
    remove_tag_parser.add_argument(
        "tag",
        type=str,
        help="Tag to remove (only user-added tags can be removed)"
    )

    # Reset Tags command
    reset_tags_parser = subparsers.add_parser(
        "resettags",
        help="Reset tags to original (remove all user-added tags)"
    )
    reset_tags_parser.add_argument(
        "doc_id",
        type=str,
        help="Document ID"
    )

    # Add Knowledge command
    add_knowledge_parser = subparsers.add_parser(
        "addknowledge",
        help="Add knowledge (description) to a document"
    )
    add_knowledge_parser.add_argument(
        "identifier",
        type=str,
        help="Document ID or image path"
    )
    add_knowledge_parser.add_argument(
        "knowledge",
        type=str,
        help="Knowledge text to add (markdown supported)"
    )

    # Update Knowledge command
    update_knowledge_parser = subparsers.add_parser(
        "updateknowledge",
        help="Replace existing knowledge with new knowledge"
    )
    update_knowledge_parser.add_argument(
        "identifier",
        type=str,
        help="Document ID or image path"
    )
    update_knowledge_parser.add_argument(
        "knowledge",
        type=str,
        help="New knowledge text (replaces existing)"
    )

    # Get Knowledge command
    get_knowledge_parser = subparsers.add_parser(
        "getknowledge",
        help="Get knowledge for a document"
    )
    get_knowledge_parser.add_argument(
        "identifier",
        type=str,
        help="Document ID or image path"
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

    # Server command
    server_parser = subparsers.add_parser(
        "server",
        help="Start the RAG API server"
    )
    server_parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host address (default: 0.0.0.0)"
    )
    server_parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port number (default: 8080)"
    )
    
    
    args = parser.parse_args()
    
    # Ensure directories exist
    ensure_directories()
    
    if args.command == "process":
        for option_name, option_value in (
            ("--workers", args.workers),
            ("--embedding-threads", args.embedding_threads),
        ):
            if not _is_auto_cpu_value(option_value) and _coerce_positive_int(option_value) is None:
                parser.error(f"{option_name} must be 'auto' or an integer >= 1")

        if args.embedding_batch_size is not None and args.embedding_batch_size < 1:
            parser.error("--embedding-batch-size must be >= 1")

        # Manual Validation for Strategy
        if not args.no_images:
            if not args.fullpage:
                parser.error("When processing images (default), you MUST specify full-page extraction: --fullpage (-fp)")
        
        process_documents(
            input_dir=args.input,
            include_charts=not args.no_charts,
            include_images=not args.no_images,
            image_format=args.format,
            max_workers=args.workers,
            embedding_threads=args.embedding_threads,
            embedding_batch_size=args.embedding_batch_size,
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
            use_hybrid=args.hybrid,
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

    elif args.command == "removetag":
        remove_tag(args.doc_id, args.tag)

    elif args.command == "resettags":
        reset_tags(args.doc_id)

    elif args.command == "addknowledge":
        add_knowledge(args.identifier, args.knowledge)

    elif args.command == "updateknowledge":
        update_knowledge(args.identifier, args.knowledge)

    elif args.command == "getknowledge":
        get_knowledge(args.identifier)

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

    elif args.command == "server":
        from specrag.api_server import main as run_server
        run_server(host=args.host, port=args.port)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
