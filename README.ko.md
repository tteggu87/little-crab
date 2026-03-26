# little-crab

[English README](README.md)

![little-crab logo](logo.png)

little-crab는 OpenCrab의 문법, validator, MCP tool surface, agentic ontology workflow를 유지하면서 서버형 데이터베이스 운영 부담을 제거한 로컬 퍼스트 포크입니다.

이 프로젝트의 핵심은 “OpenCrab 의미 체계를 버리지 않고 한 대의 머신에서 바로 돌릴 수 있게 만드는 것”입니다. 예전처럼 Neo4j, MongoDB, PostgreSQL 서비스를 따로 올리는 대신, 지금은 임베디드 로컬 스택으로 동작합니다.

- `LadybugDB`: 그래프 탐색
- `DuckDB`: 문서, audit event, registry, policy, impact, simulation
- embedded `ChromaDB`: 벡터 검색

패키지 이름은 `little-crab`이지만, 표준 CLI 명령은 `littlecrab`입니다. 기존 `little-crab`와 `opencrab`는 호환용 alias로 함께 제공합니다.

---

## 유지되는 것

- 9-space MetaOntology grammar
- grammar validation rules
- MCP tool names
  - `ontology_manifest`
  - `ontology_add_node`
  - `ontology_add_edge`
  - `ontology_query`
  - `ontology_impact`
  - `ontology_rebac_check`
  - `ontology_lever_simulate`
  - `ontology_extract`
  - `ontology_ingest`
- partial-knowledge 기반 agentic ontology workflow

## 달라진 것

- Docker 필수 아님
- Neo4j, MongoDB, PostgreSQL 의존성 제거
- 로컬 머신 중심 실행
- OpenCrab 의미 체계는 유지하고 운영 복잡도만 낮춤

---

## 빠른 시작

아래 예시는 `python`이 Python 3.11 이상을 가리킨다고 가정합니다.

### 1. 설치

```bash
python -m pip install -e ".[dev]"
```

### 2. 로컬 설정 초기화

```bash
littlecrab init
```

이 명령은 `.env`를 만들고 기본 로컬 런타임 설정을 채웁니다.

```env
STORAGE_MODE=local
LOCAL_DATA_DIR=./opencrab_data
CHROMA_COLLECTION=little_crab_vectors
MCP_SERVER_NAME=little-crab
MCP_SERVER_VERSION=0.1.0
LOG_LEVEL=INFO
```

### 3. 내장 스토어 확인

```bash
littlecrab status
```

### 4. 예제 데이터 시드

```bash
python scripts/seed_ontology.py
```

### 5. 질의 실행

```bash
littlecrab query "system performance and error rates"
littlecrab manifest
```

---

## Codex MCP 연결

Windows에서 저장소 로컬 경로를 바로 쓰는 예시는 아래와 같습니다.

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

등록 후 확인:

```bash
codex mcp list
```

새 MCP 서버를 현재 에이전트 세션에서 보려면 Codex 새 세션을 여는 편이 안전합니다.

만약 `littlecrab` 명령이 `PATH`에 없다면 먼저 가상환경을 활성화하세요. Windows에서 `python`이 아직 3.10을 가리키는 경우에는 아래 launcher fallback을 쓰면 됩니다.

```bash
py -3.12 -m opencrab.cli serve
```

## Claude Code MCP 연결

```bash
claude mcp add little-crab -- littlecrab serve
```

호환 alias를 써도 됩니다.

```bash
claude mcp add little-crab -- little-crab serve
claude mcp add little-crab -- opencrab serve
```

Claude Code용 JSON 설정 예시는 아래와 같습니다.

```json
{
  "mcpServers": {
    "little-crab": {
      "command": "littlecrab",
      "args": ["serve"],
      "env": {
        "LOCAL_DATA_DIR": "./opencrab_data"
      }
    }
  }
}
```

---

