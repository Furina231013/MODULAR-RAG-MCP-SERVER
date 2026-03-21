"""Utilities for cleaning local-model answers into a stable format."""

from __future__ import annotations

import re

SECTION_LABELS = ("结论", "依据", "边界")


def _strip_reasoning_blocks(answer: str) -> str:
    cleaned = answer.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"(?is)<think>.*?</think>", "", cleaned)
    cleaned = re.sub(r"(?im)^thinking process:\s*$", "", cleaned)
    cleaned = re.sub(r"(?im)^analysis:\s*$", "", cleaned)
    return cleaned.strip()


def _insert_section_breaks(answer: str) -> str:
    normalized = answer
    for label in SECTION_LABELS:
        normalized = re.sub(
            rf"(?<!\n)\s*({label}[:：])",
            r"\n\1",
            normalized,
        )
    return normalized.strip()


def _structured_answer_only(answer: str) -> str:
    normalized = _insert_section_breaks(answer)
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    structured_lines = []

    for label in SECTION_LABELS:
        matched = next(
            (
                line
                for line in lines
                if line.startswith(f"{label}：") or line.startswith(f"{label}:")
            ),
            None,
        )
        if matched is not None:
            structured_lines.append(matched.replace(":", "：", 1))

    if structured_lines:
        return "\n".join(structured_lines)
    return normalized


def sanitize_answer(answer: str) -> str:
    """Remove reasoning traces and normalize section formatting."""

    cleaned = _strip_reasoning_blocks(answer)
    cleaned = _structured_answer_only(cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned
