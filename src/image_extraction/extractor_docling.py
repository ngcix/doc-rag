import os
import pypdfium2 as pdfium

from PIL import Image, ImageDraw, ImageFont

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption

# Cấu hình pipeline
pipeline_options = PdfPipelineOptions()
pipeline_options.images_scale = 2.0
pipeline_options.generate_picture_images = True
pipeline_options.generate_table_images = True
pipeline_options.generate_page_images = True
pipeline_options.do_ocr = False
pipeline_options.do_table_structure = True

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)

# Thư mục output
file_path = os.path.realpath(__file__)
file_dir = os.path.dirname(os.path.dirname(os.path.dirname(file_path)))

output_dir = os.path.join(file_dir, "data", "documents", "prediction")
os.makedirs(output_dir, exist_ok=True)

pic_dir = os.path.join(file_dir, "data", "documents", "charts")
os.makedirs(output_dir, exist_ok=True)

def crop_and_save_pictures_from_page(page_image: Image.Image, elements_on_page, page_num: int):
    """Cắt và lưu picture"""
    picture_counter = 0
    page_h_original = page_image.height / 2.0

    for elem, _ in elements_on_page:
        if elem.label != "picture":
            continue
        if not hasattr(elem, 'prov') or not elem.prov:
            continue

        for prov in elem.prov:
            if prov.page_no != page_num or not prov.bbox:
                continue

            b = prov.bbox
            left = int(b.l * 2)
            top = int((page_h_original - b.t) * 2)
            right = int(b.r * 2)
            bottom = int((page_h_original - b.b) * 2)

            cropped = page_image.crop((left, top, right, bottom))
            picture_counter += 1
            picture_path = os.path.join(pic_dir, f"page_{page_num:03d}_picture_{picture_counter:03d}.png")
            cropped.save(picture_path)
            print(f"   ➜ Saved picture: page_{page_num:03d}_picture_{picture_counter:03d}.png")

    return picture_counter


def draw_and_save_pages_with_elements(file_path, doc, save_pages_with_bbox: bool = True):
    pdf = pdfium.PdfDocument(file_path)

    # Font cho label (chỉ dùng khi vẽ bbox)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", 18)
        except:
            font = ImageFont.load_default()

    # Thu thập trang có picture
    pages_with_elements = set()
    all_elements = list(doc.iterate_items())

    for elem, _ in all_elements:
        if elem.label in ["picture"] and hasattr(elem, 'prov') and elem.prov:
            for prov in elem.prov:
                if prov.page_no is not None:
                    pages_with_elements.add(prov.page_no)

    if not pages_with_elements:
        print("⚠️ Không tìm thấy trang nào có picture hoặc table.")
        pdf.close()
        return

    print(f"📄 Đang xử lý {len(pages_with_elements)} trang: {sorted(pages_with_elements)}")

    total_pictures_cropped = 0

    for page_idx in range(len(pdf)):
        page_num = page_idx + 1
        if page_num not in pages_with_elements:
            continue

        # Render trang
        page_image = pdf[page_idx].render(scale=2).to_pil()
        original_image_for_crop = page_image.copy()  # Dùng bản gốc để cắt picture sạch

        # Lọc element chỉ thuộc trang này
        elements_on_this_page = [
            (elem, depth) for elem, depth in all_elements
            if hasattr(elem, 'prov') and elem.prov and
            any(p.page_no == page_num for p in elem.prov if p.page_no is not None)
        ]

        # === Vẽ bbox chỉ khi cần (và chỉ cho picture/table) ===
        if save_pages_with_bbox:
            draw = ImageDraw.Draw(page_image)
            page_h = page_image.height / 2.0

            for elem, _ in elements_on_this_page:
                if not hasattr(elem, 'prov') or not elem.prov:
                    continue

                for prov in elem.prov:
                    if prov.page_no != page_num or not prov.bbox:
                        continue

                    b = prov.bbox
                    coords = [
                        b.l * 2,
                        (page_h - b.t) * 2,
                        b.r * 2,
                        (page_h - b.b) * 2
                    ]

                    # Vẽ viền đỏ
                    draw.rectangle(coords, outline="red", width=4)

                    # Vẽ label
                    label_text = elem.label.upper()
                    text_x = coords[0]
                    text_y = coords[1] - 30

                    try:
                        bbox = draw.textbbox((text_x, text_y), label_text, font=font)
                        bg_coords = [text_x - 4, text_y - 4, bbox[2] + 4, bbox[3] + 4]
                        draw.rectangle(bg_coords, fill="white", outline="red")
                        draw.text((text_x, text_y), label_text, fill="red", font=font)
                    except:
                        draw.text((text_x, text_y), label_text, fill="red")

            # Lưu trang đã annotate
            annotated_path = os.path.join(output_dir, f"page_{page_num:03d}_annotated.png")
            page_image.save(annotated_path)
            print(f"Saved annotated page: page_{page_num:03d}_annotated.png")

        # === Cắt picture sạch từ bản gốc (không bị ảnh hưởng bởi viền đỏ) ===
        cropped_count = crop_and_save_pictures_from_page(original_image_for_crop, elements_on_this_page, page_num)
        total_pictures_cropped += cropped_count

    pdf.close()
    print(f"🎉 Hoàn thành: Đã cắt và lưu {total_pictures_cropped} picture.")


def convert(file_path: str, save_pages_with_bbox: bool = False):
    file_path = os.path.join(os.getcwd(), file_path)

    result = converter.convert(file_path)

    processed_labels = [item.label for item, _ in result.document.iterate_items()]
    print(f"📊 Tìm thấy {len(processed_labels)} elements")

    draw_and_save_pages_with_elements(file_path, result.document, save_pages_with_bbox=save_pages_with_bbox)

if __name__ == "__main__":
    pdf_file_path = "data/documents/HID_v1.1.1.pdf"
    pdf_file_path_test = "data/documents/test.pdf"
    convert(pdf_file_path, save_pages_with_bbox=True)  # Hoặc False để chỉ cắt picture
    