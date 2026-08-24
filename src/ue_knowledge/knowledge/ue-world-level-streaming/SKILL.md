---
description: Use for UE 5.7 World Partition, ULevelStreaming state, latent stream-level requests, dynamic level instances, travel boundaries, or per-world subsystems. Read the patterns reference before choosing a streaming mechanism.
---

# UE World and Level Streaming

Choose the world-loading mechanism before writing code; World Partition, sub-level streaming, dynamic instances, and travel have different ownership contracts.

## World Partition

`UWorldPartitionSubsystem` is a tickable world subsystem that exposes the World Partition runtime boundary for a world. World Partition streaming depends on the partitioned world, runtime partitions, streaming sources, and generated data.

## Traditional level streaming

`ULevelStreaming` represents a streaming-level object. `GetLevelStreamingState` returns its current `ELevelStreamingState`; desired loaded and visible flags are separate from the observed current state.

```cpp fragment
const ELevelStreamingState State = StreamingLevel->GetLevelStreamingState();
StreamingLevel->SetShouldBeLoaded(true);
StreamingLevel->SetShouldBeVisible(true);
```

## Latent requests

`UGameplayStatics::LoadStreamLevel` and `UnloadStreamLevel` use latent action information. A function return does not mean the level is already loaded or visible.

```cpp fragment
UGameplayStatics::LoadStreamLevel(
    WorldContext,
    LevelName,
    true,
    false,
    LatentInfo);
```

## Dynamic instances

`ULevelStreamingDynamic::LoadLevelInstance` creates a runtime streaming instance from a level package and transform. Treat the success flag and returned streaming object as request-creation evidence; observe later state for readiness.

## Travel boundary

Map travel replaces or changes world ownership rather than merely toggling one streaming level. Persist cross-world state in a lifetime owner chosen by the project, and validate server/client travel separately.

## World subsystem lifetime

`UWorldSubsystem` belongs to a `UWorld`; it is initialized and deinitialized with that world. Use it for per-world services, not process-global persistence.

## Focused reference

See [Streaming patterns](references/streaming-patterns.md) for selection and completion evidence.

## Verification boundary

Compile evidence proves UE 5.7 public types and calls. Cooked content, generated World Partition data, loading order, network visibility, memory budget, and visible transitions require target-build runtime or human evidence.
