"""
Local-first ontology extractor with optional LLM enrichment.

The extractor preserves little-crab's no-network-required heuristic bootstrap
while selectively catching up to upstream OpenCrab's richer extractor direction.
If an Anthropic client is available and configured, the extractor can enrich the
result with LLM-produced nodes and edges; otherwise it stays purely heuristic.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import textwrap
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_GRAMMAR_SUMMARY = """
MetaOntology 9-Space grammar:

SPACES and valid node types:
  subject  → User, Team, Org, Agent
  resource → Project, Document, File, Dataset, Tool, API
  evidence → TextUnit, LogEntry, Evidence
  concept  → Entity, Concept, Topic, Class
  claim    → Claim, Covariate
  community→ Community, CommunityReport
  outcome  → Outcome, KPI, Risk
  lever    → Lever
  policy   → Policy, Sensitivity, ApprovalRule

Valid meta-edges (from_space → to_space: [relations]):
  subject  → resource  : owns, member_of, manages, can_view, can_edit, can_execute, can_approve
  resource → evidence  : contains, derived_from, logged_as
  evidence → concept   : mentions, describes, exemplifies
  evidence → claim     : supports, contradicts, timestamps
  concept  → concept   : related_to, subclass_of, part_of, influences, depends_on
  concept  → outcome   : contributes_to, constrains, predicts, degrades
  lever    → outcome   : raises, lowers, stabilizes, optimizes
  lever    → concept   : affects
  community→ concept   : clusters, summarizes
  policy   → resource  : protects, classifies, restricts
  policy   → subject   : permits, denies, requires_approval
