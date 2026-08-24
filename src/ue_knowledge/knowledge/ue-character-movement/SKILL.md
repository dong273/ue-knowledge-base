---
title: ue-character-movement
description: Use when configuring ACharacter/UCharacterMovementComponent, movement modes, floor handling, LaunchCharacter, or a focused custom-movement extension in Unreal Engine 5.7.
---

# UE Character Movement

Use this guide to choose the movement owner, configure the built-in Character Movement Component (CMC), and identify when a custom movement mode needs additional prediction work.

## Choose the movement owner

`ACharacter` owns a capsule and `UCharacterMovementComponent`. A bare `APawn` can collect input with `AddMovementInput`, but the base pawn does not automatically turn that input into movement; a pawn movement component or project code must consume it.

## Feed movement input

The following is a fragment showing the input boundary, not a complete input component or character class:

```cpp fragment
// Fragment: call from a bound input handler on an APawn/ACharacter instance.
AddMovementInput(GetActorForwardVector(), AxisValue);
```

`AddMovementInput` accepts a world-space direction and scale. For `ACharacter`, CMC consumes the accumulated input during its movement update. Do not multiply the scale by frame delta before passing ordinary axis input to CMC.

## Configure built-in movement

Common CMC configuration surfaces include `MaxWalkSpeed`, `MaxAcceleration`, `BrakingDecelerationWalking`, `GroundFriction`, `AirControl`, `JumpZVelocity`, and `GravityScale`. Treat them as interacting parameters and measure acceleration, stopping distance, and air control separately.

## Use movement modes

`SetMovementMode` selects an `EMovementMode`; when the mode is `MOVE_Custom`, the second argument selects `CustomMovementMode`. Override `PhysCustom` in a CMC subclass for custom physics. A custom byte identifies a mode but does not implement its movement or network prediction.

## Move through collision-aware APIs

CMC and `UMovementComponent` provide collision-aware movement helpers such as `SafeMoveUpdatedComponent` and `SlideAlongSurface`. Directly setting the character transform bypasses the normal CMC movement path and is not an equivalent replacement for predicted locomotion.

## Launch a character

`ACharacter::LaunchCharacter` queues a launch velocity for the character movement update. Its two boolean parameters choose whether XY and Z replace or add to the existing velocity.

## Multiplayer boundary

Built-in Character movement has a client/server prediction path. New replicated custom modes, saved flags, or move payloads require focused `FSavedMove_Character` and network-move work; a local `PhysCustom` override alone does not prove multiplayer correctness.

## Verification checklist

- Confirm the pawn class and movement component that own locomotion.
- Record movement mode, velocity, acceleration, and floor state while reproducing a problem.
- Test walking, falling, transitions, collision, and network roles independently.
- Add a networked fixture before claiming a custom movement mode is predicted.

See `references/movement-pipeline.md` and `references/cmc-extension-patterns.md` for focused boundaries.
