# CHANGES

## v0.3.0

- Add portable path rebasing for copied databases and documents directories.
- Resolve image paths against the current `database_dir` so `search -pic` results can be analyzed after moving data.
- Normalize CLI logs for legacy Windows console encodings.
- Add full-page-all processing mode and pdf_oxide extraction support.
- Improve packaged CLI/build support.

## v0.2.0

- Dependencies should be install with `pip install -e .` instead of `pip install -r requirements.txt`
- The main script is rename `rag` -> `specrag`
- All documents is now use `specrag` instead of `python -m src.main`
- config folder is moved into src