""".strip()


@dataclass
class ExtractedNode:
    space: str
    node_type: str
    node_id: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedEdge:
    from_space: str
    from_id: str
    relation: str
    to_space: str
    to_id: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    nodes: list[ExtractedNode] = field(default_factory=list)
    edges: list[ExtractedEdge] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    mode: str = "heuristic"
    model: str = "heuristic"
    source_id: str = ""
    llm_requested: bool = False
    llm_attempted: bool = False
    heuristic_fallback_used: bool = False
    chunk_count: int = 0


class LLMExtractor:
    """
    Local-first extractor with optional Anthropic-backed enrichment.

    Behavior:
    - always produces a deterministic resource/evidence bootstrap
    - adds heuristic concept/claim extraction when running in heuristic mode or
      when the LLM path is unavailable / empty
    - optionally enriches the result with chunked Anthropic extraction when an
      API key and SDK are available
    """

    _STOPWORDS = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
        "have", "in", "into", "is", "it", "its", "of", "on", "or", "that", "the",
        "their", "this", "to", "was", "were", "will", "with", "we", "you", "your",
        "they", "them", "can", "could", "should", "would", "about", "after",
        "before", "during", "over", "under", "through", "using", "used", "use",
    }

    _CLAIM_CUES = (
        " is ",
        " are ",
        " was ",
        " were ",
        " can ",
        " should ",
        " must ",
        " improves ",
        " degrade",
        " affects ",
        " raises ",
        " lowers ",
        " reduces ",
        " increases ",
    )

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "heuristic",
        chunk_size: int = 3000,
    ) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._model = model
        self._chunk_size = chunk_size
        self._client: Any | None = None

    def extract_from_text(self, text: str, source_id: str) -> ExtractionResult:
        result = ExtractionResult(
            mode="heuristic",
            model=self._model,
            source_id=source_id,
            llm_requested=self._llm_mode() is not None,
        )
        cleaned = text.strip()
        if not cleaned:
            result.errors.append("Empty text.")
            return result

        result.chunk_count = len(self._split(cleaned))
        resource_node, evidence_node = self._bootstrap_resource_evidence(cleaned, source_id)
        result.nodes.extend([resource_node, evidence_node])
        result.edges.append(
            ExtractedEdge(
                from_space="resource",
                from_id=resource_node.node_id,
                relation="contains",
                to_space="evidence",
                to_id=evidence_node.node_id,
                properties={"source_id": source_id},
            )
        )

        llm_nodes: list[ExtractedNode] = []
        llm_edges: list[ExtractedEdge] = []
        llm_errors: list[str] = []
        llm_mode = self._llm_mode()

        if llm_mode is not None:
            result.llm_attempted = True
            try:
                llm_nodes, llm_edges = self._extract_llm_chunks(cleaned, source_id)
                result.mode = llm_mode if (llm_nodes or llm_edges) else "heuristic"
            except Exception as exc:
                logger.warning("LLM extraction failed; falling back to heuristic mode: %s", exc)
                llm_errors.append(str(exc))
                result.mode = "heuristic"
                result.heuristic_fallback_used = True

        if llm_nodes or llm_edges:
            result.nodes.extend(llm_nodes)
            result.edges.extend(llm_edges)
        else:
            if result.llm_requested:
                result.heuristic_fallback_used = True
            self._append_heuristic_semantics(result, cleaned, source_id, evidence_node.node_id)

        result.errors.extend(llm_errors)
        result.nodes = self._dedupe_nodes(result.nodes)
        result.edges = self._dedupe_edges(result.edges)
        return result

    def extract_from_file(self, path: str | Path) -> ExtractionResult:
        source_path = Path(path)
        text = source_path.read_text(encoding="utf-8", errors="ignore")
        return self.extract_from_text(text=text, source_id=str(source_path.resolve()))

    def _bootstrap_resource_evidence(
        self, text: str, source_id: str
    ) -> tuple[ExtractedNode, ExtractedNode]:
        resource_node = ExtractedNode(
            space="resource",
            node_type="Document",
            node_id=self._resource_id(source_id),
            properties={
                "name": Path(source_id).name or source_id,
                "source_id": source_id,
            },
        )
        evidence_node = ExtractedNode(
            space="evidence",
            node_type="TextUnit",
            node_id=self._evidence_id(source_id),
            properties={
                "name": f"Evidence from {Path(source_id).name or source_id}",
                "text": text[:4000],
                "source_id": source_id,
            },
        )
        return resource_node, evidence_node

    def _append_heuristic_semantics(
        self,
        result: ExtractionResult,
        text: str,
        source_id: str,
        evidence_id: str,
    ) -> None:
        for phrase in self._extract_concepts(text):
            concept_node = ExtractedNode(
                space="concept",
                node_type="Concept",
                node_id=self._concept_id(phrase),
                properties={"name": phrase},
            )
            result.nodes.append(concept_node)
            result.edges.append(
                ExtractedEdge(
                    from_space="evidence",
                    from_id=evidence_id,
                    relation="mentions",
                    to_space="concept",
                    to_id=concept_node.node_id,
                    properties={"source_id": source_id},
                )
            )

        for index, sentence in enumerate(self._extract_claims(text), start=1):
            claim_node = ExtractedNode(
                space="claim",
                node_type="Claim",
                node_id=self._claim_id(source_id, index),
                properties={"text": sentence, "source_id": source_id},
            )
            result.nodes.append(claim_node)
            result.edges.append(
                ExtractedEdge(
                    from_space="evidence",
                    from_id=evidence_id,
                    relation="supports",
                    to_space="claim",
                    to_id=claim_node.node_id,
                    properties={"source_id": source_id},
                )
            )

    def _extract_concepts(self, text: str) -> list[str]:
        phrases: list[str] = []

        title_case_hits = re.findall(
            r"\b(?:[A-Z][a-z0-9]+(?:\s+[A-Z][a-z0-9]+){0,2}|[A-Z]{2,})\b",
            text,
        )
        for hit in title_case_hits:
            normalized = hit.strip(".,:;()[]{}\"'")
            if len(normalized) >= 3:
                phrases.append(normalized)

        quoted_hits = re.findall(r"[\"'“”](.{3,80}?)[\"'“”]", text)
        for hit in quoted_hits:
            normalized = hit.strip()
            if normalized:
                phrases.append(normalized)

        words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text.lower())
        counts = Counter(w for w in words if w not in self._STOPWORDS)
        for word, _count in counts.most_common(3):
            phrases.append(word.replace("_", " ").replace("-", " "))

        unique: list[str] = []
        seen: set[str] = set()
        for phrase in phrases:
            key = phrase.casefold()
            if key in seen:
                continue
            seen.add(key)
            unique.append(phrase)
            if len(unique) >= 5:
                break
        return unique

    def _extract_claims(self, text: str) -> list[str]:
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", text)
            if sentence.strip()
        ]

        claims: list[str] = []
        for sentence in sentences:
            normalized = f" {sentence.lower()} "
            if len(sentence.split()) < 5:
                continue
            if any(cue in normalized for cue in self._CLAIM_CUES):
                claims.append(sentence)
            if len(claims) >= 3:
                break
        return claims

    def _llm_mode(self) -> str | None:
        if self._model.strip().lower() == "heuristic":
            return None
        if not self._api_key:
            return None
        return "anthropic"

    def _extract_llm_chunks(
        self, text: str, source_id: str
    ) -> tuple[list[ExtractedNode], list[ExtractedEdge]]:
        chunks = self._split(text)
        all_nodes: list[ExtractedNode] = []
        all_edges: list[ExtractedEdge] = []
        errors: list[str] = []

        for index, chunk in enumerate(chunks):
            try:
                nodes, edges = self._extract_chunk(chunk, source_id, chunk_index=index)
                all_nodes.extend(nodes)
                all_edges.extend(edges)
            except Exception as exc:
                logger.warning("Chunk %d extraction failed: %s", index, exc)
                errors.append(str(exc))

        if errors and not (all_nodes or all_edges):
            raise RuntimeError("; ".join(errors))
        return all_nodes, all_edges

    def _split(self, text: str) -> list[str]:
        paragraphs = re.split(r"\n{2,}", text)
        chunks: list[str] = []
        current = ""
        for para in paragraphs:
            if len(current) + len(para) > self._chunk_size and current:
                chunks.append(current.strip())
                current = para
            else:
                current = current + "\n\n" + para if current else para
        if current.strip():
            chunks.append(current.strip())
        return chunks or [text[: self._chunk_size]]

    def _extract_chunk(
        self,
        chunk: str,
        source_id: str,
        chunk_index: int,
    ) -> tuple[list[ExtractedNode], list[ExtractedEdge]]:
        client = self._anthropic_client()
        prompt = textwrap.dedent(
            f"""
            You are an expert knowledge graph builder using the MetaOntology OS grammar.

            {_GRAMMAR_SUMMARY}

            Source file: {source_id}

            Analyze the following text and extract meaningful ontology nodes and edges.

            Rules:
            - node_id must be a stable snake_case identifier
            - only use spaces and node types listed above
            - only use valid relations for the corresponding space pair
            - return empty arrays if the chunk contains no clear ontology signal

            Text:
            ---
            {chunk[:2500]}
            ---

            Respond ONLY with JSON in this shape:
            {{
              "nodes": [
                {{"space": "subject", "node_type": "Agent", "node_id": "example_agent", "properties": {{"name": "Example"}}}}
              ],
              "edges": [
                {{"from_space": "subject", "from_id": "example_agent", "relation": "owns", "to_space": "resource", "to_id": "example_document", "properties": {{}}}}
              ]
            }}
            """
        ).strip()

        response = client.messages.create(
            model=self._model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        data = self._extract_json_payload(raw, chunk_index)

        nodes = [
            ExtractedNode(
                space=node["space"],
                node_type=node["node_type"],
                node_id=node["node_id"],
                properties=node.get("properties", {}),
            )
            for node in data.get("nodes", [])
        ]
        edges = [
            ExtractedEdge(
                from_space=edge["from_space"],
                from_id=edge["from_id"],
                relation=edge["relation"],
                to_space=edge["to_space"],
                to_id=edge["to_id"],
                properties=edge.get("properties", {}),
            )
            for edge in data.get("edges", [])
        ]
        return nodes, edges

    def _anthropic_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import anthropic  # type: ignore[import]
        except Exception as exc:  # pragma: no cover - depends on optional install
            raise RuntimeError("Anthropic SDK is unavailable") from exc
        self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def _extract_json_payload(self, raw: str, chunk_index: int) -> dict[str, Any]:
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if json_match:
            raw = json_match.group(1)
        elif not raw.startswith("{"):
            brace_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if brace_match:
                raw = brace_match.group(0)
            else:
                logger.debug("No JSON found in LLM response for chunk %d", chunk_index)
                return {"nodes": [], "edges": []}
        return json.loads(raw)

    def _resource_id(self, source_id: str) -> str:
        return f"resource-{self._short_hash(source_id)}"

    def _evidence_id(self, source_id: str) -> str:
        return f"evidence-{self._short_hash(source_id)}"

    def _concept_id(self, phrase: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", phrase.casefold()).strip("-") or "concept"
        return f"concept-{slug[:40]}-{self._short_hash(phrase.casefold())}"

    def _claim_id(self, source_id: str, index: int) -> str:
        return f"claim-{self._short_hash(source_id)}-{index}"

    def _short_hash(self, value: str) -> str:
        return hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]

    def _dedupe_nodes(self, nodes: list[ExtractedNode]) -> list[ExtractedNode]:
        deduped: list[ExtractedNode] = []
        seen: set[tuple[str, str]] = set()
        for node in nodes:
            key = (node.space, node.node_id)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(node)
        return deduped

    def _dedupe_edges(self, edges: list[ExtractedEdge]) -> list[ExtractedEdge]:
        deduped: list[ExtractedEdge] = []
        seen: set[tuple[str, str, str, str, str]] = set()
        for edge in edges:
            key = (
                edge.from_space,
                edge.from_id,
                edge.relation,
                edge.to_space,
                edge.to_id,
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(edge)
        return deduped
