"""Retrieval-first answer generation built on top of HybridSearch."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from src.core.answer.answer_sanitizer import sanitize_answer
from src.core.answer.prompt_builder import build_answer_messages
from src.core.answer.types import AskChunk, AskResult
from src.core.query_engine.runtime import QueryRuntime, create_query_runtime
from src.core.settings import Settings, load_settings, resolve_path
from src.core.types import RetrievalResult
from src.libs.llm import LLMFactory

PLACEHOLDER_ANSWER = "当前未生成模型答案，请先检查模型配置或查看检索片段。"
NO_CONTEXT_ANSWER = "根据当前检索结果，信息不足。"


class AskService:
    """Generate answers from retrieved chunks using the configured LLM."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self._llm = None
        self._runtime_cache: dict[str, QueryRuntime] = {}

    def ask(
        self,
        question: str,
        *,
        collection: str = "default",
        top_k: int = 5,
        use_rerank: bool = True,
        save_log: bool = True,
    ) -> AskResult:
        """Run retrieval + answer generation and return a structured result."""

        if not question or not question.strip():
            raise ValueError("Question cannot be empty")

        results = self._retrieve(
            question=question,
            collection=collection,
            top_k=top_k,
            use_rerank=use_rerank,
        )
        ask_chunks = self._to_ask_chunks(results)
        sources = list(
            dict.fromkeys(chunk.source_path for chunk in ask_chunks if chunk.source_path)
        )

        if not ask_chunks:
            ask_result = AskResult(
                question=question,
                collection=collection,
                answer=NO_CONTEXT_ANSWER,
                answer_mode="placeholder",
                answer_status="no_context",
                answer_note="No matching chunks were found, so the LLM was not called.",
                provider=self.settings.llm.provider,
                model=self.settings.llm.model,
                total_hits=0,
                returned_count=0,
                sources=sources,
                chunks=ask_chunks,
            )
        else:
            try:
                answer = self.generate_answer(question, results)
                ask_result = AskResult(
                    question=question,
                    collection=collection,
                    answer=answer,
                    answer_mode="llm",
                    answer_status="generated",
                    answer_note="Answer generated from retrieved chunks.",
                    provider=self.settings.llm.provider,
                    model=self.settings.llm.model,
                    total_hits=len(results),
                    returned_count=len(ask_chunks),
                    sources=sources,
                    chunks=ask_chunks,
                )
            except Exception as exc:
                ask_result = AskResult(
                    question=question,
                    collection=collection,
                    answer=PLACEHOLDER_ANSWER,
                    answer_mode="placeholder",
                    answer_status="error",
                    answer_note=str(exc),
                    provider=self.settings.llm.provider,
                    model=self.settings.llm.model,
                    total_hits=len(results),
                    returned_count=len(ask_chunks),
                    sources=sources,
                    chunks=ask_chunks,
                )

        if save_log:
            ask_result.log_path = self._save_log(ask_result)

        return ask_result

    def generate_answer(
        self,
        question: str,
        chunks: Iterable[Any],
    ) -> str:
        """Generate an answer from already retrieved chunks."""

        retrieval_results = self._normalize_chunks(chunks)
        if not retrieval_results:
            return NO_CONTEXT_ANSWER

        llm = self._get_llm()
        messages = build_answer_messages(question, retrieval_results)
        response = llm.chat(messages)
        answer = sanitize_answer(response.content)
        if not answer:
            raise RuntimeError("LLM returned an empty answer after sanitization.")
        return answer

    def _get_runtime(self, collection: str) -> QueryRuntime:
        runtime = self._runtime_cache.get(collection)
        if runtime is None:
            runtime = create_query_runtime(self.settings, collection=collection)
            self._runtime_cache[collection] = runtime
        return runtime

    def _get_llm(self) -> Any:
        if self._llm is None:
            self._llm = LLMFactory.create(self.settings)
        return self._llm

    def _retrieve(
        self,
        *,
        question: str,
        collection: str,
        top_k: int,
        use_rerank: bool,
    ) -> list[RetrievalResult]:
        runtime = self._get_runtime(collection)
        initial_top_k = (
            top_k * 2
            if use_rerank and runtime.reranker is not None and runtime.reranker.is_enabled
            else top_k
        )

        search_result = runtime.hybrid_search.search(query=question, top_k=initial_top_k)
        results = search_result if isinstance(search_result, list) else search_result.results

        if results and use_rerank and runtime.reranker is not None and runtime.reranker.is_enabled:
            rerank_result = runtime.reranker.rerank(question, results, top_k=top_k)
            results = rerank_result.results

        return results[:top_k]

    def _normalize_chunks(self, chunks: Iterable[Any]) -> list[RetrievalResult]:
        normalized: list[RetrievalResult] = []
        for index, chunk in enumerate(chunks):
            if isinstance(chunk, RetrievalResult):
                normalized.append(chunk)
                continue

            if isinstance(chunk, AskChunk):
                normalized.append(
                    RetrievalResult(
                        chunk_id=chunk.chunk_id,
                        score=chunk.score,
                        text=chunk.text,
                        metadata={**chunk.metadata, "source_path": chunk.source_path},
                    )
                )
                continue

            if isinstance(chunk, dict):
                chunk_id = str(chunk.get("chunk_id") or chunk.get("id") or f"chunk_{index}")
                score = float(chunk.get("score", 0.0))
                text = str(chunk.get("text") or chunk.get("content") or "")
                metadata = chunk.get("metadata", {})
                if not isinstance(metadata, dict):
                    metadata = {}
                source_path = chunk.get("source_path") or metadata.get("source_path") or ""
                normalized.append(
                    RetrievalResult(
                        chunk_id=chunk_id,
                        score=score,
                        text=text,
                        metadata={**metadata, "source_path": source_path},
                    )
                )
                continue

            if hasattr(chunk, "text") and hasattr(chunk, "chunk_id"):
                normalized.append(
                    RetrievalResult(
                        chunk_id=str(getattr(chunk, "chunk_id")),
                        score=float(getattr(chunk, "score", 0.0)),
                        text=str(getattr(chunk, "text", "")),
                        metadata=getattr(chunk, "metadata", {}) or {},
                    )
                )
                continue

            raise ValueError(
                f"Unsupported chunk type for answer generation: {type(chunk).__name__}"
            )

        return normalized

    def _to_ask_chunks(self, results: list[RetrievalResult]) -> list[AskChunk]:
        return [
            AskChunk(
                rank=index + 1,
                chunk_id=result.chunk_id,
                score=result.score,
                text=result.text,
                source_path=str(result.metadata.get("source_path", "")),
                metadata=result.metadata.copy(),
            )
            for index, result in enumerate(results)
        ]

    def _save_log(self, result: AskResult) -> str:
        log_dir = resolve_path("logs/ask_runs")
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_question = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "_", result.question).strip("_")
        safe_question = safe_question[:48] or "ask"
        log_path = log_dir / f"{timestamp}_{safe_question}.json"

        payload = {
            "timestamp": timestamp,
            **result.to_dict(),
        }
        log_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(log_path)
