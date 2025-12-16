"""Script to view all images and their context in the database."""
import pickle

# Load metadata from FAISS pickle file
with open('data/faiss_index/documents_metadata.pkl', 'rb') as f:
    data = pickle.load(f)

metadata_dict = data.get('metadata', {})
documents_dict = data.get('documents', {})

print('='*70)
print('DANH SACH ANH VA CONTEXT TRONG DATABASE')
print('='*70)

count = 0
for chunk_id, meta in metadata_dict.items():
    if meta.get('type') == 'extracted_image':
        count += 1
        
        # Get image filename
        img_path = meta.get('image_path', '')
        img_name = img_path.replace('\\', '/').split('/')[-1] if img_path else 'unknown'
        
        # Get the document content (vectorized text)
        content = documents_dict.get(chunk_id, '')
        
        print(f"\n[{count}] {img_name}")
        print(f"    ID: {chunk_id}")
        print(f"    Page: {meta.get('page_number', '?')}")
        print(f"    Type: {meta.get('region_type', '?')}")
        print(f"    ---CONTEXT TEXT (dung de search)---")
        
        # Show content that was vectorized
        for line in content.split('\n'):
            if line.strip():
                print(f"    | {line.strip()}")

print('\n' + '='*70)
print(f'TONG CONG: {count} anh trong database')
print('='*70)
