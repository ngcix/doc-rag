"""Configure plain, robust CLI output."""
import sys


def configure_cli_output() -> None:
    """Avoid UnicodeEncodeError on legacy Windows consoles."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="replace")
            except Exception:
                pass
