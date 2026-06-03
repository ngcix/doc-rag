"""Check if page 29 is indexed in the database."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.vectorization import get_vector_store

vs = get_vector_store()
results = vs._collection.get()
metas = results['metadatas']
docs = results['documents']

# Find page 29 items
page29_items = []
for i, m in enumerate(metas):
    page_num = m.get('page_number')
    chunk_id = m.get('chunk_id', '')
    
    if page_num == 29 or '_p29' in chunk_id or 'p29' in chunk_id:
        page29_items.append({
            'id': chunk_id,
            'type': m.get('content_type', 'N/A'),
            'page': page_num,
            'content_preview': docs[i][:200] if i < len(docs) else ''
        })

print(f"=== Found {len(page29_items)} items from page 29 ===\n")

for item in page29_items[:15]:
    print(f"ID: {item['id']}")
    print(f"Type: {item['type']}")
    print(f"Page: {item['page']}")
    print(f"Content: {item['content_preview']}")
    print("-" * 60)

# Search for "Table 4.22" in content
print("\n=== Searching for 'Table 4.22' in documents ===\n")
table_found = []
for i, doc in enumerate(docs):
    if 'table 4.22' in doc.lower():
        table_found.append({
            'id': metas[i].get('chunk_id', 'N/A'),
            'page': metas[i].get('page_number', 'N/A'),
            'type': metas[i].get('content_type', 'N/A'),
            'content': doc[:300]
        })

if table_found:
    print(f"Found {len(table_found)} documents containing 'Table 4.22':\n")
    for t in table_found:
        print(f"ID: {t['id']}")
        print(f"Page: {t['page']}")
        print(f"Type: {t['type']}")
        print(f"Content: {t['content']}")
        print("-" * 60)
else:
    print("Could not find 'Table 4.22' in database!")
    print("\nThis means:")
    print("1. Page 29 has not been extracted")
    print("2. Or this table is an image and was not extracted with fullpage mode")
    print("3. Or text extraction could not read table text")
