"""Data structures for ask-style retrieval + generation flows."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class AskChunk:
    """Chunk returned to the user alongside an answer."""

    rank: int
    chunk_id: str
    score: float
    text: str
    source_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AskResult:
    """Structured result for ask-style interactions."""

    question: str
    collection: str
    answer: str
    answer_mode: str
    answer_status: str
    answer_note: str | None = None
    provider: str = "placeholder"
    model: str | None = None
    total_hits: int = 0
    returned_count: int = 0
    sources: list[str] = field(default_factory=list)
    chunks: list[AskChunk] = field(default_factory=list)
    log_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "collection": self.collection,
            "answer": self.answer,
            "answer_mode": self.answer_mode,
            "answer_status": self.answer_status,
            "answer_note": self.answer_note,
            "provider": self.provider,
            "model": self.model,
            "total_hits": self.total_hits,
            "returned_count": self.returned_count,
            "sources": self.sources,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "log_path": self.log_path,
        }
