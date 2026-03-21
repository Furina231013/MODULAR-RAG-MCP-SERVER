#!/usr/bin/env python
"""Ask script for retrieval-first question answering.

Usage:
    python scripts/ask.py --question "当前 demo 文档主要讲了什么？" --collection demo
    python scripts/ask.py --question "FastAPI 的职责边界是什么？" --collection demo --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_REPO_ROOT))

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from src.core.answer import AskService  # noqa: E402
from src.core.settings import load_settings  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an answer from retrieved knowledge-hub chunks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--question", "-q", required=True, help="Question to answer.")
    parser.add_argument("--collection", "-c", default="default", help="Collection name.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to retrieve.")
    parser.add_argument(
        "--config",
        default=str(_REPO_ROOT / "config" / "settings.yaml"),
        help="Path to configuration file.",
    )
    parser.add_argument("--no-rerank", action="store_true", help="Disable reranking.")
    parser.add_argument("--json", action="store_true", help="Print full result as JSON.")
    return parser.parse_args()


def _print_human(result: dict) -> None:
    print("[*] Modular RAG Ask Script")
    print("=" * 60)
    print(f"Collection: {result['collection']}")
    print(f"Answer status: {result['answer_status']} ({result['answer_mode']})")
    if result.get("answer_note"):
        print(f"Note: {result['answer_note']}")
    if result.get("model"):
        print(f"Model: {result['model']}")
    print(f"Log: {result.get('log_path', '-')}")
    print("\nANSWER")
    print("-" * 60)
    print(result["answer"])
    print("\nCHUNKS")
    print("-" * 60)
    for chunk in result.get("chunks", []):
        snippet = " ".join((chunk.get("text") or "").split())[:180]
        print(
            f"#{chunk['rank']:02d} score={chunk['score']:.4f} id={chunk['chunk_id']} "
            f"source={chunk.get('source_path', '')}"
        )
        print(f"    {snippet}...")


def main() -> int:
    args = parse_args()

    try:
        settings = load_settings(args.config)
    except Exception as exc:
        print(f"[FAIL] Failed to load configuration: {exc}")
        return 2

    try:
        service = AskService(settings=settings)
        result = service.ask(
            args.question,
            collection=args.collection,
            top_k=args.top_k,
            use_rerank=not args.no_rerank,
        )
    except Exception as exc:
        print(f"[FAIL] Ask flow failed: {exc}")
        return 1

    payload = result.to_dict()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_human(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
