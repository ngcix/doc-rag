"""Test search for images - output to file."""
from src.search.engine import SearchEngine

engine = SearchEngine()

output_lines = []
output_lines.append("="*70)
output_lines.append("SEARCH TEST: Tim kiem images trong database")
output_lines.append("="*70)

# Search for images  
query = "diagram figure image"

output_lines.append(f"\nQuery: '{query}'")
output_lines.append("-"*70)

results = engine.search(query, top_k=10)

image_count = 0
text_count = 0

for r in results:
    meta = r.metadata or {}
    item_type = meta.get('type', 'text_chunk')
    
    if item_type == 'extracted_image':
        image_count += 1
        output_lines.append(f"\n[{r.rank}] [IMAGE] (Score: {r.similarity:.4f})")
        output_lines.append(f"    Region Type: {meta.get('region_type', 'unknown')}")
        output_lines.append(f"    Page: {meta.get('page_number', '?')}")
        # Get just filename
        img_path = meta.get('image_path', '')
        if img_path:
            img_name = img_path.split('\\')[-1].split('/')[-1]
            output_lines.append(f"    Image File: {img_name}")
        # Show content that was vectorized  
        content = r.document.replace('\n', ' | ')[:300]
        output_lines.append(f"    Vectorized Text: {content}...")
    else:
        text_count += 1
        output_lines.append(f"\n[{r.rank}] [TEXT] (Score: {r.similarity:.4f})")
        content = r.document.replace('\n', ' ')[:150]
        output_lines.append(f"    Content: {content}...")

output_lines.append("\n" + "="*70)
output_lines.append(f"SUMMARY: {image_count} images, {text_count} text chunks in top 10")
output_lines.append("="*70)

# Write to file
with open("search_results.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print("Results saved to search_results.txt")
