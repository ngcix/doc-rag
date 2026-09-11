#!/usr/bin/env python3
"""Analyze extracted images and save their descriptions as RAG knowledge."""

import argparse
import gc
import os
import time
from pathlib import Path

import psutil
import requests

from specrag.config import EXTRACTED_IMAGES_DIR
from specrag.image_analysis import analyze_image, extract_content
from specrag.ops import add_knowledge


def get_chunk_id_from_image_path(image_path: Path) -> str:
    """Convert an image filename to its chunk ID."""
    filename = image_path.stem  # Remove extension
    return filename


def process_single_image(image_path: Path, dry_run: bool = False, image_index: int = 0, total_images: int = 0, session: requests.Session | None = None) -> tuple[bool, float]:
    """
    Process a single image: analyze and add knowledge to RAG system.

    Args:
        image_path: Path to the image file
        dry_run: If True, only print what would be done without actually calling APIs
        image_index: Current image index (1-based) for display
        total_images: Total number of images being processed
        session: Optional requests Session for connection reuse

    Returns:
        Tuple of (success, processing_time_seconds)
    """
    start_time = time.time()

    if dry_run:
        print(f"[{image_index}/{total_images}] Processing {image_path.name}")
        print("  [DRY RUN] Would analyze image and add knowledge")
        return True, 0.0

    print(f"[{image_index}/{total_images}] Processing {image_path.name}")

    # Step 1: Detailed image analysis
    detailed_prompt = """
Analyze this technical diagram/image in extreme detail. Describe only what
you observe, without asking questions or requesting more information.
Focus on factual observations:
1. What type of diagram/chart/image this is
2. All visual elements, components, and their relationships
3. Any text, labels, or annotations present
4. The overall purpose or function represented
5. Technical specifications or data shown
6. Connections, flows, or processes depicted
7. Any notable patterns, structures, or key features
Provide only factual descriptions of what is visible in the image.
    """.strip()

    analysis_start = time.time()
    analysis_result = analyze_image(image_path, detailed_prompt, session)
    analysis_time = time.time() - analysis_start

    if "error" in analysis_result:
        print(f"  [ERROR] Failed to analyze image: {analysis_result['error']}")
        return False, time.time() - start_time

    # Extract only the content part from analysis result
    analysis_text = extract_content(analysis_result)

    if not analysis_text:
        print("  [ERROR] No analysis text received")
        # Active cleanup
        if "analysis_result" in locals():
            del analysis_result
        return False, time.time() - start_time

    print(f"  Image analysis ({analysis_time:.2f}s): {analysis_text[:200]}...")

    # Step 2: Add knowledge to RAG system (only content part)
    chunk_id = get_chunk_id_from_image_path(image_path)

    knowledge_start = time.time()
    try:
        # Only add the analysis content without additional metadata
        add_knowledge(chunk_id, analysis_text)
    except Exception as e:
        print(f"  [ERROR] Failed to add knowledge: {e}")
        # Active cleanup
        if "analysis_result" in locals():
            del analysis_result
        if analysis_text:
            del analysis_text
        if "chunk_id" in locals():
            del chunk_id
        return False, time.time() - start_time

    knowledge_time = time.time() - knowledge_start

    # Active cleanup of large objects
    if "analysis_result" in locals():
        del analysis_result
    if analysis_text:
        del analysis_text
    if "chunk_id" in locals():
        del chunk_id

    total_time = time.time() - start_time
    print(f"  Total time: {total_time:.2f}s")
    return True, total_time


def process_image(
    image_path: Path,
    query: str = "",
    dry_run: bool = False,
    image_index: int = 0,
    total_images: int = 0,
    session: requests.Session | None = None,
) -> tuple[bool, str | None]:
    """
    Analyze an image using the Gauss AI model and return the analysis text.
    Does NOT add the analysis to the RAG knowledge base.
    Returns (success, analysis_text_or_None).
    """
    if dry_run:
        print(f"[{image_index}/{total_images}] (Dry run) Would analyze {image_path.name}")
        return True, None

    print(f"[{image_index}/{total_images}] Analyzing {image_path.name}")
    detailed_prompt = f"""
Analyze this technical diagram/image in extreme detail. Describe only what
you observe, without asking questions or requesting more information. Focus
on factual observations, especially this query: {query}

1. What type of diagram/chart/image this is
2. All visual elements, components, and their relationships, particularly those related to the query
3. Any text, labels, or annotations present, especially those relevant to the query
4. The overall purpose or function represented, with emphasis on the query
5. Technical specifications or data shown, particularly those connected to the query
6. Connections, flows, or processes depicted, with a focus on how they relate to the query
7. Any notable patterns, structures, or key features, especially those that address the query
Provide only factual descriptions of what is visible in the image, ensuring that the query is explicitly addressed in your analysis.
""".strip()
    analysis_result = analyze_image(image_path, detailed_prompt, session)
    # print(analysis_result)
    if "error" in analysis_result:
        print(f"  [ERROR] Failed to analyze image: {analysis_result['error']}")
        return False, None

    analysis_text = extract_content(analysis_result)
    if not analysis_text:
        print("  [ERROR] No analysis text received")
        return False, None

    print(f"{get_chunk_id_from_image_path(image_path)} has been analyzed!")
    # Optionally, you could return processing time as well, but this function returns only success and text.
    return True, analysis_text


