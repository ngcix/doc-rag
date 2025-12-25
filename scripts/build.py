import os
import shutil
import sys
import PyInstaller.__main__
from setuptools import setup
from Cython.Build import cythonize
from PyInstaller.utils.hooks import collect_all
from pathlib import Path

PROJECT_NAME = "simpleRAG"
DIST_PATH = Path(f".\\dist\\{PROJECT_NAME}")
INTERNAL_PATH = DIST_PATH / "_internal"

def clean_old_builds():
    """Xóa các thư mục build cũ."""
    folders = [f".\\dist\\{PROJECT_NAME}", ".\\build", ".\\src_temp"]
    for folder in folders:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"Removed: {folder}")

def compile_cython():
    """Biên dịch các module logic sang file .pyd (C-Extension)."""
    print("--- Starting Cython Compilation ---")
    
    # Chỉ định các folder chứa logic quan trọng cần bảo mật
    # Không biên dịch main.py vì PyInstaller cần nó làm entry point
    include_folders = [
        "src/chunking",
        "src/image_extraction",
        "src/search",
        "src/vectorization"
    ]
    
    files_to_compile = []
    for folder in include_folders:
        for file in os.listdir(folder):
            if file.endswith(".py") and file != "__init__.py":
                files_to_compile.append(os.path.join(folder, file))

    if not files_to_compile:
        print("No files found to compile.")
        return

    # Thực hiện biên dịch
    setup(
        ext_modules=cythonize(
            files_to_compile,
            compiler_directives={'language_level': "3"},
            quiet=True
        ),
        script_args=["build_ext", "--inplace"]
    )
    
    # Dọn dẹp các file .c sinh ra sau khi biên dịch
    for folder in include_folders:
        for file in os.listdir(folder):
            if file.endswith(".c"):
                os.remove(os.path.join(folder, file))
    print("--- Cython Compilation Finished ---")

def run_pyinstaller():
    """Đóng gói ứng dụng."""
    print("--- Starting PyInstaller Build ---")
    
    # 1. Thu thập TẤT CẢ mọi thứ của docling
    datas, binaries, hiddenimports = collect_all('docling')
    d_core_datas, d_core_binaries, d_core_hidden = collect_all('docling_core')
    d_models_datas, d_models_binaries, d_models_hidden = collect_all('docling_ibm_models')
    
    datas += d_core_datas + d_models_datas
    binaries += d_core_binaries + d_models_binaries
    hiddenimports += d_core_hidden + d_models_hidden + [
        'docling_parse', 
        'docling_ibm_models',
        'langchain.text_splitter',
        'langchain_core.documents', 
        'langchain.schema',
        'langchain.docstore',
        'langchain.docstore.document'
    ]

    # 2. Fix lỗi pdf_resources_v2 của docling-parse
    import docling_parse
    dp_root = Path(docling_parse.__file__).parent
    res_src = dp_root / "pdf_resources_v2"
    
    dp_path = Path(docling_parse.__file__).parent / "pdf_resources_v2"
    datas.append((str(dp_path), "docling_parse/pdf_resources_v2"))
    datas.append((str(res_src), "docling_parse/pdf_resources_v2"))

    # 3. Lệnh PyInstaller chính thức
    PyInstaller.__main__.run([
        'src/main.py',
        '--onedir',
        f'--name={PROJECT_NAME}',
        '--clean',
        # Copy Metadata cho tất cả các gói vệ tinh
        *[f'--copy-metadata={pkg}' for pkg in ['docling', 'docling_core', 'docling-ibm-models', 'docling-parse']], 
        # Thêm các file .pyd đã biên dịch từ Cython (tự động nhận diện)
        *[f'--hiddenimport={h}' for h in hiddenimports],
        *[f'--add-data={d[0]};{d[1]}' for d in datas],
        *[f'--add-binary={b[0]};{b[1]}' for b in binaries],
    ])

def finalize_dist():
    """Copy model offline và tạo cấu trúc folder data."""
    print("--- Finalizing Distribution Folder ---")
    
    # Copy folder models vào _internal để app dùng Offline
    src_models = Path(".\\models")
    dest_models = INTERNAL_PATH / "models"
    if src_models.exists():
        shutil.copytree(src_models, dest_models, dirs_exist_ok=True)
        print(f"Copied models to: {dest_models}")

    # Tạo các folder dữ liệu trống bên cạnh file .exe
    data_structure = ["data/documents", "data/embeddings", "data/images"]
    for folder in data_structure:
        path = DIST_PATH / folder
        path.mkdir(parents=True, exist_ok=True)
        print(f"Created data directory: {path}")

if __name__ == "__main__":
    try:
        clean_old_builds()
        compile_cython()
        run_pyinstaller()
        finalize_dist()
        print(f"\nSUCCESS! Build output located at: {DIST_PATH}")
    except Exception as e:
        print(f"\nBUILD FAILED: {str(e)}")
        sys.exit(1)