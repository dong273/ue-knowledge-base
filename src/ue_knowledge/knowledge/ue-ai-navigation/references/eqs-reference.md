# EQS API Reference

Use EQS to generate, test, and score candidate items. This reference covers the public launch and result boundaries, not authoring claims about a particular query asset.

## Launch surface

`UEnvQueryManager::RunEQSQuery` accepts a world context, `UEnvQuery` template, querier, `EEnvQueryRunMode`, and wrapper class. It returns a `UEnvQueryInstanceBlueprintWrapper*` for the launched instance.

```cpp fragment
UEnvQueryInstanceBlueprintWrapper* Query = UEnvQueryManager::RunEQSQuery(
    WorldContext,
    QueryTemplate,
    Querier,
    EEnvQueryRunMode::SingleResult,
    UEnvQueryInstanceBlueprintWrapper::StaticClass());
```

## Run modes

`EEnvQueryRunMode` selects how many scored items are retained. Choose the mode from the consumer's contract; do not infer that `SingleResult` makes the query synchronous.

## Querier and context

The querier supplies world and owner context. Query contexts determine the origins or reference items used by generators and tests. Verify both independently when results are empty.

## Result boundary

Launching a query does not prove it completed or returned a usable item. Bind the wrapper's supported completion delegate, then inspect status and typed results in project code.

## Navigation interaction

Navigation-backed generators and path tests depend on valid navigation data for the queried world. A compiled query call does not prove NavMesh coverage or reachability.

## Review checklist

- Record query asset, querier, run mode, and wrapper type.
- Distinguish launch failure, execution failure, and an empty result set.
- Validate the result type before reading locations or actors.
- Use runtime evidence for the actual query asset and map.
