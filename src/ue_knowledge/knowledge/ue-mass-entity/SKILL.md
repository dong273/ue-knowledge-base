---
description: Use for UE 5.7 Mass Entity fragments, tags, archetypes, entity handles, queries, processors, deferred commands, or Mass StateTree ownership. Read the focused references for query patterns or fragment categories.
---

# UE Mass Entity

Mass stores entities in archetypes and processes matching chunks. Design from data requirements and batch execution rather than Actor-style per-object ticks.

## Core types

- `FMassEntityHandle` identifies an entity.
- `FMassFragment` is per-entity data.
- `FMassTag` is presence-only entity state.
- `FMassChunkFragment` stores per-chunk data.
- `FMassSharedFragment` and `FMassConstSharedFragment` hold archetype-shared data.
- `FMassEntityManager` owns entities and archetypes.

See [Fragment reference](references/mass-fragment-reference.md) for category selection.

## Query contract

`FMassEntityQuery` declares fragment/tag/subsystem requirements and iterates matching chunks. In UE 5.7, the current `ForEachEntityChunk` overload receives an `FMassExecutionContext` without the deprecated `FMassEntityManager` parameter.

```cpp fragment
EntityQuery.ForEachEntityChunk(Context, [](FMassExecutionContext& Context)
{
    const TConstArrayView<FTransformFragment> Transforms =
        Context.GetFragmentView<FTransformFragment>();
});
```

## Processor contract

`UMassProcessor` defines queries in `ConfigureQueries` and performs work in `Execute`. `ProcessingPhase`, execution groups, and before/after dependencies control scheduling.

## Structural changes

Archetype-changing operations must respect Mass execution rules. During query execution, enqueue structural changes through the execution context or the manager's deferred command buffer instead of mutating the iterated archetype directly.

## Entity lifetime

`FMassEntityManager::CreateEntity` and `DestroyEntity` are manager surfaces. Validate a handle before access; an index without its serial/generation information is not an entity identity.

## Focused references

- [Mass patterns](references/mass-entity-patterns.md) covers queries, processors, and deferred changes.
- [Fragment reference](references/mass-fragment-reference.md) covers fragment and tag categories.
- `ue-state-trees/references/state-tree-mass-integration.md` covers MassAIBehavior.

## Verification boundary

Compile evidence proves types and current signatures. Archetype composition, processor order, thread safety, entity counts, and performance require project-specific Mass runtime evidence.
