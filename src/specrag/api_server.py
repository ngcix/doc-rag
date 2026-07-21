"""SpecRAG HTTP server entry point (FastAPI + uvicorn)."""

from __future__ import annotations


def create_app():
    """Create the FastAPI application (used by uvicorn and tests)."""
    from specrag.api.app import create_app as _create

    return _create()


def main(host: str = "0.0.0.0", port: int = 8080) -> None:
    """Run the API with uvicorn."""
    import uvicorn

    print("SpecRAG API starting (FastAPI)")
    print(f"  Local access: http://localhost:{port}")
    print(f"  OpenAPI docs: http://localhost:{port}/docs")
    uvicorn.run(
        "specrag.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
