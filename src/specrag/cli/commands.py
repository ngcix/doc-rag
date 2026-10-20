"""CLI command handlers over application services."""

from __future__ import annotations

import json

from specrag.cli.maintenance import clean_data, initialize
from specrag.ingestion import ingest_documents, rebuild_index
from specrag.ops import (
    add_knowledge,
    add_tag,
    find_nodes,
    get_knowledge,
    get_stats,
    list_documents,
    list_tags,
    lookup_node,
    multi_search,
    remove_tag,
    reset_tags,
    search_documents,
    update_knowledge,
    walk_graph,
)
from specrag.performance import _coerce_positive_int, _is_auto_cpu_value


def _print(payload) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def _serialize_results(results) -> list[dict]:
    return [result.to_dict() if hasattr(result, "to_dict") else vars(result) for result in results]


def _process(args, parser) -> None:
    _process_validation(args, parser)
    report = ingest_documents(**_ingestion_options(args))
    _print(report.to_dict())


def _reindex(args, parser) -> None:
    if not args.yes:
        answer = input("Stop RAG writers and replace the entire FAISS index? [y/N]: ")
        if answer.lower() not in {"y", "yes"}:
            print("Cancelled.")
            return
    _process_validation(args, parser)
    _print(rebuild_index(**_ingestion_options(args)).to_dict())


def _process_validation(args, parser) -> None:
    if not _is_auto_cpu_value(args.workers) and _coerce_positive_int(args.workers) is None:
        parser.error("--workers must be 'auto' or an integer >= 1")
    if args.embedding_batch_size < 1:
        parser.error("--embedding-batch-size must be >= 1")
    if not args.no_images and not args.fullpage:
        parser.error("Image processing requires --fullpage (-fp)")


def _ingestion_options(args) -> dict:
    return {
        "input_dir": args.input,
        "include_charts": not args.no_charts,
        "include_images": not args.no_images,
        "image_format": args.format,
        "max_workers": args.workers,
        "embedding_batch_size": args.embedding_batch_size,
    }


def _search(args) -> None:
    results = search_documents(
        query=args.query,
        top_k=args.top_k,
        save_results=not args.no_save,
        images_only=args.pic,
        use_hybrid=args.hybrid,
    )
    _print(_serialize_results(results))


def _multi_search(args) -> None:
    results = multi_search(
        queries=args.queries,
        top_k=args.top_k,
        save_results=not args.no_save,
        images_only=args.pic,
        use_hybrid=args.hybrid,
    )
    _print(_serialize_results(results))


def dispatch(args, parser) -> None:
    handlers = {
        "process": lambda: _process(args, parser),
        "reindex": lambda: _reindex(args, parser),
        "search": lambda: _search(args),
        "msearch": lambda: _multi_search(args),
        "stats": lambda: _print(get_stats()),
        "init": lambda: _print(initialize()),
        "list": lambda: _print(list_documents()),
        "clean": lambda: clean_data(
            include_models=args.all,
            confirmed=args.yes,
        ),
        "addtag": lambda: _print(add_tag(args.doc_id, args.tag)),
        "listtag": lambda: _print(list_tags(args.doc_id)),
        "removetag": lambda: _print(remove_tag(args.doc_id, args.tag)),
        "resettags": lambda: _print(reset_tags(args.doc_id)),
        "addknowledge": lambda: _print(add_knowledge(args.identifier, args.knowledge)),
        "updateknowledge": lambda: _print(update_knowledge(args.identifier, args.knowledge)),
        "getknowledge": lambda: _print(get_knowledge(args.identifier)),
        "clause": lambda: _print(lookup_node(args.key, args.source, args.text)),
        "refs": lambda: _print(walk_graph(args.key, args.source, "in" if args.incoming else "out", args.depth)),
        "find": lambda: _print(find_nodes(args.text, args.source, args.limit)),
        "server": lambda: _run_server(args.host, args.port),
    }
    if args.command is None:
        parser.print_help()
        return
    handlers[args.command]()


def _run_server(host: str, port: int) -> None:
    from specrag.api_server import main

    main(host=host, port=port)