def get_memory_usage() -> float:
    """Get current memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def process_all_images(images_dir: Path, dry_run: bool = False, limit: int | None = None) -> None:
    """
    Process all images in the extracted_images directory.

    Args:
        images_dir: Directory containing extracted images
        dry_run: If True, only print what would be done
        limit: Maximum number of images to process (None for all)
    """
    if not images_dir.exists():
        print(f"Error: Directory {images_dir} does not exist")
        return

    # Supported image extensions
    image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"}

    # Get all image files
    image_files = []
    for ext in image_extensions:
        image_files.extend(images_dir.glob(f"*{ext}"))

    # Sort for consistent processing order
    image_files.sort()

    if not image_files:
        print(f"No image files found in {images_dir}")
        return

    print(f"Found {len(image_files)} images to process")
    if limit:
        image_files = image_files[:limit]
        print(f"Limited to {len(image_files)} images")

    if dry_run:
        print("\n=== DRY RUN MODE ===")
        print("Would process the following images:")
        for i, image_path in enumerate(image_files, 1):
            print(f"  {i}. {image_path.name}")
        return

    # Create session for connection reuse
    session = requests.Session()

    # Process each image
    successful = 0
    failed = 0
    total_processing_time = 0.0

    print(f"\n=== Processing {len(image_files)} images ===")
    start_time = time.time()

    # Memory monitoring
    start_memory = get_memory_usage()
    print(f"Starting memory usage: {start_memory:.2f} MB")

    for i, image_path in enumerate(image_files, 1):
        try:
            success, processing_time = process_single_image(image_path, dry_run=False, image_index=i, total_images=len(image_files), session=session)
            total_processing_time += processing_time
            if success:
                successful += 1
            else:
                failed += 1

            # Memory monitoring and garbage collection every 10 images
            if i % 10 == 0:
                current_memory = get_memory_usage()
                memory_increase = current_memory - start_memory
                gc.collect()
                print(f"  [Memory cleanup] Processed {i}/{len(image_files)} images")
                print(f"  Current memory: {current_memory:.2f} MB (+{memory_increase:.2f} MB)")

                # Warning if memory usage is too high
                if memory_increase > 500:  # 500MB threshold
                    print(f"  [WARN] High memory usage detected ({memory_increase:.2f} MB)")

        except Exception as e:
            if not dry_run:
                print(f"[{i}/{len(image_files)}] Processing {image_path.name}")
            print(f"  [ERROR] Unexpected error processing {image_path.name}: {e}")
            failed += 1

    total_time = time.time() - start_time

    # Final garbage collection and memory report
    gc.collect()
    end_memory = get_memory_usage()
    print(f"Final memory usage: {end_memory:.2f} MB")

    # Summary
    print("\n=== Processing Summary ===")
    print(f"Total images: {len(image_files)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    if failed > 0:
        print(f"Success rate: {successful / len(image_files) * 100:.1f}%")
    print(f"Total processing time: {total_time:.2f}s")
    print(f"Average time per image: {total_processing_time / len(image_files):.2f}s")
    if successful > 0:
        print(f"Average time per successful image: {total_processing_time / successful:.2f}s")


def main():
    """Main function to demonstrate usage."""
    parser = argparse.ArgumentParser(description="Analyze extracted images using Gauss AI and add knowledge to RAG system")
    parser.add_argument("--images-dir", default=str(EXTRACTED_IMAGES_DIR), help=f"Directory containing extracted images (default: {EXTRACTED_IMAGES_DIR})")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually processing")
    parser.add_argument("--limit", type=int, help="Limit number of images to process")

    args = parser.parse_args()

    # Convert string path to Path object
    images_dir = Path(args.images_dir)

    # Check if directory exists
    if not images_dir.exists():
        print(f"Error: Directory {images_dir} does not exist")
        return

    print("Starting image analysis and knowledge addition process...")
    print(f"Images directory: {images_dir}")
    print(f"Dry run mode: {args.dry_run}")
    if args.limit:
        print(f"Processing limit: {args.limit} images")

    process_all_images(images_dir, dry_run=args.dry_run, limit=args.limit)


if __name__ == "__main__":
    main()
