---
status: Active
source_of_truth: No
last_updated: 2026-03-26
superseded_by: N/A
---

# Usage Guide

This guide explains how to set up little-crab as an MCP server, where to place source material, and what kinds of requests work well with an agent.

## 1. Install And Initialize

These examples assume `python` resolves to Python 3.11 or newer.

```bash
python -m pip install -e ".[dev]"
littlecrab init
littlecrab status
```

This creates `.env` and a local runtime directory such as `opencrab_data/`.

## 2. Connect From Codex

Windows repo-local example:

```bash
codex mcp add little-crab ^
  --env PYTHONPATH=C:\path\to\little-crab ^
  --env STORAGE_MODE=local ^
  --env LOCAL_DATA_DIR=C:\path\to\little-crab\opencrab_data ^
  --env CHROMA_COLLECTION=little_crab_vectors ^
  --env MCP_SERVER_NAME=little-crab ^
  --env MCP_SERVER_VERSION=0.1.0 ^
  --env LOG_LEVEL=WARNING ^
  -- littlecrab serve
```

Then check:

```bash
codex mcp list
```

Open a new Codex session after registration so the MCP server is available to the agent.

If the canonical `littlecrab` command is not on `PATH`, activate your virtualenv first. On Windows systems where `python` still resolves to 3.10, fall back to:

```bash
py -3.12 -m opencrab.cli serve
```

## 3. Connect From Claude Code

```bash
claude mcp add little-crab -- littlecrab serve
```

Compatibility aliases are still available:

```bash
claude mcp add little-crab -- little-crab serve
claude mcp add little-crab -- opencrab serve
```

## 4. Recommended Project Layout

```text
your-project/
├── knowledge/
│   ├── inbox/
│   ├── curated/
│   └── exports/
├── opencrab_data/
└── ...
```

Recommended use:

- `knowledge/inbox/`
  - raw notes
  - meeting transcripts
  - markdown docs
  - reports
  - copied text snippets
- `knowledge/curated/`
  - important cleaned documents
  - high-signal reference notes
  - approved summaries
- `knowledge/exports/`
  - optional output you want to keep outside runtime state
- `opencrab_data/`
  - runtime database files
  - vector collection
  - graph storage

Do not treat `opencrab_data/` as a document folder. That is runtime state, not source material.

## 5. How To Load Material

### Batch from disk

```bash
littlecrab ingest ./knowledge/inbox -r
littlecrab ingest ./knowledge/curated -r
```

### Through an agent over MCP

Use this pattern:

1. Ask the agent to read the files you care about.
2. Ask it to `ontology_ingest` the important text.
3. Ask it to `ontology_extract` if you want bootstrap structure.
4. Ask it to `ontology_query` or analysis tools to answer your actual question.

## 6. Good Requests

Bootstrap requests:

- `먼저 ontology_manifest로 문법을 보여주고, 어떤 space들이 있는지 설명해줘.`
- `knowledge/inbox 폴더 문서 중 중요한 것부터 읽고 ontology_ingest 해줘.`
- `같은 문서들에서 concept, claim, evidence를 ontology_extract로 초안 생성해줘.`

Retrieval requests:

- `incident report와 reliability 관련 내용을 ontology_query로 찾아줘.`
- `cache ttl 관련 문서와 연결된 concept, claim, outcome을 묶어서 보여줘.`

Analysis requests:

- `user-alice가 ds-events를 볼 수 있는지 ontology_rebac_check로 확인해줘.`
- `cache-ttl-lever를 raises 0.7로 움직였을 때 outcome 영향이 뭔지 ontology_lever_simulate로 보여줘.`
- `cache-ttl-lever 변경이 impact 관점에서 어떤 범주를 건드리는지 ontology_impact로 정리해줘.`

Refinement requests:

- `이 문서에서 빠진 노드가 있으면 ontology_add_node와 ontology_add_edge로 보강해줘.`
- `새 문서가 기존 claim을 강화하는지, 반박하는지 설명하고 필요한 graph 보강을 제안해줘.`

## 7. Recommended Agent Prompt Pattern

```text
1. ontology_manifest로 문법을 먼저 확인해.
2. 내가 지정한 knowledge 폴더 문서를 읽어.
3. 중요한 본문은 ontology_ingest 해.
4. 필요하면 ontology_extract로 concept/claim/evidence 초안을 만들어.
5. 마지막에는 ontology_query 또는 rebac/impact/simulation으로 결과를 정리해.
6. 무엇을 추가했고 무엇이 아직 불확실한지 구분해서 말해.
```

## 8. When To Use Which Tool

- `ontology_manifest`
  - 문법 확인
  - 어떤 space / relation이 가능한지 확인
- `ontology_ingest`
  - retrieval용 텍스트 적재
  - 문서 검색 기반을 먼저 만들 때
- `ontology_extract`
  - concept / claim / evidence 부트스트랩
  - 구조 초안이 필요할 때
- `ontology_query`
  - 의미 검색 + graph anchor 조회
- `ontology_add_node`
  - 명시적으로 노드를 추가할 때
- `ontology_add_edge`
  - 명시적으로 relation을 추가할 때
- `ontology_rebac_check`
  - 접근 권한 판단
- `ontology_impact`
  - 변경 영향 분석
- `ontology_lever_simulate`
  - 레버 조정에 대한 outcome 예측

## 9. Practical Notes

- The canonical CLI command is `littlecrab`.
- `little-crab` and `opencrab` remain available only as compatibility aliases.
- little-crab는 local-only runtime입니다.
- Docker, Neo4j, MongoDB, PostgreSQL 운영 경로는 현재 범위가 아닙니다.
- 현재 extractor는 heuristic 중심이라, `model` 문자열이 보여도 외부 LLM extractor가 기본으로 도는 구조는 아닙니다.
- retrieval 품질은 문서 품질과 metadata 정리에 크게 좌우됩니다.

## 10. First Session Checklist

1. `littlecrab status`
2. MCP 연결 확인
3. `ontology_manifest`
4. `knowledge/inbox/` 문서 ingest
5. 필요한 문서 extract
6. 첫 query
7. 필요한 경우 node/edge 보강
