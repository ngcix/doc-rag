"""This is buider with pyinstaller"""

import shutil
import os
import PyInstaller.__main__
from PyInstaller.utils.hooks import collect_all

PROJECT_NAME = "simpleRAG"

try:
    shutil.rmtree(f".\\dist\\{PROJECT_NAME}")
except:  # noqa: E722
    pass

# remove old release
try:
    os.remove(".\\dist\\release.zip")
except:  # noqa: E722
    pass

datas, binaries, hiddenimports = collect_all('docling')

hiddenimports.append('docling_ibm_models')
hiddenimports.append('docling_parse')

# make the program
PyInstaller.__main__.run([
    'src/main.py',
    '--onedir',
    '--name=simpleRAG',

    *[f'--copy-metadata={pkg}' for pkg in ['docling', 'docling_core', 'docling-ibm-models', 'docling-parse', ]], 
    *([f'--hiddenimport={h}' for h in hiddenimports]),
    *([f'--add-data={d[0]};{d[1]}' for d in datas]),
    *([f'--add-binary={b[0]};{b[1]}' for b in binaries]),
    '--clean'
])

# TODO: copy offline models to dist
 