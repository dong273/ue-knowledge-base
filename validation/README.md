# UE 5.7 validation gate

This is a source-only Unreal project used to validate API and runtime claims
from the public corpus. It contains no project assets, project paths, or private
evidence. The registry currently contains fourteen domain fixtures (including
RPC, GAS, Build.cs, actor/component, C++ reflection, data assets,
gameplay-framework, input/UI, and collision surfaces), and
the project runs five Automation tests. A fixture proves only the symbols it
actually compiles; it is not blanket coverage for an entire document.

Run the local gate from PowerShell 7:

```powershell
pwsh -NoProfile -File scripts/validate_ue57.ps1 -EngineRoot <ENGINE_ROOT>
python scripts/check_ue57_evidence.py validation/artifacts/ue57/ue57-validation-evidence.json --fixture-registry validation/fixture-registry.json --claim-ledger validation/corpus-audit.json
# Optional: validate sidecar and claim-level links against the sanitized report.
ue-kb audit-corpus --scope public --evidence-manifest validation/artifacts/ue57/ue57-validation-evidence.json --claim-ledger validation/corpus-audit.json --allow-pending --json
```

The script requires UE 5.7.4 / Changelist 51494982, builds the editor target,
runs `UEKnowledgeValidation` Automation tests with `-NullRHI`, and writes a
sanitized evidence manifest under `validation/artifacts/ue57/`. The checker
cross-validates the manifest against the Automation report and fixture source
hashes when those artifacts are present. The generated artifact is local
evidence; it is not a substitute for human visual or first-player acceptance.

`validation/fixture-registry.json` (schema v2) is the source-of-truth list of
compile fixtures and Automation tests. A successful clean UBT build hashes
every listed source into the sanitized manifest and copies the declared
`symbols`, `assertions`, and direct `covers_claims` mappings into the result.
The registry is not a claim that a fixture covers unrelated APIs. Each listed
source also carries a human-readable `Validation ID` comment so reviewers can
cross-check the registry without relying on filenames alone. A terminal claim
in the schema-v2 ledger is accepted only when its linked compile/runtime ID
names that claim in this registry.

`expected_failures` contains the missing-GameplayAbilities dependency probe.
The checker requires its explicit C1083 diagnostic and rejects exporting that
probe as a successful validation ID.

`validation/fixtures/ue57-validation-evidence.json` is a checked-in schema,
version, ID, and fixture-hash contract used by the Python CI job. Its success
states are structural test data, not the result of a CI Unreal build, and it
must never be used as release evidence; the local artifact above is the
authoritative run output.
