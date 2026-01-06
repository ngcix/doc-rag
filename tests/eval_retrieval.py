import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.main import search_documents, multi_search, log

def load_dataset(path: str) -> List[Dict]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def evaluate_query(query_data: Dict, top_k: int = 5) -> Dict:
    query_text = query_data["query"]
    expected_ids = query_data["expected_ids"]
    mode = query_data.get("mode", "text")
    
    print(f"\nEvaluating: '{query_text}' (Mode: {mode})")
    
    start_time = time.perf_counter()
    
    # Execute Search based on mode
    results = []
    if mode == "pic":
        results = search_documents(query_text, top_k=top_k, images_only=True, save_results=False)
    elif mode == "hybrid":
        results = search_documents(query_text, top_k=top_k, use_hybrid=True, save_results=False)
    elif mode == "msearch":
         # Assumption: 'query' field might be a list for msearch, or we split it
         queries = query_text if isinstance(query_text, list) else [query_text]
         results = multi_search(queries, top_k=top_k, save_results=False)
    else:
        results = search_documents(query_text, top_k=top_k, save_results=False)
        
    duration = time.perf_counter() - start_time
    
    # Analyze Results
    hit = False
    rank = None
    found_id = None
    
    print(f"  Top {top_k} Results:")
    for i, res in enumerate(results):
        # Result ID format usually: 'filename_pPage'
        # We need to match loose or exact
        res_id = res.chunk_id
        # Also check image_path if it's an image result
        img_path = res.metadata.get("image_path", "")
        
        is_match = False
        for expected in expected_ids:
            if expected in res_id or (img_path and expected in img_path):
                is_match = True
                break
        
        mark = "✅" if is_match else "❌"
        print(f"    {i+1}. [{mark}] {res_id} (Score: {res.similarity:.4f})")
        
        if is_match and not hit:
            hit = True
            rank = i + 1
            found_id = res_id
            
    return {
        "id": query_data.get("id"),
        "query": query_text,
        "hit": hit,
        "rank": rank,
        "duration": duration
    }

def main():
    parser = argparse.ArgumentParser(description="Evaluate RAG Retrieval Performance")
    parser.add_argument("--dataset", default="tests/data/golden_dataset.json", help="Path to golden dataset")
    parser.add_argument("--top-k", type=int, default=5, help="Top K results to check")
    args = parser.parse_args()
    
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"Dataset not found: {dataset_path}")
        return
        
    dataset = load_dataset(dataset_path)
    print(f"Loaded {len(dataset)} test cases from {dataset_path}")
    
    metrics = {
        "total": 0,
        "hits": 0,
        "mrr_sum": 0,
        "total_time": 0
    }
    
    for item in dataset:
        metrics["total"] += 1
        result = evaluate_query(item, top_k=args.top_k)
        
        metrics["total_time"] += result["duration"]
        if result["hit"]:
            metrics["hits"] += 1
            metrics["mrr_sum"] += 1.0 / result["rank"]
            
    # Summary
    hit_rate = (metrics["hits"] / metrics["total"]) * 100 if metrics["total"] > 0 else 0
    mrr = metrics["mrr_sum"] / metrics["total"] if metrics["total"] > 0 else 0
    avg_time = metrics["total_time"] / metrics["total"] if metrics["total"] > 0 else 0
    
    print("\n" + "="*40)
    print("📊 EVALUATION SUMMARY")
    print("="*40)
    print(f"Total Queries: {metrics['total']}")
    print(f"Hit Rate @ {args.top_k}:  {hit_rate:.2f}% ({metrics['hits']}/{metrics['total']})")
    print(f"MRR:           {mrr:.4f}")
    print(f"Avg Latency:   {avg_time*1000:.2f} ms")
    print("="*40)

if __name__ == "__main__":
    main()
