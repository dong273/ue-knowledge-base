# Locomotion Data Setup

This page defines a minimal data path from gameplay movement to an animation graph.

## Owner lookup

UAnimInstance::TryGetPawnOwner returns the pawn currently associated with the animation instance when one is available. Guard the result before reading movement state.

```cpp fragment
const APawn* Pawn = AnimInstance->TryGetPawnOwner();
if (!Pawn)
{
    return;
}
```

## Velocity and speed

Read world velocity from the pawn or movement component. Compute planar speed only when vertical velocity should not drive the locomotion blend.

```cpp fragment
const FVector Velocity = Pawn->GetVelocity();
const float GroundSpeed = Velocity.Size2D();
```

## Character movement state

For ACharacter, UCharacterMovementComponent::IsFalling exposes the current falling-state query. Movement mode is gameplay state; the animation graph consumes a copy rather than owning the transition.

## Direction and local space

World velocity and actor rotation are different coordinate spaces. Convert deliberately before deriving forward or lateral intent, and test backwards and strafing motion.

## Update timing

Use the animation instance update hooks to refresh graph inputs. Cache only the object references and values whose lifetime is understood; preview and teardown can invalidate owner assumptions.

## Root motion

Root-motion extraction and character-movement application must be validated together. Enabling root motion in an asset does not by itself prove authoritative displacement or network correction.

## Validation checklist

- Compile owner, velocity, movement-mode, and root-motion APIs.
- Runtime-test transitions such as idle, acceleration, jump, fall, land, and interruption.
- Treat foot placement, sliding, and blend quality as human outcomes.
