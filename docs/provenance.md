# Provenance and index scopes

v0.7 keeps reusable UE guidance and project evidence in separate indexes. The
schema-v2 claim ledger is the single source of truth for public trust metadata;
the sidecar is a generated, read-only projection and is not embedded into the
searchable Markdown text.

## Sidecar shape

Put `.ue-kb-provenance.json` beside a corpus, or pass `--provenance`:

```json
{
  "schema_version": 1,
  "scope": "public",
  "documents": {
    "ue-physics-collision/references/actor-collision-enable-state.md": {
      "knowledge_id": "uekb.<stable-path-digest>",
      "scope": "public",
      "content_sha256": "<sha256-of-markdown>",
      "engine_versions": ["5.7.4"],
      "verification": ["engine_source", "compile_test"],
      "claim_types": ["api", "runtime"],
      "verified_at": "2026-08-23",
      "evidence_refs": [
        "EngineSource:Actor.h::AActor::GetActorEnableCollision",
        "UEKB.ActorCollisionEnableState"
      ],
      "source_ids": [],
      "validation_ids": ["UEKnowledgeValidation.ActorCollisionEnableState"],
      "expires_at": null,
      "audit_status": "verified",
      "human_evidence": "not_run"
    }
  }
}
```

`knowledge_id` is derived from the normalized relative path. Do not put local
drive paths, project names, Bead IDs, or private evidence text in a public
sidecar. Project entries use `scope=project` and must list `source_ids` that
exist in the supplied `Source-Registry.tsv`.

For a new corpus, create a fail-closed review queue with:

```bash
python scripts/scaffold_provenance.py \
  --source src/ue_knowledge/knowledge \
  --output src/ue_knowledge/knowledge/.ue-kb-provenance.json
```

The v0.7 publication path uses `scripts/prepare_corpus_audit.py` to regenerate
both `validation/corpus-audit.json` and the public sidecar from the corpus. The
scaffold fills stable IDs and explicit pending values only; it never invents
engine versions, evidence, or human acceptance. Do not hand-edit the generated
sidecar: update the ledger/review decision and regenerate it.

The accepted verification types are `engine_source`, `epic_docs`,
`compile_test`, `runtime_test`, and `human_required`. API claims require a
compile test and at least one `validation_id`; runtime claims require a runtime
test and at least one `validation_id`; visual or discoverability claims require
a human evidence result. Pass `--evidence-manifest <json>` to verify those IDs
against the sanitized UE validation report. The audit remains fail-closed until
every Markdown document is covered and marked `audit_status=verified`.

## Commands

```bash
ue-kb audit-corpus --source <corpus> --provenance <sidecar> \
  --evidence-manifest <ue-validation.json> --claim-ledger <corpus-audit.json> --json
ue-kb build --scope public --provenance <sidecar> --strict-provenance
ue-kb build --scope project --source <project-notes> \
  --source-registry <Source-Registry.tsv> --db <project-index>
ue-kb federated-query "<question>" \
  --index public=<PUBLIC_INDEX> --index project=<PROJECT_INDEX> --json
```

`--strict-provenance` is the release gate. A normal build may create a local
working index with pending entries, but its manifest advertises that the
index is not release-ready.

Before creating a v0.7 candidate package, run the combined local gate. It
requires both a strict corpus audit and a sanitized UE evidence manifest:

```bash
python scripts/release_gate.py \
  --source src/ue_knowledge/knowledge \
  --evidence-manifest validation/artifacts/ue57/ue57-validation-evidence.json \
  --claim-ledger validation/corpus-audit.json
```

The schema-v2 claim ledger inventories semantic sections and owned code
artifacts. A code fence is not a second copy of its parent section: it carries
its own stable artifact ID, code kind, and parent claim. The scanner only
proposes classifications; reviewers must set `non_claim`, `concept`,
`api_contract`, `runtime_behavior`, or `human_outcome` and attach the evidence
required by that disposition. Its hashes must match the current corpus, every
document must be reviewed, and every linked compile/runtime/human result must
pass. The scaffold intentionally fails this command until all 90 documents
have real review decisions; that failure is the release blocker, not a
successful release result.

## Agent rule

Use `ue-kb query --envelope --json` when the answer needs coverage or evidence
metadata. Use `ue-kb federated-query` (or MCP `ue_kb_federated_query`) when a
question may mix reusable UE guidance with project facts. Never compare
`raw_score` values across the public and project groups.
