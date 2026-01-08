"""Test the figure caption detection on page 80."""
import fitz
import re

doc = fitz.open('data/documents/HID_SPEC_V10.pdf')
pages_to_check = [80, 41, 42, 77, 1, 2]  # 80 should now pass due to Figure caption

min_drawing_size = 20

for page_num in pages_to_check:
    page = doc[page_num - 1]
    r = page.rect
    page_area = r.width * r.height
    max_drawing_area = page_area * 0.50
    
    has_images = False
    reason = ""
    
    # Check drawings with COMBINED area logic
    drawings = page.get_drawings()
    total_content_area = 0
    
    for d in drawings:
        rect = d["rect"]
        drawing_area = rect.width * rect.height
        
        fill = d.get("fill")
        if fill and len(d.get("items", [])) == 1:
            item_type = d.get("items", [[""]])[0][0]
            if item_type == "re":
                brightness = sum(fill) / len(fill) if fill else 0
                if brightness > 0.85:
                    continue
        
        if rect.width < min_drawing_size or rect.height < min_drawing_size:
            continue
        
        if drawing_area > max_drawing_area:
            continue
        
        total_content_area += drawing_area
    
    if total_content_area >= page_area * 0.02:
        has_images = True
        reason = f"combined area {total_content_area/page_area*100:.1f}%"
    
    # Secondary check: Figure/Table captions
    if not has_images:
        text = page.get_text().lower()
        figure_patterns = [
            r'figure\s+\d+',
            r'fig\.\s*\d+',
            r'table\s+\d+',
        ]
        for pattern in figure_patterns:
            match = re.search(pattern, text)
            if match:
                has_images = True
                reason = f"figure caption: '{match.group()}'"
                break
    
    if not has_images:
        reason = f"combined area {total_content_area/page_area*100:.1f}%, no figure caption"
    
    status = "CAPTURED" if has_images else "SKIPPED"
    print(f"Page {page_num}: {status} ({reason})")

doc.close()
