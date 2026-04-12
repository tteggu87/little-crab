"""
Agent context pipeline for little-crab.

This module provides a single read-only reasoning ingress for agent-facing
context assembly while keeping canonical truth ownership in the existing stores.
"""

from __future__ import annotations

from collections.abc import Callable
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

        enrichment_notes: list[str] = []
        enrichment_gaps: list[MissingLink] = []
        facts = [self._fact_from_result(result) for result in results]
        supporting_evidence = self._collect_supporting_evidence(
            facts,
            enrichment_notes,
            enrichment_gaps,
        )
        provenance_paths = self._collect_provenance_paths(facts)
        inferred_links = self._collect_inferred_links(facts)
        missing_links = self._collect_missing_links(
            request,
            facts,
            supporting_evidence,
            provenance_paths,
        )
        missing_links.extend(enrichment_gaps)
        policies = self._collect_policy_hints(
            request,
            facts,
            enrichment_notes,
            missing_links,
        )
        raw_refs = self._collect_raw_refs(facts)

        notes = (
            []
            if facts
            else ["No facts matched the current request; context may be incomplete."]
        )
        notes.extend(enrichment_notes)
        uncertainty = {
            "partial_knowledge_possible": True,
            "scope_filters_active": not request.graph_expansion_enabled,
            "graph_expansion_enabled": request.graph_expansion_enabled,
            "fact_count": len(facts),
            "notes": notes,
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
            status="inferred" if result.source == "graph" else "confirmed",
        )

    def _collect_supporting_evidence(
        self,
        facts: list[AgentFact],
        enrichment_notes: list[str],
        missing_links: list[MissingLink],
    ) -> list[SupportingEvidence]:
        evidence: list[SupportingEvidence] = []
        source_map = self._load_supporting_sources(
            facts,
            enrichment_notes,
            missing_links,
        )
        node_doc_map = self._load_node_documents(
            facts,
            enrichment_notes,
            missing_links,
        )

        for fact in facts:
            source_id = str(fact.metadata.get("source_id") or "")
            if source_id:
                stored_source = source_map.get(source_id)
                evidence.append(
                    SupportingEvidence(
                        ref=source_id,
                        ref_type="source_document",
                        text_excerpt=(
                            _trim_excerpt(str(stored_source.get("text") or ""))
                            if stored_source
                            else fact.text
                        ),
                        metadata={
                            "node_id": fact.node_id,
                            "source": fact.source,
                            "source_metadata": (
                                dict(stored_source.get("metadata") or {})
                                if stored_source
                                else {}
                            ),
                        },
                    )
                )
            elif fact.node_id:
                node_doc = None
                space = str(fact.metadata.get("space") or "")
                if space:
                    node_doc = node_doc_map.get((space, fact.node_id))
                evidence.append(
                    SupportingEvidence(
                        ref=fact.node_id,
                        ref_type="ontology_node",
                        text_excerpt=_node_excerpt(node_doc) or fact.text,
                        metadata={
                            "source": fact.source,
                            "space": space or None,
                            "properties": (
                                dict(node_doc.get("properties") or {})
                                if node_doc
                                else {}
                            ),
                        },
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
            source_id = str(fact.metadata.get("source_id") or "")
            if source_id and fact.node_id:
                paths.append(
                    ProvenancePath(
                        nodes=[source_id, str(fact.node_id)],
                        relation="source_supports_fact",
                        metadata={"source": fact.source},
                    )
                )
        return paths

    def _collect_inferred_links(self, facts: list[AgentFact]) -> list[InferredLink]:
        links: list[InferredLink] = []
        for fact in facts:
            graph_context = fact.graph_context or {}
            anchor_id = graph_context.get("anchor_id")
            if fact.source == "graph" and anchor_id and fact.node_id:
                links.append(
                    InferredLink(
                        from_id=str(anchor_id),
                        relation="neighbor_of",
                        to_id=str(fact.node_id),
                        basis="graph_expansion",
                        metadata={"labels": list(graph_context.get("labels", []))},
                    )
                )
        return links

    def _collect_missing_links(
        self,
        request: AgentContextRequest,
        facts: list[AgentFact],
        supporting_evidence: list[SupportingEvidence],
        provenance_paths: list[ProvenancePath],
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
        evidence_refs = {item.ref for item in supporting_evidence}
        provenance_targets = {path.nodes[-1] for path in provenance_paths if path.nodes}
        for fact in facts:
            if fact.node_id and fact.node_id not in evidence_refs and not fact.metadata.get("source_id"):
                missing.append(
                    MissingLink(
                        kind="missing_supporting_evidence",
                        description=(
                            f"Fact {fact.node_id} has no linked source document evidence in the "
                            "current context bundle."
                        ),
                        suggested_next_step="Attach supporting source material or ingest a related document.",
                        metadata={"node_id": fact.node_id},
                    )
                )
            if fact.node_id and fact.node_id not in provenance_targets and fact.source != "vector":
                missing.append(
                    MissingLink(
                        kind="missing_provenance_path",
                        description=(
                            f"Fact {fact.node_id} is visible but has no explicit provenance path "
                            "in the current context bundle."
                        ),
                        suggested_next_step="Investigate neighboring evidence or add missing relation edges.",
                        metadata={"node_id": fact.node_id},
                    )
                )
        return missing

    def _collect_policy_hints(
        self,
        request: AgentContextRequest,
        facts: list[AgentFact],
        enrichment_notes: list[str],
        missing_links: list[MissingLink],
    ) -> list[PolicyHint]:
        if not request.subject_id or not request.permission or self._operational is None:
            return []

        hints: list[PolicyHint] = []
        policy_map = self._load_policy_hints(
            request,
            facts,
            enrichment_notes,
            missing_links,
        )
        for fact in facts:
            if fact.metadata.get("space") not in (None, "resource", ""):
                continue
            resource_id = fact.node_id or str(fact.metadata.get("resource_id") or "")
            if not resource_id:
                continue
            stored = policy_map.get(resource_id)
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

    def _load_supporting_sources(
        self,
        facts: list[AgentFact],
        enrichment_notes: list[str],
        missing_links: list[MissingLink],
    ) -> dict[str, dict[str, Any]]:
        source_ids = [
            str(fact.metadata.get("source_id") or "")
            for fact in facts
            if str(fact.metadata.get("source_id") or "")
        ]
        if not source_ids or self._documents is None or not self._documents.available:
            return {}
        documents = self._documents
        return self._load_batch_map(
            keys=source_ids,
            batch_loader=getattr(documents, "get_sources", None),
            single_loader=documents.get_source,
            failure_message=lambda source_id, exc: (
                f"Supporting source lookup failed for {source_id}: {exc}"
            ),
            missing_link_factory=lambda source_id, exc: MissingLink(
                kind="supporting_evidence_unavailable",
                description=(
                    f"Supporting source lookup failed for {source_id}; "
                    "the context bundle used the retrieved fact text instead."
                ),
                suggested_next_step=(
                    "Retry after document store recovery or inspect the source "
                    "document directly."
                ),
                metadata={"ref": source_id, "error": str(exc)},
            ),
            enrichment_notes=enrichment_notes,
            missing_links=missing_links,
        )

    def _load_node_documents(
        self,
        facts: list[AgentFact],
        enrichment_notes: list[str],
        missing_links: list[MissingLink],
    ) -> dict[tuple[str, str], dict[str, Any]]:
        node_refs = [
            (str(fact.metadata.get("space") or ""), str(fact.node_id))
            for fact in facts
            if fact.node_id
            and str(fact.metadata.get("space") or "")
            and not str(fact.metadata.get("source_id") or "")
        ]
        if not node_refs or self._documents is None or not self._documents.available:
            return {}
        documents = self._documents
        return self._load_batch_map(
            keys=node_refs,
            batch_loader=getattr(documents, "get_node_docs", None),
            single_loader=lambda ref: documents.get_node_doc(ref[0], ref[1]),
            failure_message=lambda ref, exc: (
                f"Node document lookup failed for {ref[0]}/{ref[1]}: {exc}"
            ),
            missing_link_factory=lambda ref, exc: MissingLink(
                kind="supporting_evidence_unavailable",
                description=(
                    f"Node document lookup failed for {ref[0]}/{ref[1]}; "
                    "the context bundle used the retrieved fact text instead."
                ),
                suggested_next_step=(
                    "Retry after document store recovery or inspect the ontology "
                    "node directly."
                ),
                metadata={"ref": ref[1], "space": ref[0], "error": str(exc)},
            ),
            enrichment_notes=enrichment_notes,
            missing_links=missing_links,
        )

    def _load_policy_hints(
        self,
        request: AgentContextRequest,
        facts: list[AgentFact],
        enrichment_notes: list[str],
        missing_links: list[MissingLink],
    ) -> dict[str, bool]:
        resource_ids = [
            fact.node_id or str(fact.metadata.get("resource_id") or "")
            for fact in facts
            if fact.metadata.get("space") in (None, "resource", "")
            and (fact.node_id or str(fact.metadata.get("resource_id") or ""))
        ]
        if not resource_ids:
            return {}

        assert self._operational is not None
        subject_id = request.subject_id
        permission = request.permission
        assert subject_id is not None
        assert permission is not None

        batch_loader = getattr(self._operational, "check_policies", None)
        if callable(batch_loader):
            try:
                return dict(
                    batch_loader(
                        subject_id,
                        permission,
                        resource_ids,
                    )
                    or {}
                )
            except Exception as exc:
                for resource_id in resource_ids:
                    enrichment_notes.append(
                        f"Policy hint lookup failed for {resource_id}: {exc}"
                    )
                    missing_links.append(
                        MissingLink(
                            kind="policy_hint_unavailable",
                            description=(
                                f"Policy hint lookup failed for {resource_id}; "
                                "the context bundle omitted policy hints for this resource."
                            ),
                            suggested_next_step=(
                                "Retry after operational store recovery or inspect policies directly."
                            ),
                            metadata={"resource_id": resource_id, "error": str(exc)},
                        )
                    )
                return {}

        policy_map: dict[str, bool] = {}
        for resource_id in resource_ids:
            try:
                stored = self._operational.check_policy(
                    subject_id,
                    permission,
                    resource_id,
                )
            except Exception as exc:
                enrichment_notes.append(
                    f"Policy hint lookup failed for {resource_id}: {exc}"
                )
                missing_links.append(
                    MissingLink(
                        kind="policy_hint_unavailable",
                        description=(
                            f"Policy hint lookup failed for {resource_id}; "
                            "the context bundle omitted policy hints for this resource."
                        ),
                        suggested_next_step=(
                            "Retry after operational store recovery or inspect policies directly."
                        ),
                        metadata={"resource_id": resource_id, "error": str(exc)},
                    )
                )
                continue
            if stored is not None:
                policy_map[resource_id] = bool(stored)
        return policy_map

    def _load_batch_map(
        self,
        keys: list[Any],
        batch_loader: Callable[[list[Any]], dict[Any, dict[str, Any]] | None] | None,
        single_loader: Callable[[Any], dict[str, Any] | None],
        failure_message: Callable[[Any, Exception], str],
        missing_link_factory: Callable[[Any, Exception], MissingLink],
        enrichment_notes: list[str],
        missing_links: list[MissingLink],
    ) -> dict[Any, dict[str, Any]]:
        deduped_keys = list(dict.fromkeys(keys))
        if callable(batch_loader):
            try:
                return dict(batch_loader(deduped_keys) or {})
            except Exception as exc:
                for key in deduped_keys:
                    enrichment_notes.append(failure_message(key, exc))
                    missing_links.append(missing_link_factory(key, exc))
                return {}

        results: dict[Any, dict[str, Any]] = {}
        for key in deduped_keys:
            try:
                item = single_loader(key)
            except Exception as exc:
                enrichment_notes.append(failure_message(key, exc))
                missing_links.append(missing_link_factory(key, exc))
                continue
            if item is not None:
                results[key] = item
        return results

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


def _trim_excerpt(text: str, limit: int = 280) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _node_excerpt(node_doc: dict[str, Any] | None) -> str | None:
    if not node_doc:
        return None
    properties = dict(node_doc.get("properties") or {})
    for key in ("text", "description", "name"):
        value = properties.get(key)
        if value:
            return _trim_excerpt(str(value))
    return None
