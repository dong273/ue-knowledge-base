# Actor Lifecycle Reference

This reference records lifecycle contracts, not a universal timestamp trace.

Source: the class documentation and virtual declarations in
`Engine/Source/Runtime/Engine/Classes/GameFramework/Actor.h`.

## Initialization order

For spawned actors, construction and component initialization occur before
`BeginPlay`. Level-loaded actors have an additional loading path, so code should rely
on documented hooks rather than assuming the same constructor history.

The documented high-level order is: component registration, actor initialization,
`PostInitializeComponents`, then `BeginPlay` when play begins. Exact editor and
network timing still depends on world state.

## Constructor

Use the native constructor for default subobjects and class defaults. World-dependent
lookups and gameplay side effects do not belong there because a gameplay world may
not exist.

## PostInitializeComponents

`PostInitializeComponents` runs after actor components have been initialized. It is a
suitable hook for actor/component wiring that must exist before play, while gameplay
that depends on the match or other actors normally belongs in `BeginPlay`.

## BeginPlay

`BeginPlay` marks participation in play. It does not guarantee that every unrelated
actor has already run `BeginPlay`, so cross-actor dependencies need explicit
coordination.

```cpp fragment
void AExampleActor::BeginPlay()
{
    Super::BeginPlay();
}
```

## EndPlay and destruction

`EndPlay` receives an `EEndPlayReason::Type` and can run for destruction, level
transition, end of PIE, or application shutdown. Release delegates, timers, and other
external registrations here. Do not treat `Destroyed` as the only cleanup path.

```cpp fragment
void AExampleActor::EndPlay(const EEndPlayReason::Type Reason)
{
    Super::EndPlay(Reason);
}
```

## Evidence boundary

The header documents hook contracts and ordering. A specific game's cross-actor
ordering, replication arrival, or visual readiness needs a focused runtime test.
