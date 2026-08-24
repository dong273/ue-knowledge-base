---
description: Use for UE 5.7 animation instances, montages, skeletal-mesh animation ownership, locomotion data, root motion, and animation notify contracts.
---

# UE Animation System

Use this workflow to separate animation requests, graph evaluation, movement state, and visible results.

## Runtime owners

USkeletalMeshComponent owns the skeletal animation component state. UAnimInstance exposes montage control and animation-update hooks. Character translation remains owned by the movement or root-motion path, not by a state-machine label alone.

## Montage requests

UAnimInstance::Montage_Play starts a montage request and returns a duration-style value according to EMontagePlayReturnType. Use Montage_IsPlaying to inspect current montage state and Montage_Stop to request a stop.

```cpp fragment
const float Result = AnimInstance->Montage_Play(Montage);
const bool bPlaying = AnimInstance->Montage_IsPlaying(Montage);
AnimInstance->Montage_Stop(0.2f, Montage);
```

An accepted play call is not proof that the intended slot, section, blend, or visible pose was correct.

## Locomotion inputs

Read stable gameplay state from the owning pawn and movement component, then copy the values needed by the animation graph. TryGetPawnOwner can be null during initialization, preview, or teardown.

## Root-motion boundary

UAnimInstance::SetRootMotionMode selects how extracted root motion is handled. Asset root-motion settings, montage usage, movement mode, and network authority remain separate conditions.

## Threading boundary

NativeThreadSafeUpdateAnimation is a thread-safe update hook. Keep UObject mutation, world queries, spawning, and other game-thread-only work outside that hook unless the called API explicitly supports worker-thread use.

## Focused references

- [Anim Notify contracts](references/anim-notify-reference.md)
- [Locomotion setup](references/locomotion-setup.md)

## Verification boundary

Compile the C++ surface against UE 5.7.4. Use runtime tests for state transitions. Pose quality, foot sliding, blend quality, and visual timing require human observation.
