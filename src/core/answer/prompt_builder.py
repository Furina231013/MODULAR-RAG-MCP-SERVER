"""Prompt construction for ask-style answer generation."""

from __future__ import annotations

from collections.abc import Iterable

from src.core.types import RetrievalResult
from src.libs.llm import Message

MAX_CONTEXT_CHUNKS = 6
MAX_CHUNK_CHARS = 1400

SYSTEM_PROMPT = """你是一个严谨的 RAG 问答助手。

你必须只根据给定检索上下文回答，不要补充上下文里没有的新事实，不要引用外部知识。
如果上下文不足以支持完整结论，要明确说明“根据当前检索结果，信息不足”或指出未覆盖的边界。
不要输出思维链、分析过程、<think> 标签或额外寒暄。

输出格式必须严格为三行：
结论：<直接回答问题>
依据：<引用上下文中的关键事实、条件或数字>
边界：<说明上下文是否充分，或当前材料未覆盖的范围>
"""


def _truncate(text: str, limit: int) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "..."


def _chunk_block(result: RetrievalResult, rank: int) -> str:
    source_path = result.metadata.get("source_path", "")
    chunk_index = result.metadata.get("chunk_index", "")
    header = [
        f"Chunk rank: {rank}",
        f"Chunk ID: {result.chunk_id}",
        f"Score: {result.score:.4f}",
    ]
    if source_path:
        header.append(f"Source: {source_path}")
    if chunk_index != "":
        header.append(f"Chunk Index: {chunk_index}")
    header.append("Content:")
    header.append(_truncate(result.text or "", MAX_CHUNK_CHARS))
    return "\n".join(header)


def build_answer_messages(
    question: str,
    chunks: Iterable[RetrievalResult],
) -> list[Message]:
    """Build system/user messages for answer generation."""

    selected_chunks = list(chunks)[:MAX_CONTEXT_CHUNKS]
    if selected_chunks:
        context_block = "\n\n---\n\n".join(
            _chunk_block(result, rank=index + 1) for index, result in enumerate(selected_chunks)
        )
    else:
        context_block = "No retrieved context."

    user_prompt = (
        f"问题：\n{question}\n\n"
        f"检索上下文：\n{context_block}\n\n"
        "请基于以上上下文，按照指定格式输出最终答案。"
    )

    return [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content=user_prompt),
    ]
