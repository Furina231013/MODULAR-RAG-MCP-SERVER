"""Shared runtime helpers for retrieval-oriented entry points.

This module centralizes the construction of HybridSearch and optional reranker
instances so CLI tools, MCP tools, dashboard pages, and future ask flows can
reuse the same setup logic.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.query_engine.dense_retriever import create_dense_retriever
from src.core.query_engine.hybrid_search import HybridSearch, create_hybrid_search
from src.core.query_engine.query_processor import QueryProcessor
from src.core.query_engine.reranker import CoreReranker, create_core_reranker
from src.core.query_engine.sparse_retriever import create_sparse_retriever
from src.core.settings import Settings, resolve_path
from src.ingestion.storage.bm25_indexer import BM25Indexer
from src.libs.embedding.embedding_factory import EmbeddingFactory
from src.libs.vector_store.vector_store_factory import VectorStoreFactory


@dataclass
class QueryRuntime:
    """Fully initialized retrieval runtime for a single collection."""

    collection: str
    hybrid_search: HybridSearch
    reranker: CoreReranker | None = None


def create_query_runtime(
    settings: Settings,
    collection: str = "default",
    *,
    enable_reranker: bool = True,
) -> QueryRuntime:
    """Build HybridSearch and optional reranker for *collection*."""

    vector_store = VectorStoreFactory.create(
        settings,
        collection_name=collection,
    )

    embedding_client = EmbeddingFactory.create(settings)
    dense_retriever = create_dense_retriever(
        settings=settings,
        embedding_client=embedding_client,
        vector_store=vector_store,
    )

    bm25_indexer = BM25Indexer(index_dir=str(resolve_path(f"data/db/bm25/{collection}")))
    sparse_retriever = create_sparse_retriever(
        settings=settings,
        bm25_indexer=bm25_indexer,
        vector_store=vector_store,
    )
    sparse_retriever.default_collection = collection

    query_processor = QueryProcessor()
    hybrid_search = create_hybrid_search(
        settings=settings,
        query_processor=query_processor,
        dense_retriever=dense_retriever,
        sparse_retriever=sparse_retriever,
    )

    reranker = create_core_reranker(settings=settings) if enable_reranker else None
    if reranker is not None and not reranker.is_enabled:
        reranker = None

    return QueryRuntime(
        collection=collection,
        hybrid_search=hybrid_search,
        reranker=reranker,
    )
