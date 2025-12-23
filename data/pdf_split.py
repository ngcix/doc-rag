import fitz  # PyMuPDF

def save_specific_page(input_pdf, output_pdf, page_number):
    # Mở file PDF gốc
    doc = fitz.open(input_pdf)
    
    # Kiểm tra xem trang có tồn tại không (index bắt đầu từ 0)
    # Trang 23 sẽ là index 22
    page_index = page_number - 1
    
    if page_index < len(doc):
        # Tạo một file PDF mới
        new_doc = fitz.open()
        # Chép trang cụ thể vào file mới
        new_doc.insert_pdf(doc, from_page=22, to_page=24)
        
        # Lưu file
        new_doc.save(output_pdf)
        new_doc.close()
        print(f"Đã lưu trang {page_number} vào file {output_pdf}")
    else:
        print(f"Lỗi: File chỉ có {len(doc)} trang.")
    
    doc.close()

if __name__ == "__main__":
    save_specific_page("HID_v1.1.1.pdf", "page_23_24.pdf", 23)