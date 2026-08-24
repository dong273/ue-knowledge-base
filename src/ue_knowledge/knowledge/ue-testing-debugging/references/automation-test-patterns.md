# Automation Test Patterns

Keep each test focused on one contract and make failure output identify the broken boundary.

## Simple tests

A simple Automation test implements `RunTest` and returns whether execution completed without failed assertions.

```cpp fragment
bool FExampleTest::RunTest(const FString& Parameters)
{
    TestTrue(TEXT("Condition"), bCondition);
    return true;
}
```

## Complex tests

Use a complex test when one registered test enumerates named parameter cases through `GetTests`.

## Specifications

`BEGIN_DEFINE_SPEC` and `END_DEFINE_SPEC` provide behavior-style grouping while using the same Automation framework.

## Latent commands

Queue latent commands when the result arrives in later frames. Add a timeout and a diagnostic that distinguishes NotRun, timeout, and assertion failure.

```cpp fragment
ADD_LATENT_AUTOMATION_COMMAND(FWaitForConditionCommand());
```

## Expected errors

Use expected-error support only for diagnostics that are part of the contract. Match the intended pattern and occurrence count so unrelated errors remain visible.

## Test flags

Choose context and filter flags that match where the test can run. A test omitted by filtering is NotRun, not Success.

## Evidence export

Export test names, states, engine version, changelist, and report hashes. Only `Success` tests may produce runtime validation IDs.

## Verification boundary

A passing representative test covers only its declared behavior and claims. It does not validate every example in the same document.
