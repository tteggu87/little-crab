"""
Heuristic ontology extractor used by the MCP extraction tool.

This keeps OpenCrab's extraction path available in local-first mode without
requiring network LLM access. The goal is not perfect ontology modelling; it
is to create a conservative bootstrap that an agent or human can refine.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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


class LLMExtractor:
    """
    Conservative extractor that currently falls back to deterministic heuristics.

    The class keeps the original API shape so the MCP surface can evolve toward a
    network-backed extractor later without breaking callers.
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

    def __init__(self, api_key: str | None = None, model: str = "heuristic") -> None:
        self._api_key = api_key or ""
        self._model = model

    def extract_from_text(self, text: str, source_id: str) -> ExtractionResult:
        result = ExtractionResult(mode="heuristic")
        cleaned = text.strip()
        if not cleaned:
            result.errors.append("Empty text.")
            return result

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
                "text": cleaned[:4000],
                "source_id": source_id,
            },
        )
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

        for phrase in self._extract_concepts(cleaned):
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
                    from_id=evidence_node.node_id,
                    relation="mentions",
                    to_space="concept",
                    to_id=concept_node.node_id,
                    properties={"source_id": source_id},
                )
            )

        for index, sentence in enumerate(self._extract_claims(cleaned), start=1):
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
                    from_id=evidence_node.node_id,
                    relation="supports",
                    to_space="claim",
                    to_id=claim_node.node_id,
                    properties={"source_id": source_id},
                )
            )

        result.nodes = self._dedupe_nodes(result.nodes)
        result.edges = self._dedupe_edges(result.edges)
        return result

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