## 권장 폴더 구조

런타임 데이터와 원본 자료는 분리하는 게 좋습니다.

```text
your-project/
├── knowledge/
│   ├── inbox/        # 원본 메모, 문서, 보고서, 인터뷰, 회의록
│   ├── curated/      # 정리된 핵심 문서
│   └── exports/      # 선택적 산출물
├── opencrab_data/    # little-crab 런타임 데이터
└── ...
```

권장 방식:

- 학습시킬 자료는 `knowledge/inbox/` 또는 `knowledge/curated/` 아래에 넣습니다.
- `opencrab_data/`는 직접 수정하지 않는 것이 좋습니다.
- 처음에는 `.md`, `.txt`, `.py`, 짧은 plain text 문서 위주로 시작하는 게 편합니다.

## 자료 넣는 방법

디스크의 파일을 배치로 적재할 때:

```bash
littlecrab ingest ./knowledge/inbox -r
littlecrab ingest ./knowledge/curated -r
```

에이전트를 통해 MCP로 작업할 때:

- 에이전트에게 먼저 관련 파일을 읽게 합니다.
- semantic retrieval이 필요하면 `ontology_ingest`를 호출하게 합니다.
- concept, claim, evidence 부트스트랩이 필요하면 `ontology_extract`를 호출하게 합니다.
- 이후에는 `ontology_query`, `ontology_rebac_check`, `ontology_impact`, `ontology_lever_simulate`로 분석을 이어가게 합니다.

---

## 에이전트에게 이렇게 요청하면 좋음

좋은 시작 요청 예시:

- `먼저 ontology_manifest로 문법을 보여주고, 이 저장소에 맞는 공간 구성을 설명해줘.`
- `knowledge/inbox 폴더 문서들을 읽고 중요한 텍스트를 ontology_ingest 해줘.`
- `같은 문서들에서 concept, claim, evidence를 ontology_extract로 부트스트랩해줘.`
- `cache ttl, reliability, incident report 관련 내용을 ontology_query로 찾아줘.`
- `Alice가 events-dataset을 볼 수 있는지 ontology_rebac_check로 검사해줘.`
- `cache-ttl-lever를 올렸을 때 outcome 영향이 어떤지 ontology_lever_simulate로 보여줘.`
- `새 문서가 들어오면 기존 claim과 충돌하는지 확인해줘.`

권장 요청 패턴:

```text
1. 먼저 ontology_manifest로 현재 문법을 확인해.
2. knowledge/inbox 아래 문서 중 관련 있는 것만 읽어.
3. 중요한 본문은 ontology_ingest 해.
4. 필요한 경우 ontology_extract로 부트스트랩해.
5. 마지막에는 ontology_query 또는 impact/rebac/simulation으로 답을 정리해.
```

## 전형적인 사용 흐름

1. 원본 자료를 `knowledge/inbox/`에 넣습니다.
2. Codex 또는 Claude Code를 little-crab MCP에 연결합니다.
3. `ontology_manifest`로 문법을 먼저 확인합니다.
4. 자료를 ingest 하거나 extract 합니다.
5. 그래프와 벡터에서 query 합니다.
6. 필요하면 node/edge를 추가하며 온톨로지를 키웁니다.
7. 단순 검색이 아니라 분석이 필요하면 ReBAC, impact, lever simulation을 사용합니다.

더 자세한 가이드는 [docs/USAGE_GUIDE.md](docs/USAGE_GUIDE.md)를 보면 됩니다.

---

## CLI 요약

```text
littlecrab init               Create .env from template
littlecrab serve              Start MCP server (stdio)
littlecrab status             Check embedded store connections
littlecrab ingest <path>      Ingest files into vector store
littlecrab query <text>       Query hybrid local ontology data
littlecrab manifest           Print canonical ontology grammar manifest
```

호환 alias:

```text
little-crab <same-command>
opencrab <same-command>
```
