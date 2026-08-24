# Mass Entity Query Patterns

Use these UE 5.7 boundaries when implementing Mass processors.

## Declare requirements

Build an `FMassEntityQuery` from the fragments and tags the processor actually reads or writes. Access mode and presence rules are part of the query contract.

```cpp fragment
EntityQuery.AddRequirement<FTransformFragment>(EMassFragmentAccess::ReadOnly);
EntityQuery.AddRequirement<FMassVelocityFragment>(EMassFragmentAccess::ReadWrite);
```

## Iterate chunks

Use the UE 5.7 `ForEachEntityChunk(FMassExecutionContext&, ...)` overload. Read fragment arrays from the callback context and iterate `GetNumEntities()` for the current chunk.

```cpp fragment
EntityQuery.ForEachEntityChunk(Context, [](FMassExecutionContext& ChunkContext)
{
    const auto Locations = ChunkContext.GetFragmentView<FTransformFragment>();
    auto Velocities = ChunkContext.GetMutableFragmentView<FMassVelocityFragment>();
    for (int32 Index = 0; Index < ChunkContext.GetNumEntities(); ++Index)
    {
        // fragment-only batch work
    }
});
```

## Defer structural changes

Adding/removing fragments or destroying entities changes archetypes. Queue those operations through deferred command facilities while a query is executing.

## Schedule processors

Set the processing phase and execution-order dependencies from actual data flow. A textual before/after declaration still needs a runtime schedule inspection when ordering is release-critical.

## Parallel boundary

`ParallelForEachEntityChunk` is available with UE 5.7 execution flags. Parallel work is valid only when declared access and shared state are thread-safe; defer commands through the supported per-job command-buffer behavior.

## Validation checklist

- Confirm every fragment view has a matching query requirement.
- Match read/write access to the code path.
- Use the non-deprecated UE 5.7 query overloads.
- Queue structural changes.
- Measure chunk count and processor time in the target workload.
