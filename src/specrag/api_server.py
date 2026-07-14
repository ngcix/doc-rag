"""Simple aiohttp HTTP server exposing RAG search functionalities.

Endpoints:
- POST /search          -> search_documents
- POST /multi_search    -> multi_search
- POST /add_tag         -> add_tag
"""

import json
import multidict
if not hasattr(multidict, 'istr'):
    multidict.istr = str
from aiohttp import web

# Import core functions from the project
from specrag.main import search_documents, multi_search, add_tag
from pathlib import Path
from scripts.analyze_extracted_images import process_image


def _result_to_dict(r):
    """Convert a SearchResult (or similar) object to a plain dict for JSON response."""
    if hasattr(r, "__dict__"):
        return r.__dict__
    return {
        "rank": getattr(r, "rank", None),
        "chunk_id": getattr(r, "chunk_id", None),
        "similarity": getattr(r, "similarity", None),
        "metadata": getattr(r, "metadata", {}),
        "document": getattr(r, "document", ""),
    }

async def handle_search(request):
    try:
        data = await request.json()
        query = data.get("query")
        top_k = data.get("top_k", 5)
        images_only = data.get("images_only", False)
        use_hybrid = data.get("use_hybrid", False)
        if not query:
            return web.json_response({"error": "Missing \"query\" field"}, status=400)
        results = search_documents(
            query=query,
            top_k=top_k,
            save_results=False,
            images_only=images_only,
            use_hybrid=use_hybrid,
        )
        # Analyze image results and embed analysis into metadata
        for r in results:
            meta = getattr(r, "metadata", {})
            if meta.get("content_type") == "image":
                image_path = meta.get("image_path")
                if image_path:
                    success, analysis = process_image(Path(image_path), query=query)
                    if success and analysis:
                        meta["image_content"] = analysis
        return web.json_response([_result_to_dict(r) for r in results])
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_multi_search(request):
    try:
        data = await request.json()
        queries = data.get("queries")
        top_k = data.get("top_k", 5)
        images_only = data.get("images_only", False)
        use_hybrid = data.get("use_hybrid", False)
        if not queries or not isinstance(queries, list):
            return web.json_response({"error": "Missing or invalid \"queries\" field (list required)"}, status=400)
        results = multi_search(
            queries=queries,
            top_k=top_k,
            images_only=images_only,
            use_hybrid=use_hybrid,
            save_results=False,
        )
        return web.json_response([_result_to_dict(r) for r in results])
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def handle_add_tag(request):
    try:
        data = await request.json()
        doc_id = data.get("doc_id")
        tag = data.get("tag")
        if not doc_id or not tag:
            return web.json_response({"error": "Missing \"doc_id\" or \"tag\" field"}, status=400)
        add_tag(doc_id, tag)
        return web.json_response({"status": "success", "message": f"Tag '{tag}' added to document '{doc_id}'."})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

def create_app() -> web.Application:
    """Create and configure the aiohttp application."""
    app = web.Application()
    app.router.add_post('/search', handle_search)
    app.router.add_post('/multi_search', handle_multi_search)
    app.router.add_post('/add_tag', handle_add_tag)
    return app

def main(host: str = '0.0.0.0', port: int = 8080) -> None:
    """Entry point to run the aiohttp server."""
    print(f"✅ Server started successfully!")
    print(f"   Local access: http://localhost:{port}")
    app = create_app()

    web.run_app(app, host=host, port=port)
    

if __name__ == '__main__':
    main()
