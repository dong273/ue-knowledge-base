---
description: Use for UE 5.7 Automation tests, assertions, latent commands, logs, profiling, and evidence-based debugging.
---

# UE Testing and Debugging

Define the claim first, then choose compile, Automation, log, artifact, or human evidence that can actually prove it.

## Automation test

Use Unreal Automation macros to register focused tests and return failure when an asserted contract is not met.

```cpp fragment
IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FExampleTest,
    "UEKnowledge.Example",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
```

## Assertions

Use `TestTrue`, `TestFalse`, and `TestEqual` for recoverable test assertions. Reserve `check` for invariants whose violation should stop execution.

```cpp fragment
TestTrue(TEXT("Object is valid"), IsValid(Object));
TestEqual(TEXT("Count"), ActualCount, ExpectedCount);
```

## Latent work

Use latent Automation commands or another explicit completion signal for asynchronous behavior. Scheduling work is not completion evidence.

## Logs

Capture the relevant category, severity, time window, and negative evidence. Absence of one expected error can support a narrow claim but cannot prove unrelated gameplay success.

## Profiling

Capture a reproducible workload and compare the same metric under the same configuration. A single editor frame is not a performance conclusion.

## Focused references

- [Automation test patterns](references/automation-test-patterns.md)
- [Profiling commands](references/profiling-commands.md)
- [Fresh PIE negative evidence](references/fresh-pie-negative-evidence.md)

## Verification boundary

Automatic results cannot replace visual, usability, discoverability, or independent-player evidence when the claim is about those outcomes.
