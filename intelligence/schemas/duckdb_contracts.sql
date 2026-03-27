-- Canonical DuckDB contract excerpt for little-crab.
-- Mirrors the live embedded operational store shape implemented in
-- opencrab/stores/duckdb_store.py.

CREATE TABLE node_documents (
    doc_id TEXT PRIMARY KEY,
    space TEXT NOT NULL,
    node_type TEXT NOT NULL,
    node_id TEXT NOT NULL,
    properties_json TEXT NOT NULL
);

CREATE TABLE source_documents (
    source_id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    metadata_json TEXT NOT NULL
);

CREATE TABLE audit_log (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    subject_id TEXT,
    details_json TEXT NOT NULL
);

CREATE TABLE ontology_nodes (
    space TEXT NOT NULL,
    node_type TEXT NOT NULL,
    node_id TEXT NOT NULL,
    PRIMARY KEY (space, node_id)
);

CREATE TABLE ontology_edges (
    from_space TEXT NOT NULL,
    from_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    to_space TEXT NOT NULL,
    to_id TEXT NOT NULL,
    PRIMARY KEY (from_space, from_id, relation, to_space, to_id)
);

CREATE TABLE rebac_policies (
    subject_id TEXT NOT NULL,
    permission TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    granted BOOLEAN NOT NULL,
    PRIMARY KEY (subject_id, permission, resource_id)
);

CREATE TABLE impact_records (
    id BIGINT PRIMARY KEY,
    node_id TEXT NOT NULL,
    change_type TEXT NOT NULL,
    impact_json TEXT NOT NULL
);

CREATE TABLE lever_simulations (
    id BIGINT PRIMARY KEY,
    lever_id TEXT NOT NULL,
    direction TEXT NOT NULL,
    magnitude DOUBLE NOT NULL,
    results_json TEXT NOT NULL
);

CREATE TABLE staged_operations (
    stage_id TEXT PRIMARY KEY,
    entry_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    published_at TIMESTAMP,
    publish_result_json TEXT NOT NULL
);
