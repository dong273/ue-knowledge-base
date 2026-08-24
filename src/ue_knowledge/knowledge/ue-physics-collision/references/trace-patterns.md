# Collision Trace Patterns

## Line trace by channel

`UWorld::LineTraceSingleByChannel` returns whether a blocking hit was found and writes an `FHitResult`.

```cpp fragment
// Fragment: World, start/end points, and channel selection are project-owned.
FHitResult Hit;
FCollisionQueryParams Params(SCENE_QUERY_STAT(InteractionTrace), false);
Params.AddIgnoredActor(OwnerActor);
const bool bBlocked = World->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params);
```

## Sweep with shape

Use `SweepSingleByChannel` when the query has volume. Build the shape with `FCollisionShape`, pass an explicit rotation, and interpret the returned blocking hit.

```cpp fragment
// Fragment: Radius and endpoints must be validated for the gameplay use case.
const FCollisionShape Shape = FCollisionShape::MakeSphere(Radius);
const bool bBlocked = World->SweepSingleByChannel(
    Hit, Start, End, FQuat::Identity, ECC_Visibility, Shape, Params);
```

## Ignore policy

`FCollisionQueryParams::AddIgnoredActor` and `AddIgnoredComponent` exclude known owners or components. Ignoring self is a query policy, not a substitute for fixing a wrong collision profile.

## Interpret the result

For a blocking hit, inspect `Hit.GetActor()`, `Hit.GetComponent()`, `Location`, `ImpactPoint`, `Normal`, `ImpactNormal`, `Time`, and `bStartPenetrating` as appropriate. Do not dereference hit objects without checking the query result and pointer validity.

## Single versus multi

Single queries answer the closest blocking result according to the query contract. Multi queries are appropriate when gameplay needs the ordered set of overlaps and blocking results; they require explicit filtering rather than selecting an arbitrary entry.

## Debug drawing boundary

Debug drawing can show the intended start, end, and shape, but it does not prove the collision response or selected object. Pair drawings with the actual `FHitResult` and state snapshot.
