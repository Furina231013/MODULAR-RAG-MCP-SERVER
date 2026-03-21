"""Ask Playground page for retrieval-first answer generation."""

from __future__ import annotations

import streamlit as st

from src.core.answer import AskService
from src.observability.dashboard.services.data_service import DataService


def render() -> None:
    """Render the Ask Playground page."""

    st.header("💬 Ask Playground")
    st.markdown(
        "Run a real retrieval-first ask flow against the current collection, "
        "inspect the generated answer, and review the supporting chunks."
    )

    data_service = DataService()
    collections = data_service.list_collections()
    if "default" not in collections:
        collections.insert(0, "default")

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        question = st.text_area(
            "Question",
            value="",
            height=120,
            key="ask_question",
            placeholder="请输入你想基于当前知识库回答的问题…",
        )
    with col2:
        collection = st.selectbox(
            "Collection",
            options=collections,
            index=0,
            key="ask_collection",
        )
    with col3:
        top_k = st.number_input(
            "Top-K",
            min_value=1,
            max_value=20,
            value=5,
            key="ask_top_k",
        )
        use_rerank = st.checkbox("Use rerank", value=True, key="ask_use_rerank")

    if st.button("▶️ Generate Answer", type="primary", key="ask_run_btn"):
        if not question.strip():
            st.warning("请输入问题后再运行 Ask。")
            return

        with st.spinner("Retrieving chunks and generating answer…"):
            try:
                ask_service = AskService()
                result = ask_service.ask(
                    question.strip(),
                    collection=collection,
                    top_k=int(top_k),
                    use_rerank=use_rerank,
                )
            except Exception as exc:
                st.error(f"Ask failed: {exc}")
                return

        st.success("✅ Ask complete!")
        st.caption(
            f"status=`{result.answer_status}` · mode=`{result.answer_mode}` · "
            f"provider=`{result.provider}` · model=`{result.model or '—'}`"
        )
        if result.answer_note:
            st.info(result.answer_note)
        if result.log_path:
            st.caption(f"Log saved to: `{result.log_path}`")

        st.subheader("📝 Answer")
        st.text(result.answer)

        st.subheader(f"📚 Evidence Chunks ({len(result.chunks)})")
        if not result.chunks:
            st.info("No chunks returned for this question.")
            return

        for chunk in result.chunks:
            label = (
                f"#{chunk.rank:02d} · score={chunk.score:.4f} · "
                f"{chunk.source_path or chunk.chunk_id}"
            )
            with st.expander(label, expanded=(chunk.rank == 1)):
                st.text_area(
                    "Content",
                    value=chunk.text,
                    height=max(140, min(len(chunk.text) // 2, 420)),
                    disabled=True,
                    key=f"ask_chunk_{chunk.rank}_{chunk.chunk_id}",
                    label_visibility="collapsed",
                )
                st.json(
                    {
                        "chunk_id": chunk.chunk_id,
                        "source_path": chunk.source_path,
                        "metadata": chunk.metadata,
                    }
                )
