---
description: Use for building, querying, serving, and validating this public UE knowledge-base package and its federated project layer.
---

# UE Knowledge Base RAG

Use the package interfaces as the authority for indexing and query behavior. Keep public and project knowledge physically separate.

## Build scopes

Build public and project indexes independently. Project sources require their own registry and must never be appended into a public snapshot.

```command
ue-kb build --scope public --db .chroma_db/public
ue-kb build --scope project --source-registry Source-Registry.tsv --db .chroma_db/project
```

## Query envelope

The compatibility JSON remains available. The optional envelope adds `coverage=supported|weak|none` and evidence metadata so a relative top score is not mistaken for authority.

## Federated query

Federated results group `public_hits` and `project_hits`. Do not compare raw scores across independently built indexes.

## MCP service

Long-running agents should use the resident MCP server so the embedding model remains warm. Measure startup, first query, and hot query separately.

## Corpus integrity

The publication manifest fixes the 90 public documents. Corpus hashes, provenance projection, privacy scanning, and deterministic Hermes rendering are release gates.

## Unsupported questions

Return `coverage=none` when public evidence does not cover a project-specific fact. Project status and acceptance facts are authoritative only in the project group.

## Focused reference

- [Query optimization](references/query-optimization.md)

## Verification boundary

Repository tests and package round trips prove implementation behavior. They do not prove a retrieved UE claim unless that document has its own source and validation evidence.
