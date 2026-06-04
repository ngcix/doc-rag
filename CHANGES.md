# CHANGES

## v0.3.1

- Auto-tune processing workers and embedding threads from available CPU resources.
- Add performance config for target CPU utilization, reserved threads, worker count, and embedding batch size.
- Add CLI overrides for processing workers, embedding threads, and embedding batch size.
- Simplify image extraction to a single PyMuPDF full-page backend.
- Remove Docling extraction mode, PP-Structure/cropped-image code paths, and related configuration.
- Remove pdf-oxide backend and dependency so PDF processing uses PyMuPDF consistently.
- Remove the `--fullpage-all` / `-fpa` process option.

## v0.3.0

- Add portable path rebasing for copied databases and documents directories.
- Resolve image paths against the current `database_dir` so `search -pic` results can be analyzed after moving data.
- Normalize CLI logs for legacy Windows console encodings.
- Add full-page-all processing mode.
- Improve packaged CLI/build support.

## v0.2.0

- Dependencies should be install with `pip install -e .` instead of `pip install -r requirements.txt`
- The main script is rename `rag` -> `specrag`
- All documents is now use `specrag` instead of `python -m src.main`
- config folder is moved into src
