# Build

The project uses a standard Python wheel for RAG and a separate TEI/ONNX image
for embeddings. See [the build guide](../scripts/build.md).

PyInstaller and Cython builds were removed because they bundled the model
runtime into the RAG process and produced large, fragile artifacts.
