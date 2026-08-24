# CMC Extension Patterns

These are API-focused fragments for UE 5.7. They are not a complete production movement mode or a network-prediction implementation.

## Install a CMC subclass

`ACharacter` creates its movement component as a default subobject. A character constructor can replace the default component class through the object initializer:

```cpp fragment
// Fragment: constructor declaration/definitions and generated header are omitted.
AMyCharacter::AMyCharacter(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer.SetDefaultSubobjectClass<UMyCharacterMovementComponent>(
        ACharacter::CharacterMovementComponentName))
{
}
```

The replacement type must derive from `UCharacterMovementComponent`.

## Enter a custom mode

Use `SetMovementMode(MOVE_Custom, CustomModeByte)` to enter a project-defined mode. Keep the byte mapping stable anywhere it is serialized or sent across the network.

```cpp fragment
// Fragment: EMyCustomMode and ownership checks are project-specific.
Movement->SetMovementMode(MOVE_Custom, static_cast<uint8>(EMyCustomMode::Climb));
```

## Implement PhysCustom

Override `PhysCustom(float DeltaTime, int32 Iterations)` and dispatch only the modes owned by the subclass. Delegate unknown modes to `Super::PhysCustom`.

```cpp fragment
// Fragment: PhysClimb must calculate velocity and collision-aware movement.
void UMyCharacterMovementComponent::PhysCustom(float DeltaTime, int32 Iterations)
{
    if (CustomMovementMode == static_cast<uint8>(EMyCustomMode::Climb))
    {
        PhysClimb(DeltaTime, Iterations);
        return;
    }
    Super::PhysCustom(DeltaTime, Iterations);
}
```

## Preserve collision handling

Custom physics normally moves `UpdatedComponent` through movement-component helpers and examines `FHitResult` instead of teleporting the owner.

```cpp fragment
// Fragment: Delta, rotation policy, and impact response are intentionally incomplete.
FHitResult Hit;
SafeMoveUpdatedComponent(Delta, UpdatedComponent->GetComponentQuat(), true, Hit);
if (Hit.IsValidBlockingHit())
{
    SlideAlongSurface(Delta, 1.0f - Hit.Time, Hit.Normal, Hit, true);
}
```

## Prediction is a separate deliverable

If a custom mode adds input flags or data that the server must replay, extend the appropriate saved-move and network-move structures and validate them in a multi-process test. Do not label a mode “network ready” from a standalone compile or single-player PIE run.
