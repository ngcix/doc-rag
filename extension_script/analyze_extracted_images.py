#!/usr/bin/env python3
"""
Script to add knowledge/tags to extracted images in RAG system.

This script:
1. Browses all images in data/extracted_images directory
2. Allows manual addition of knowledge and tags to RAG system
3. Can be extended to use RAG's built-in analysis capabilities
"""

import requests
import json
import os
from pathlib import Path
import sys
import argparse
import time
from typing import Dict, List, Optional, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import RAG system functions
from src.main import add_knowledge, add_tag

# Gauss API Configuration
GAUSS_CLIENT_KEY = os.environ.get("GAUSS_CLIENT_KEY")
GAUSS_TOKEN = os.environ.get("GAUSS_TOKEN")
GAUSS_ENDPOINT_URL = os.environ.get("GAUSS_ENDPOINT_URL")
GAUSS_USER_EMAIL = os.environ.get("GAUSS_USER_EMAIL")

# Model IDs
YOUR_TEXT_MODEL_ID = "0198f11e-ceab-71c3-8fb1-d077d6331843"  # GaussO Flash
YOUR_I2T_MODEL_ID = "019a37fd-0c64-72c5-bb17-3b590f80be57"   # GaussO MM - I2T

def get_gauss_headers() -> Dict[str, str]:
    """Get headers for Gauss API requests."""
    return {
        "x-generative-ai-client": GAUSS_CLIENT_KEY or "",
        "x-openapi-token": GAUSS_TOKEN or "",
        "x-generative-ai-user-email": GAUSS_USER_EMAIL or "",
    }

def get_llm_config() -> str:
    """Get LLM configuration."""
    return json.dumps({
        "max_new_tokens": 2024,
        "seed": None,
        "top_k": 14,
        "top_p": 0.94,
        "temperature": 0.4,
        "repetition_penalty": 1.04,
    })

def analyze_image_with_ai(image_path: Path, prompt: str) -> Dict:
    """
    Analyze an image using Gauss AI model.
    
    Args:
        image_path: Path to the image file
        prompt: Prompt to send to the AI model
        
    Returns:
        JSON response from the AI model
    """
    if not GAUSS_CLIENT_KEY or not GAUSS_TOKEN or not GAUSS_ENDPOINT_URL or not GAUSS_USER_EMAIL:
        raise ValueError("Missing Gauss API credentials. Please set the required environment variables.")

    headers = get_gauss_headers()
    llm_config = get_llm_config()
    
    form_data = {
        "modelIds": [YOUR_TEXT_MODEL_ID, YOUR_I2T_MODEL_ID],
        "contents": [f"{prompt}: {image_path.name}"],
        "llmConfig": llm_config,
        "isStream": False,
    }
    
    api_endpoint_url = f"{GAUSS_ENDPOINT_URL}/openapi/chat/v1/messages-with-models"
    
    try:
        with image_path.open("rb") as f:
            response = requests.post(
                api_endpoint_url, 
                headers=headers, 
                data=form_data, 
                files=[("files", f)]
            )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error analyzing image {image_path}: {e}")
        return {"error": str(e)}

def extract_content_from_response(response: Dict) -> str:
    """
    Extract only the content part from Gauss API response.
    Uses jq -r '.actions[0].answer' equivalent logic.

    Args:
        response: API response from Gauss AI

    Returns:
        Content string from the response
    """
    if not isinstance(response, dict):
        return str(response)
        
    if "error" in response:
        return ""
        
    # Extract content using jq equivalent: .actions[0].answer
    try:
        # Try Gauss API specific structure first
        if "actions" in response and len(response["actions"]) > 0:
            action = response["actions"][0]
            if "answer" in action:
                return str(action["answer"])
            elif "content" in action:
                return str(action["content"])
        
        # Fallback to existing logic
        if "choices" in response and len(response["choices"]) > 0:
            choice = response["choices"][0]
            if "message" in choice:
                return choice["message"].get("content", "")
            elif "content" in choice:
                return choice["content"]
            else:
                return ""
        elif "result" in response:
            return str(response["result"])
        else:
            # Try to find content in other possible structures
            return str(response)
    except Exception:
        # Return empty string if extraction fails
        return ""

def generate_tags_from_analysis(image_path: Path, analysis_result: Dict) -> List[str]:
    """
    Generate tags from image analysis result.

    Args:
        image_path: Path to the image file
        analysis_result: Analysis result from Gauss AI

    Returns:
        List of tags
    """
    if "error" in analysis_result:
        print(f"Error in analysis for {image_path}, cannot generate tags")
        return []

    # Extract only the content part from analysis result
    analysis_text = extract_content_from_response(analysis_result)

    # Create prompt for tag generation
    tag_prompt = f"""
Based on this detailed analysis of the image: '{analysis_text}', please provide EXACTLY 3-5 concise tags (2-5 words each) that best describe what this image represents. CRITICAL: Return ONLY a simple comma-separated list with NO additional text, explanations, formatting, or questions. Example format: bluetooth,connection diagram,audio streaming,device pairing. Your response must contain only tags in this exact format:
    """.strip()

    # Call Gauss API again to generate tags
    tag_result = analyze_image_with_ai(image_path, tag_prompt)
    
    if "error" in tag_result:
        print(f"Error generating tags for {image_path}")
        return []

    # Extract only the content part from tag result
    tags_text = extract_content_from_response(tag_result)

    # Parse tags (comma-separated)
    tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
    return tags[:5]  # Limit to 5 tags maximum

