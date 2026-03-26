# Agent Session Evidence

- Status: `pass`
- Record count: `18`

## bootstrap
- Methods: `initialize, tools/list`
- server_name: `"little-crab"`
- tool_count: `9`

## scenario_1_manifest_node_edge
- Methods: `tools/call, tools/call, tools/call, tools/call`
- created_nodes: `["dogfood-user", "dogfood-doc"]`
- edge_relation: `"owns"`
- node_store_roles: `["documents", "graph", "registry"]`

## scenario_2_ingest_extract_query
- Methods: `tools/call, tools/call, tools/call`
- ingest_store_roles: `["documents", "vectors"]`
- extracted_nodes: `8`
- added_nodes: `8`
- query_total: `1`
- query_node_ids: `["lever-cache-ttl"]`

## scenario_3_rebac_impact_simulation
- Methods: `tools/call, tools/call, tools/call, tools/call, tools/call, tools/call, tools/call, tools/call, tools/call`
- rebac_granted: `true`
- impact_ids: `["I1", "I5", "I6", "I7", "I3"]`
- predicted_outcome_ids: `["system-reliability"]`
- simulation_confidence: `0.815`
