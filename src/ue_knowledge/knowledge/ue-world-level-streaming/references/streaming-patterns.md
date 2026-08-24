# World Streaming Selection Patterns

Select one primary ownership model, then define observable completion.

## Partitioned open world

Use World Partition when the map and content pipeline are authored for partitioning. Validate runtime partitions, streaming sources, generated data, dedicated-server policy, and cook output together.

## Authored sub-levels

Use `ULevelStreaming` or the GameplayStatics latent helpers when a persistent world owns known sub-level packages. Track loaded and visible state independently.

## Dynamic level instances

Use `ULevelStreamingDynamic::LoadLevelInstance` when the same level package needs runtime instances at chosen transforms. Store the returned streaming object in the owner responsible for later visibility and unload requests.

```cpp fragment
bool bRequestCreated = false;
ULevelStreamingDynamic* Instance = ULevelStreamingDynamic::LoadLevelInstance(
    WorldContext,
    LevelPackageName,
    Location,
    Rotation,
    bRequestCreated);
```

## Travel

Use map travel when the destination is a new world/session boundary rather than a streamed child of the current persistent world. Define state handoff and multiplayer authority before invoking travel.

## Completion evidence

Keep these observations separate:

- a request was accepted or a streaming object was created;
- the level reached a loaded state;
- the level reached a visible state;
- required actors initialized;
- gameplay declared the destination ready;
- the transition passed visual and usability review.

## Unload ownership

The owner that requests a streaming level or instance should retain enough identity to request unload and confirm the resulting state. Releasing a local pointer is not an unload operation.

## Validation checklist

- Test from a cooked target representative of release.
- Record loaded and visible state transitions.
- Exercise repeated load/unload or travel cycles.
- Measure memory and hitching on target hardware.
- Validate server/client visibility separately.