def get_chunk_id_from_image_path(image_path: Path) -> str:
    """
    Convert image path to chunk_id format.
    Example: data/extracted_images/A2DP_v1.4.1_p14_0.png -> A2DP_v1.4.1_p14_0
    """
    filename = image_path.stem  # Remove extension
    return filename

def process_single_image(image_path: Path, dry_run: bool = False, image_index: int = 0, total_images: int = 0) -> Tuple[bool, float]:
    """
    Process a single image: analyze, generate tags, add to RAG system.
    
    Args:
        image_path: Path to the image file
        dry_run: If True, only print what would be done without actually calling APIs
        image_index: Current image index (1-based) for display
        total_images: Total number of images being processed
        
    Returns:
        Tuple of (success, processing_time_seconds)
    """
    start_time = time.time()
    
    if dry_run:
        print(f"[{image_index}/{total_images}] Processing {image_path.name}")
        print(f"  [DRY RUN] Would analyze image and add knowledge/tags")
        return True, 0.0

    print(f"[{image_index}/{total_images}] Processing {image_path.name}")
    
    # Step 1: Detailed image analysis
    detailed_prompt = """
Analyze this technical diagram/image in extreme detail. Please describe only what you observe in the image, without asking questions or requesting additional information. Focus on factual observations only:
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
    analysis_result = analyze_image_with_ai(image_path, detailed_prompt)
    analysis_time = time.time() - analysis_start
    
    if "error" in analysis_result:
        print(f"  ❌ Failed to analyze image: {analysis_result['error']}")
        return False, time.time() - start_time

    # Extract only the content part from analysis result
    analysis_text = extract_content_from_response(analysis_result)

    if not analysis_text:
        print("  ❌ No analysis text received")
        return False, time.time() - start_time

    print(f"  Phân tích ảnh (thời gian: {analysis_time:.2f}s): {analysis_text[:200]}...")

    # Step 2: Generate tags from analysis
    tag_start = time.time()
    tags = generate_tags_from_analysis(image_path, analysis_result)
    tag_time = time.time() - tag_start
    
    tag_list = ", ".join(tags) if tags else "No tags generated"
    print(f"  Generate tags (thời gian: {tag_time:.2f}s): {tag_list}")

    # Step 3: Add knowledge to RAG system (only content part)
    chunk_id = get_chunk_id_from_image_path(image_path)
    
    knowledge_start = time.time()
    try:
        # Only add the analysis content without additional metadata
        add_knowledge(chunk_id, analysis_text)
    except Exception as e:
        print(f"  ❌ Failed to add knowledge: {e}")
        return False, time.time() - start_time
    knowledge_time = time.time() - knowledge_start

    # Step 4: Add tags to RAG system (batch mode)
    tag_add_start = time.time()
    if tags:
        # Join all tags with comma and add them in one call
        tags_string = ",".join(tags)
        try:
            add_tag(chunk_id, tags_string)
        except Exception as e:
            print(f"    ❌ Failed to add tags '{tags_string}': {e}")
    tag_add_time = time.time() - tag_add_start

    total_time = time.time() - start_time
    print(f"  Total time: {total_time:.2f}s")
    return True, total_time

def process_all_images(images_dir: Path, dry_run: bool = False, limit: Optional[int] = None) -> None:
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
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'}
    
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

    # Process each image
    successful = 0
    failed = 0
    total_processing_time = 0.0
    
    print(f"\n=== Processing {len(image_files)} images ===")
    start_time = time.time()
    
    for i, image_path in enumerate(image_files, 1):
        try:
            success, processing_time = process_single_image(image_path, dry_run=False, image_index=i, total_images=len(image_files))
            total_processing_time += processing_time
            if success:
                successful += 1
            else:
                failed += 1
        except Exception as e:
            if not dry_run:
                print(f"[{i}/{len(image_files)}] Processing {image_path.name}")
            print(f"  ❌ Unexpected error processing {image_path.name}: {e}")
            failed += 1

    total_time = time.time() - start_time
    
    # Summary
    print(f"\n=== Processing Summary ===")
    print(f"Total images: {len(image_files)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    if failed > 0:
        print(f"Success rate: {successful/len(image_files)*100:.1f}%")
    print(f"Total processing time: {total_time:.2f}s")
    print(f"Average time per image: {total_processing_time/len(image_files):.2f}s")
    if successful > 0:
        print(f"Average time per successful image: {total_processing_time/successful:.2f}s")

def main():
    """Main function to demonstrate usage."""
    parser = argparse.ArgumentParser(
        description="Analyze extracted images using Gauss AI and add to RAG system"
    )
    parser.add_argument(
        "--images-dir", 
        default="data/extracted_images",
        help="Directory containing extracted images (default: data/extracted_images)"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Show what would be done without actually processing"
    )
    parser.add_argument(
        "--limit", 
        type=int,
        help="Limit number of images to process"
    )
    
    args = parser.parse_args()
    
    # Convert string path to Path object
    images_dir = Path(args.images_dir)
    
    # Check if directory exists
    if not images_dir.exists():
        print(f"Error: Directory {images_dir} does not exist")
        return
    
    print("Starting image analysis and knowledge tagging process...")
    print(f"Images directory: {images_dir}")
    print(f"Dry run mode: {args.dry_run}")
    if args.limit:
        print(f"Processing limit: {args.limit} images")
    
    process_all_images(images_dir, dry_run=args.dry_run, limit=args.limit)

if __name__ == "__main__":
    main()
