"""Search operations (semantic / hybrid / multi-query RRF)."""

from __future__ import annotations

from specrag.ops._helpers import (
    filter_image_results,
    get_embedding_provider,
    get_hybrid_search_engine_cls,
    get_search_engine,
    get_vector_store,
)


def search_documents(
    query: str,
    top_k: int = 5,
    save_results: bool = True,
    images_only: bool = False,
    use_hybrid: bool = False,
):
    """
    Search vectorized documents.

    Returns list[SearchResult]. Optionally writes process/output when save_results=True.
    """
    fetch_k = 1000 if images_only else top_k
    search_threshold = 0.5 if images_only else None

    if use_hybrid:
        embedding_provider = get_embedding_provider()
        vector_store = get_vector_store()
        vector_store.validate_model(embedding_provider.model_info())
        hybrid_engine = get_hybrid_search_engine_cls()(
            vector_store,
            embedding_provider,
        )
        raw_results = hybrid_engine.search(
            query,
            top_k=fetch_k,
            vector_weight=0.4,
            bm25_weight=0.6,
            threshold=search_threshold,
        )
        from specrag.search import SearchResult

        results = [
            SearchResult(
                rank=r["rank"],
                document=r["document"],
                similarity=r.get("rrf_score", r.get("similarity", 0)),
                metadata=r["metadata"],
                chunk_id=r["id"],
            )
            for r in raw_results
        ]
    else:
        engine = get_search_engine()
        results = engine.search(query, top_k=fetch_k, threshold=search_threshold)

    if images_only:
        results = filter_image_results(results)[:top_k]
        for i, r in enumerate(results):
            r.rank = i + 1

    if save_results:
        engine = get_search_engine()
        save_params = {
            "top_k": top_k,
            "images_only": images_only,
            "use_hybrid": use_hybrid,
            "fetch_k": fetch_k,
        }
        engine.save_search_results(query, results, extra_params=save_params)

    return results


def multi_search(
    queries: list[str],
    top_k: int = 5,
    images_only: bool = False,
    use_hybrid: bool = False,
    save_results: bool = True,
):
    """
    Multi-query search with RRF merge.

    Returns list[SearchResult].
    """
    all_results = {}
    rrf_k = 60
    embedding_provider = get_embedding_provider()
    query_embeddings = embedding_provider.embed(queries)

    for query, query_embedding in zip(queries, query_embeddings):
        fetch_k = top_k * 3
        search_threshold = 0.4 if images_only else 0.5

        if use_hybrid:
            vector_store = get_vector_store()
            vector_store.validate_model(embedding_provider.model_info())
            hybrid_engine = get_hybrid_search_engine_cls()(
                vector_store,
                embedding_provider,
            )
            raw_results = hybrid_engine.search(
                query,
                top_k=fetch_k,
                vector_weight=0.4,
                bm25_weight=0.6,
                threshold=search_threshold,
                query_embedding=query_embedding,
            )
            from specrag.search import SearchResult

            results = [
                SearchResult(
                    rank=r["rank"],
                    document=r["document"],
                    similarity=r.get("rrf_score", r.get("similarity", 0)),
                    metadata=r["metadata"],
                    chunk_id=r["id"],
                )
                for r in raw_results
            ]
        else:
            engine = get_search_engine()
            results = engine.search(
                query,
                top_k=fetch_k,
                threshold=search_threshold,
                query_embedding=query_embedding,
            )

        if images_only:
            results = filter_image_results(results)

        for rank, result in enumerate(results, 1):
            chunk_id = result.chunk_id
            rrf_score = 1.0 / (rrf_k + rank)

            if chunk_id in all_results:
                prev_score, prev_result, hit_count = all_results[chunk_id]
                new_score = prev_score + rrf_score
                best_result = prev_result if prev_result.similarity > result.similarity else result
                all_results[chunk_id] = (new_score, best_result, hit_count + 1)
            else:
                all_results[chunk_id] = (rrf_score, result, 1)

    sorted_results = sorted(all_results.values(), key=lambda x: x[0], reverse=True)

    final_results = []
    hit_counts = []
    for rank, (rrf_score, result, hit_count) in enumerate(sorted_results[:top_k], 1):
        result.rank = rank
        result.similarity = rrf_score
        final_results.append(result)
        hit_counts.append(hit_count)

    if save_results and final_results:
        engine = get_search_engine()
        composite_query = " | ".join(queries)
        save_params = {
            "top_k": top_k,
            "images_only": images_only,
            "use_hybrid": use_hybrid,
            "mode": "multi_search",
            "queries": queries,
            "rerank_method": "RRF",
        }
        engine.save_search_results(composite_query, final_results, extra_params=save_params)

    return final_results
