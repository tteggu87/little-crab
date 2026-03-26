"""
Agent context pipeline for little-crab.

This module provides a single read-only reasoning ingress for agent-facing
context assembly while keeping canonical truth ownership in the existing stores.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from opencrab.ontology.query import HybridQuery, QueryResult
from opencrab.stores.contracts import DocumentEventStore, OperationalStore


@dataclass(frozen=True)
class AgentContextRequest:
    """Parameters for building an agent-facing context bundle."""

    question: str
    spaces: list[str] | None = None
    limit: int = 10
    graph_depth: int = 1
    project: str | None = None
    source_id_prefix: str | None = None
    subject_id: str | None = None
    permission: str | None = None

    @property
    def graph_expansion_enabled(self) -> bool:
        return not bool(self.project or self.source_id_prefix)


@dataclass(frozen=True)
class AgentFact:
    """A directly retrieved fact or graph-visible observation."""

    source: str
    node_id: str | None
    score: float
    text: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    graph_context: dict[str, Any] | None = None
    status: str = "observed"

    def to_legacy_result(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "node_id": self.node_id,
            "score": self.score,
            "text": self.text,
            "metadata": self.metadata,
            "graph_context": self.graph_context,
        }


@dataclass(frozen=True)
class SupportingEvidence:
    """Evidence that helps an agent trust or inspect a retrieved fact."""

    ref: str
    ref_type: str
    text_excerpt: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProvenancePath:
    """A compact provenance or neighborhood path for an agent-facing fact."""

    nodes: list[str]
    relation: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InferredLink:
    """A lightweight inferred connection surfaced during context assembly."""

    from_id: str
    relation: str
    to_id: str
    basis: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MissingLink:
    """A known context gap that an agent may want to fill later."""

    kind: str
    description: str
    suggested_next_step: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PolicyHint:
    """A policy or permission hint relevant to the assembled context."""

    subject_id: str
    permission: str
    resource_id: str
    status: str
    reason: str


@dataclass(frozen=True)
class RawRef:
    """A raw reference back to a canonical store-owned identifier."""

    ref: str
    ref_type: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentContextBundle:
    """Read-only bundle consumed by agent-facing read paths."""

    facts: list[AgentFact]
    supporting_evidence: list[SupportingEvidence]
    provenance_paths: list[ProvenancePath]
    inferred_links: list[InferredLink]
    missing_links: list[MissingLink]
    policies: list[PolicyHint]
    scope: dict[str, Any]
    uncertainty: dict[str, Any]
    raw_refs: list[RawRef]

    def to_dict(self) -> dict[str, Any]:
        return {
            "facts": [asdict(item) for item in self.facts],
            "supporting_evidence": [asdict(item) for item in self.supporting_evidence],
            "provenance_paths": [asdict(item) for item in self.provenance_paths],
            "inferred_links": [asdict(item) for item in self.inferred_links],
            "missing_links": [asdict(item) for item in self.missing_links],
            "policies": [asdict(item) for item in self.policies],
            "scope": self.scope,
            "uncertainty": self.uncertainty,
            "raw_refs": [asdict(item) for item in self.raw_refs],
        }

    def legacy_results(self) -> list[dict[str, Any]]:
        return [fact.to_legacy_result() for fact in self.facts]


class AgentContextPipeline:
    """Read-only context assembly pipeline for agent-facing reasoning."""

    def __init__(
        self,
        hybrid_query: HybridQuery,
        documents: DocumentEventStore | None = None,
        operational: OperationalStore | None = None,
    ) -> None:
        self._hybrid_query = hybrid_query
        self._documents = documents
        self._operational = operational

    def build_context(self, request: AgentContextRequest) -> AgentContextBundle:
        """Build a read-only context bundle from the live local runtime."""
        results = self._hybrid_query.query(
            question=request.question,
            spaces=request.spaces,
            limit=request.limit,
            graph_depth=request.graph_depth,
            project=request.project,
            source_id_prefix=request.source_id_prefix,
        )

        facts = [self._fact_from_result(result) for result in results]
        supporting_evidence = self._collect_supporting_evidence(facts)
        provenance_paths = self._collect_provenance_paths(facts)
        inferred_links = self._collect_inferred_links(facts)
        missing_links = self._collect_missing_links(request, facts)
        policies = self._collect_policy_hints(request, facts)
        raw_refs = self._collect_raw_refs(facts)

        uncertainty = {
            "partial_knowledge_possible": True,
            "scope_filters_active": not request.graph_expansion_enabled,
            "graph_expansion_enabled": request.graph_expansion_enabled,
            "fact_count": len(facts),
            "notes": (
                []
                if facts
                else ["No facts matched the current request; context may be incomplete."]
            ),
        }
        scope = {
            "question": request.question,
            "spaces": request.spaces,
            "limit": request.limit,
            "graph_depth": request.graph_depth,
            "project": request.project,
            "source_id_prefix": request.source_id_prefix,
            "graph_expansion_enabled": request.graph_expansion_enabled,
        }

        return AgentContextBundle(
            facts=facts,
            supporting_evidence=supporting_evidence,
            provenance_paths=provenance_paths,
            inferred_links=inferred_links,
            missing_links=missing_links,
            policies=policies,
            scope=scope,
            uncertainty=uncertainty,
            raw_refs=raw_refs,
        )

    def _fact_from_result(self, result: QueryResult) -> AgentFact:
        return AgentFact(
            source=result.source,
            node_id=result.node_id,
            score=result.score,
            text=result.text,
            metadata=dict(result.metadata or {}),
            graph_context=dict(result.graph_context or {}) or None,
        )

    def _collect_supporting_evidence(
        self, facts: list[AgentFact]
    ) -> list[SupportingEvidence]:
        evidence: list[SupportingEvidence] = []

        for fact in facts:
            source_id = str(fact.metadata.get("source_id") or "")
            if source_id:
                evidence.append(
                    SupportingEvidence(
                        ref=source_id,
                        ref_type="source_document",
                        text_excerpt=fact.text,
                        metadata={"node_id": fact.node_id, "source": fact.source},
                    )
                )
            elif fact.node_id:
                evidence.append(
                    SupportingEvidence(
                        ref=fact.node_id,
                        ref_type="ontology_node",
                        text_excerpt=fact.text,
                        metadata={"source": fact.source},
                    )
                )
        return evidence

    def _collect_provenance_paths(
        self, facts: list[AgentFact]
    ) -> list[ProvenancePath]:
        paths: list[ProvenancePath] = []
        for fact in facts:
            if fact.graph_context and fact.graph_context.get("anchor_id") and fact.node_id:
                paths.append(
                    ProvenancePath(
                        nodes=[str(fact.graph_context["anchor_id"]), str(fact.node_id)],
                        relation="graph_neighbor",
                        metadata={
                            "labels": list(fact.graph_context.get("labels", [])),
                            "source": fact.source,
                        },
                    )
                )
        return paths

    def _collect_inferred_links(self, facts: list[AgentFact]) -> list[InferredLink]:
        links: list[InferredLink] = []
        for fact in facts:
            anchor_id = fact.graph_context.get("anchor_id") if fact.graph_context else None
            if fact.source == "graph" and anchor_id and fact.node_id:
                links.append(
                    InferredLink(
                        from_id=str(anchor_id),
                        relation="neighbor_of",
                        to_id=str(fact.node_id),
                        basis="graph_expansion",
                        metadata={"labels": list(fact.graph_context.get("labels", []))},
                    )
                )
        return links

    def _collect_missing_links(
        self,
        request: AgentContextRequest,
        facts: list[AgentFact],
    ) -> list[MissingLink]:
        missing: list[MissingLink] = []
        if not facts:
            missing.append(
                MissingLink(
                    kind="no_match",
                    description="No matching facts were found for the current request.",
                    suggested_next_step="Ingest more source material or add ontology nodes and edges.",
                )
            )
        if not request.graph_expansion_enabled:
            missing.append(
                MissingLink(
                    kind="scope_constrained_graph_expansion",
                    description=(
                        "Graph expansion was intentionally disabled because the request "
                        "included project or source prefix scope filters."
                    ),
                    suggested_next_step="Retry without scope filters if broader graph exploration is desired.",
                    metadata={
                        "project": request.project,
                        "source_id_prefix": request.source_id_prefix,
                    },
                )
            )
        return missing

    def _collect_policy_hints(
        self,
        request: AgentContextRequest,
        facts: list[AgentFact],
    ) -> list[PolicyHint]:
        if not request.subject_id or not request.permission or self._operational is None:
            return []

        hints: list[PolicyHint] = []
        for fact in facts:
            resource_id = fact.node_id or str(fact.metadata.get("resource_id") or "")
            if not resource_id:
                continue
            stored = self._operational.check_policy(
                request.subject_id,
                request.permission,
                resource_id,
            )
            if stored is None:
                continue
            hints.append(
                PolicyHint(
                    subject_id=request.subject_id,
                    permission=request.permission,
                    resource_id=resource_id,
                    status="granted" if stored else "denied",
                    reason="Explicit policy hint from operational store.",
                )
            )
        return hints

    def _collect_raw_refs(self, facts: list[AgentFact]) -> list[RawRef]:
        refs: list[RawRef] = []
        seen: set[tuple[str, str]] = set()
        for fact in facts:
            if fact.node_id:
                key = ("node", str(fact.node_id))
                if key not in seen:
                    refs.append(RawRef(ref=str(fact.node_id), ref_type="node"))
                    seen.add(key)
            source_id = str(fact.metadata.get("source_id") or "")
            if source_id:
                key = ("source_document", source_id)
                if key not in seen:
                    refs.append(RawRef(ref=source_id, ref_type="source_document"))
                    seen.add(key)
        return refs
