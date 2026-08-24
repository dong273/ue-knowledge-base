#!/usr/bin/env python3
"""Validate the sanitized UE 5.7 evidence manifest produced locally."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _report_path(root: Path, name: str) -> Path | None:
    candidate = Path(name)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    direct = root / candidate
    if direct.is_file():
        return direct
    # Older manifests recorded paths relative to the automation report
    # directory while keeping the evidence JSON one level above it.
    nested = root / "automation" / candidate
    return nested if nested.is_file() else None


def _default_registry(path: Path) -> Path | None:
    try:
        candidate = path.resolve().parents[2] / "fixture-registry.json"
    except IndexError:
        return None
    return candidate if candidate.is_file() else None


def check(
    path: Path,
    *,
    version: str = "5.7.4",
    changelist: int = 51494982,
    fixture_registry: Path | None = None,
    claim_ledger: Path | None = None,
) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read evidence: {type(exc).__name__}: {exc}"]
    errors: list[str] = []
    if payload.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    engine = payload.get("engine", {})
    if not isinstance(engine, dict):
        errors.append("engine must be an object")
        engine = {}
    if engine.get("version") != version:
        errors.append(f"engine version must be {version}")
    try:
        observed_changelist = int(engine.get("changelist", -1))
    except (TypeError, ValueError):
        observed_changelist = -1
    if observed_changelist != changelist:
        errors.append(f"engine changelist must be {changelist}")
    if payload.get("build_exit_code") != 0 or payload.get("automation_exit_code") != 0:
        errors.append("build and automation exit codes must be 0")
    reports_value = payload.get("reports")
    if payload.get("passed") is not True or not isinstance(reports_value, list) or not reports_value:
        errors.append("passed=true and at least one report are required")
    elif not all(isinstance(item, str) and item.strip() for item in reports_value):
        errors.append("reports must contain non-empty relative names")
    validation_ids = payload.get("validation_ids")
    if not isinstance(validation_ids, list) or not validation_ids or not all(
        isinstance(item, str) and item.strip() for item in validation_ids
    ):
        errors.append("validation_ids must contain at least one test identifier")

    compile_validations = payload.get("compile_validations")
    compile_ids: list[str] = []
    if compile_validations is not None:
        if not isinstance(compile_validations, list):
            errors.append("compile_validations must be a list")
        else:
            for item in compile_validations:
                if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                    errors.append("compile_validations entries must contain an id")
                    continue
                identifier = item["id"]
                if not _ID_RE.fullmatch(identifier):
                    errors.append(f"invalid compile validation id: {identifier}")
                if item.get("state", "Success") != "Success":
                    errors.append(f"compile validation did not pass: {identifier}")
                for field in ("symbols", "covers_claims"):
                    if field in item and not isinstance(item.get(field), list):
                        errors.append(f"compile validation {field} must be a list: {identifier}")
                fixture_hash = item.get("fixture_sha256")
                if fixture_hash is not None and not isinstance(fixture_hash, str):
                    errors.append(f"fixture hash must be a string: {identifier}")
                if fixture_hash is not None and not _SHA256_RE.fullmatch(fixture_hash):
                    errors.append(f"fixture hash must be sha256: {identifier}")
                compile_ids.append(identifier)

    tests = payload.get("tests")
    test_ids: list[str] = []
    if tests is not None:
        if not isinstance(tests, list):
            errors.append("tests must be a list")
        else:
            for item in tests:
                if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                    errors.append("tests entries must contain an id")
                    continue
                identifier = item["id"]
                if not _ID_RE.fullmatch(identifier):
                    errors.append(f"invalid automation test id: {identifier}")
                if item.get("state") != "Success":
                    errors.append(f"automation test did not pass: {identifier}")
                for field in ("assertions", "covers_claims"):
                    if field in item and not isinstance(item.get(field), list):
                        errors.append(f"automation test {field} must be a list: {identifier}")
                for field in ("warnings", "errors"):
                    value = item.get(field, 0)
                    if not isinstance(value, int) or value < 0:
                        errors.append(f"automation test {field} must be a non-negative integer: {identifier}")
                if isinstance(item.get("warnings", 0), int) and item.get("warnings", 0) > 0:
                    errors.append(f"automation test contains warnings: {identifier}")
                if isinstance(item.get("errors", 0), int) and item.get("errors", 0) > 0:
                    errors.append(f"automation test contains errors: {identifier}")
                test_ids.append(identifier)

    detailed_ids = set(compile_ids + test_ids)
    if len(compile_ids + test_ids) != len(detailed_ids):
        errors.append("compile/test validation ids must be unique")
    if (compile_validations is not None or tests is not None) and not detailed_ids:
        errors.append("at least one detailed compile or automation validation is required")
    if isinstance(validation_ids, list) and (compile_validations is not None or tests is not None):
        if set(validation_ids) != detailed_ids:
            errors.append("validation_ids must equal the detailed compile/test ids")

    expected_failure_results = payload.get("expected_failures", [])
    expected_failure_result_ids: set[str] = set()
    if not isinstance(expected_failure_results, list):
        errors.append("expected_failures must be a list")
        expected_failure_results = []
    for item in expected_failure_results:
        identifier = item.get("id") if isinstance(item, dict) else None
        if not isinstance(identifier, str) or not identifier.strip():
            errors.append("expected failure results require id")
            continue
        if identifier in expected_failure_result_ids or identifier in detailed_ids:
            errors.append(f"duplicate expected failure result id: {identifier}")
        expected_failure_result_ids.add(identifier)
        if item.get("state") != "ExpectedFailure" or item.get("matched") is not True:
            errors.append(f"expected failure result did not match: {identifier}")
        exit_code = item.get("exit_code")
        if not isinstance(exit_code, int) or exit_code == 0:
            errors.append(f"expected failure result must have a non-zero exit code: {identifier}")
        diagnostic = item.get("diagnostic")
        if not isinstance(diagnostic, str) or not diagnostic.strip():
            errors.append(f"expected failure result requires a diagnostic: {identifier}")
        fixture_hash = item.get("fixture_sha256")
        if not isinstance(fixture_hash, str) or not _SHA256_RE.fullmatch(fixture_hash):
            errors.append(f"expected failure fixture hash must be sha256: {identifier}")

    fixture_hashes = payload.get("fixture_hashes")
    if fixture_hashes is not None:
        if not isinstance(fixture_hashes, dict):
            errors.append("fixture_hashes must be an object")
        else:
            for identifier, digest in fixture_hashes.items():
                if not _ID_RE.fullmatch(str(identifier)) or not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
                    errors.append(f"invalid fixture hash entry: {identifier}")

    registry_hash = payload.get("fixture_registry_sha256")
    if registry_hash is not None and (not isinstance(registry_hash, str) or not _SHA256_RE.fullmatch(registry_hash)):
        errors.append("fixture_registry_sha256 must be sha256")

    report_hashes = payload.get("report_sha256")
    if report_hashes is not None:
        if not isinstance(report_hashes, dict):
            errors.append("report_sha256 must be an object")
        else:
            reports = reports_value if isinstance(reports_value, list) else []
            if set(report_hashes) != set(reports):
                errors.append("report_sha256 keys must match reports")
            for name, digest in report_hashes.items():
                if not isinstance(name, str) or not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
                    errors.append(f"invalid report hash entry: {name}")
                report_path = _report_path(path.parent, name) if isinstance(name, str) else None
                if report_path is None:
                    errors.append(f"report file is missing or unsafe: {name}")
                elif hashlib.sha256(report_path.read_bytes()).hexdigest() != digest:
                    errors.append(f"report hash mismatch: {name}")

    # When the Automation index is present, detailed test IDs/states must be
    # a projection of that report rather than caller-supplied assertions.
    if isinstance(tests, list) and report_hashes:
        report_index = next(
            (_report_path(path.parent, name) for name in reports_value or [] if str(name).endswith("index.json")),
            None,
        )
        if report_index is not None:
            try:
                report_payload = json.loads(report_index.read_text(encoding="utf-8-sig"))
                report_tests = report_payload.get("tests", [])
                report_by_id = {
                    item.get("fullTestPath"): item
                    for item in report_tests
                    if isinstance(item, dict) and item.get("fullTestPath")
                }
                for item in tests:
                    identifier = item.get("id") if isinstance(item, dict) else None
                    observed = report_by_id.get(identifier)
                    if observed is None:
                        errors.append(f"automation test is absent from report: {identifier}")
                    elif observed.get("state") != item.get("state"):
                        errors.append(f"automation test state mismatch: {identifier}")
                if payload.get("passed") is True and any(
                    isinstance(item, dict) and item.get("state") != "Success" for item in report_tests
                ):
                    errors.append("passed evidence contains a non-success Automation report test")
            except (OSError, json.JSONDecodeError, AttributeError, TypeError) as exc:
                errors.append(f"cannot parse Automation report: {type(exc).__name__}: {exc}")

    registry_path = fixture_registry or _default_registry(path)
    validation_coverage: dict[str, set[str]] = {}
    registry_claim_ids: set[str] = set()
    if registry_path is not None and payload.get("fixture_hashes") is not None:
        try:
            registry_payload = json.loads(registry_path.read_text(encoding="utf-8"))
            registry_digest = hashlib.sha256(registry_path.read_bytes()).hexdigest()
            if payload.get("fixture_registry_sha256") != registry_digest:
                errors.append("fixture registry hash mismatch")
            registry_engine = registry_payload.get("engine", {})
            if registry_engine.get("version") != version or int(registry_engine.get("changelist", -1)) != changelist:
                errors.append("fixture registry engine version/changelist mismatch")
            if registry_payload.get("schema_version") != 2:
                errors.append("fixture registry schema_version must be 2")
            expected_hashes = {}
            registry_fixture_ids = set()
            for fixture in registry_payload.get("fixtures", []):
                identifier = fixture.get("id") if isinstance(fixture, dict) else None
                source = fixture.get("source") if isinstance(fixture, dict) else None
                if not isinstance(identifier, str) or not isinstance(source, str):
                    errors.append("fixture registry entries require id and source")
                    continue
                if identifier in registry_fixture_ids:
                    errors.append(f"duplicate fixture registry id: {identifier}")
                registry_fixture_ids.add(identifier)
                for field in ("symbols", "covers_claims"):
                    if not isinstance(fixture.get(field), list):
                        errors.append(f"fixture registry {field} must be a list: {identifier}")
                if isinstance(fixture.get("covers_claims"), list):
                    validation_coverage[identifier] = {
                        item for item in fixture["covers_claims"] if isinstance(item, str)
                    }
                    registry_claim_ids.update(validation_coverage[identifier])
                source_path = Path(source)
                if source_path.is_absolute() or ".." in source_path.parts:
                    errors.append(f"fixture source is unsafe: {source}")
                    continue
                project_candidate = registry_path.parent / "UEKnowledgeValidation" / source_path
                fixture_path = project_candidate if project_candidate.is_file() else registry_path.parent / source_path
                if not fixture_path.is_file():
                    errors.append(f"fixture source is missing: {source}")
                    continue
                expected_hashes[identifier] = hashlib.sha256(fixture_path.read_bytes()).hexdigest()
            if payload.get("fixture_hashes") != expected_hashes:
                errors.append("fixture hashes do not match the fixture registry sources")
            detailed_hashes = {
                item.get("id"): item.get("fixture_sha256")
                for item in compile_validations or []
                if isinstance(item, dict) and item.get("id")
            }
            if detailed_hashes and detailed_hashes != expected_hashes:
                errors.append("compile validation fixture hashes do not match registry sources")
            registry_by_fixture = {
                fixture.get("id"): fixture
                for fixture in registry_payload.get("fixtures", [])
                if isinstance(fixture, dict) and fixture.get("id")
            }
            for item in compile_validations or []:
                if not isinstance(item, dict) or not item.get("id"):
                    continue
                registered = registry_by_fixture.get(item["id"])
                if registered is not None:
                    if item.get("symbols", []) != registered.get("symbols", []):
                        errors.append(f"compile validation symbols do not match registry: {item['id']}")
                    if item.get("covers_claims", []) != registered.get("covers_claims", []):
                        errors.append(f"compile validation claim coverage does not match registry: {item['id']}")
            registry_tests = registry_payload.get("tests", [])
            registry_test_ids: set[str] = set()
            if not isinstance(registry_tests, list):
                errors.append("fixture registry tests must be a list")
            else:
                for test in registry_tests:
                    identifier = test.get("id") if isinstance(test, dict) else None
                    if not isinstance(identifier, str) or not identifier.strip():
                        errors.append("fixture registry test entries require id")
                        continue
                    if identifier in registry_test_ids:
                        errors.append(f"duplicate registry test id: {identifier}")
                    registry_test_ids.add(identifier)
                    for field in ("assertions", "covers_claims"):
                        if not isinstance(test.get(field), list):
                            errors.append(f"fixture registry test {field} must be a list: {identifier}")
                    if isinstance(test.get("covers_claims"), list):
                        validation_coverage[identifier] = {
                            item for item in test["covers_claims"] if isinstance(item, str)
                        }
                        registry_claim_ids.update(validation_coverage[identifier])
                if test_ids and set(test_ids) != registry_test_ids:
                    errors.append("automation test ids must equal registry test ids")
                registry_by_test = {
                    test.get("id"): test
                    for test in registry_tests
                    if isinstance(test, dict) and test.get("id")
                }
                for item in tests or []:
                    if not isinstance(item, dict) or not item.get("id"):
                        continue
                    registered = registry_by_test.get(item["id"])
                    if registered is not None:
                        if item.get("assertions", []) != registered.get("assertions", []):
                            errors.append(f"automation test assertions do not match registry: {item['id']}")
                        if item.get("covers_claims", []) != registered.get("covers_claims", []):
                            errors.append(f"automation test claim coverage does not match registry: {item['id']}")
            expected_failures = registry_payload.get("expected_failures", [])
            if not isinstance(expected_failures, list):
                errors.append("fixture registry expected_failures must be a list")
                expected_failures = []
            expected_failure_ids: set[str] = set()
            registry_expected_failures: dict[str, dict] = {}
            for probe in expected_failures:
                identifier = probe.get("id") if isinstance(probe, dict) else None
                diagnostic = probe.get("diagnostic") if isinstance(probe, dict) else None
                if not isinstance(identifier, str) or not identifier.strip():
                    errors.append("expected failure entries require id")
                    continue
                if identifier in expected_failure_ids or identifier in registry_fixture_ids or identifier in registry_test_ids:
                    errors.append(f"duplicate validation id across registry: {identifier}")
                expected_failure_ids.add(identifier)
                registry_expected_failures[identifier] = probe
                if not isinstance(diagnostic, str) or not diagnostic.strip():
                    errors.append(f"expected failure requires a diagnostic: {identifier}")
                if identifier in detailed_ids or identifier in set(validation_ids or []):
                    errors.append(f"expected failure must not be exported as a success validation: {identifier}")
                source = probe.get("source") if isinstance(probe, dict) else None
                project = probe.get("project") if isinstance(probe, dict) else None
                target = probe.get("target") if isinstance(probe, dict) else None
                if not all(isinstance(value, str) and value.strip() for value in (source, project, target)):
                    errors.append(f"expected failure requires project, target, and source: {identifier}")
            if expected_failure_ids != expected_failure_result_ids:
                errors.append("expected failure result ids must equal registry ids")
            result_by_id = {
                item.get("id"): item
                for item in expected_failure_results
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            }
            validation_root = registry_path.parent
            for identifier, probe in registry_expected_failures.items():
                result = result_by_id.get(identifier)
                if result is None:
                    continue
                if result.get("diagnostic") != probe.get("diagnostic"):
                    errors.append(f"expected failure diagnostic does not match registry: {identifier}")
                source = probe.get("source")
                source_path = Path(source) if isinstance(source, str) else Path(".")
                if source_path.is_absolute() or ".." in source_path.parts:
                    errors.append(f"expected failure source is unsafe: {identifier}")
                    continue
                source_file = validation_root / source_path
                if not source_file.is_file():
                    errors.append(f"expected failure source is missing: {identifier}")
                elif result.get("fixture_sha256") != hashlib.sha256(source_file.read_bytes()).hexdigest():
                    errors.append(f"expected failure fixture hash mismatch: {identifier}")
        except (OSError, json.JSONDecodeError, AttributeError, TypeError, ValueError) as exc:
            errors.append(f"cannot validate fixture registry: {type(exc).__name__}: {exc}")

    # A successful fixture/test is not blanket evidence.  When a v2 claim
    # ledger is supplied, every terminal claim that requires a compile or
    # runtime result must be named by a matching registry entry.  Pending
    # claims remain the responsibility of the corpus audit and are not
    # promoted merely because a validation project happened to pass.
    if claim_ledger is not None:
        if registry_path is None:
            errors.append("claim ledger validation requires a fixture registry")
        try:
            ledger_payload = json.loads(claim_ledger.read_text(encoding="utf-8"))
            if ledger_payload.get("schema_version") != 2:
                errors.append("claim ledger schema_version must be 2")
            known_claims: dict[str, dict] = {}
            for document in (ledger_payload.get("documents") or {}).values():
                if not isinstance(document, dict):
                    continue
                for claim in document.get("claims", []):
                    if isinstance(claim, dict) and isinstance(claim.get("claim_id"), str):
                        known_claims[claim["claim_id"]] = claim
            unknown_registry_claims = sorted(registry_claim_ids - set(known_claims))
            for claim_id_value in unknown_registry_claims:
                errors.append(f"fixture registry covers unknown claim: {claim_id_value}")
            compile_id_set = set(compile_ids)
            test_id_set = set(test_ids)
            terminal_states = {"verified", "rewritten", "excluded"}
            for claim_id_value, claim in known_claims.items():
                if claim.get("review_state") not in terminal_states and claim.get("status") not in terminal_states:
                    continue
                requirements = set(claim.get("requirements") or [])
                linked_ids = {
                    item for item in (claim.get("validation_ids") or []) if isinstance(item, str)
                }
                if "compile" in requirements:
                    linked_compile_ids = linked_ids & compile_id_set
                    if not any(
                        claim_id_value in validation_coverage.get(identifier, set())
                        for identifier in linked_compile_ids
                    ):
                        errors.append(f"compile validation registry does not cover claim: {claim_id_value}")
                if "runtime" in requirements:
                    linked_test_ids = linked_ids & test_id_set
                    if not any(
                        claim_id_value in validation_coverage.get(identifier, set())
                        for identifier in linked_test_ids
                    ):
                        errors.append(f"automation registry does not cover claim: {claim_id_value}")
        except (OSError, json.JSONDecodeError, AttributeError, TypeError, ValueError) as exc:
            errors.append(f"cannot validate claim ledger: {type(exc).__name__}: {exc}")

    serialized = json.dumps(payload, ensure_ascii=False)
    if re.search(r"[A-Za-z]:[\\/]", serialized) or re.search(r"(?:^|[\\/])Users[\\/]", serialized, re.IGNORECASE):
        errors.append("evidence must not contain an absolute drive path")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check a UE 5.7 evidence manifest")
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--fixture-registry", type=Path, help="fixture registry used to cross-check source hashes")
    parser.add_argument("--claim-ledger", type=Path, help="schema-v2 claim ledger used to cross-check direct coverage")
    args = parser.parse_args(argv)
    errors = check(args.evidence, fixture_registry=args.fixture_registry, claim_ledger=args.claim_ledger)
    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        return 1
    print(f"[PASS] sanitized UE 5.7 evidence: {args.evidence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
