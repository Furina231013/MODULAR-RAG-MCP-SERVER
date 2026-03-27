# 更新日志

本文件用于记录项目中所有值得关注的变更。

当前采用简化版 `Keep a Changelog` 结构：
- `Unreleased` 表示已经合入、但尚未绑定正式版本号的改动。
- 已发布版本应与 `pyproject.toml` 中声明的版本保持一致。

## [Unreleased]

### 新增
- 新增共享查询运行时 `src/core/query_engine/runtime.py`，让 CLI 查询、ask 流程和评测流程复用同一套检索初始化逻辑。
- 新增检索优先的答案生成能力 `src/core/answer/ask_service.py`，以及对应命令行入口 `scripts/ask.py`。
- 新增 `logs/ask_runs` 下的 ask 运行日志，便于复现本地 RAG 闭环结果。
- 新增 Dashboard 的 Ask Playground 页面 `src/observability/dashboard/pages/ask_playground.py`。
- 新增面向 demo 文档的快速评测配置 `config/settings.eval_fast.yaml`。
- 新增正式的小型基线数据集 `tests/fixtures/golden_test_set_demo.json`。
- 新增面向复杂版 `demo.pdf` 的私有规则评测集 `tests/fixtures/golden_test_set_demo_private_v2.json`。
- 新增 `scripts/evaluate.py` 的 `--out` 参数，支持将 CLI 评测结果自动保存为 JSON 文件。

### 变更
- 更新 `config/settings.yaml`，支持通过 LM Studio 风格的 `base_url` 接入本地 OpenAI-compatible LLM 与 embedding 服务。
- 更新 `scripts/evaluate.py`，默认使用快速评测配置与 demo 对齐的 golden set。
- 更新 `src/observability/evaluation/eval_runner.py` 的集成方式，使深评测可以使用真实 ask 生成答案，而不是简单拼接 chunk 文本。
- 更新 `src/observability/dashboard/pages/evaluation_panel.py`，支持 `manual`、`auto_ask` 和 hybrid 三种答案来源模式。
- 更新 `src/core/settings.py`，支持 `evaluation.backends` 这类多后端评测配置。

### 修复
- 修复 `src/libs/llm/openai_llm.py` 与 `src/libs/llm/openai_vision_llm.py` 对本地 OpenAI-compatible `base_url` 的读取与使用。
- 修复 `src/observability/evaluation/ragas_evaluator.py` 对本地 judge 模型的兼容性问题，包括 `base_url` 透传与 OpenAI-compatible JSON schema 模式。
- 修复 `src/observability/evaluation/composite_evaluator.py` 中组合评测的指标过滤与配置复制逻辑。
- 修复 `src/libs/evaluator/custom_evaluator.py` 的 ID 提取逻辑，使其支持基于 `chunk_id` 的检索结果。
- 修复 `scripts/query.py` 及相关查询链路在 reranker 关闭场景下的兼容问题。

## [0.1.0] - 2026-03-21

### 新增
- 在 `pyproject.toml` 中声明项目的初始打包元数据。
- 初始化 Modular RAG MCP Server 的摄取、检索、MCP Server、Dashboard 与可观测性基础骨架。
