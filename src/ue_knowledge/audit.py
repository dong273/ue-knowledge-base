"""CLI-facing corpus audit adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .corpus_audit import audit_ledger, scan_corpus
from .metadata import audit_corpus


class TrustAudit:
    """Single façade for corpus inventory, claim audit, and release summary.

    The implementation modules remain independently testable, but callers use
    this seam so scanning, evidence validation, and document-level aggregation
    cannot silently drift into separate policies.
    """

    def __init__(
        self,
        source: Path,
        *,
        provenance: str | Path | None = None,
        scope: str = "public",
        source_registry: str | Path | None = None,
        evidence_manifest: str | Path | None = None,
        claim_ledger: str | Path | None = None,
        allow_pending: bool = False,
    ) -> None:
        self.source = Path(source)
        self.provenance = provenance
        self.scope = scope
        self.source_registry = source_registry
        self.evidence_manifest = evidence_manifest
        self.claim_ledger = claim_ledger
        self.allow_pending = allow_pending

    def scan(self) -> dict[str, Any]:
        """Return the deterministic schema-v2 corpus inventory."""
        return scan_corpus(self.source)

    def claims(self) -> dict[str, Any]:
        """Audit the claim ledger directly when a ledger path is configured."""
        if self.claim_ledger is None:
            raise ValueError("claim_ledger is required for a claim audit")
        return audit_ledger(
            self.source,
            Path(self.claim_ledger),
            evidence_manifest=Path(self.evidence_manifest) if self.evidence_manifest else None,
        )

    def run(self) -> dict[str, Any]:
        """Return the release-facing document and claim audit envelope."""
        return audit_corpus(
            self.source,
            provenance_path=self.provenance,
            scope=self.scope,
            source_registry=self.source_registry,
            evidence_manifest=self.evidence_manifest,
            claim_ledger=self.claim_ledger,
            allow_pending=self.allow_pending,
        )


def audit_payload_for_cli(
    source: Path,
    *,
    provenance: str | Path | None = None,
    scope: str = "public",
    source_registry: str | Path | None = None,
    evidence_manifest: str | Path | None = None,
    claim_ledger: str | Path | None = None,
    allow_pending: bool = False,
) -> dict[str, Any]:
    """Adapt argparse naming to the core audit API for CLI and integrations.

    Keeping this boundary explicit lets the CLI remain stable if the core
    audit function later gains richer programmatic options.
    """
    return TrustAudit(
        source,
        provenance=provenance,
        scope=scope,
        source_registry=source_registry,
        evidence_manifest=evidence_manifest,
        claim_ledger=claim_ledger,
        allow_pending=allow_pending,
    ).run()
