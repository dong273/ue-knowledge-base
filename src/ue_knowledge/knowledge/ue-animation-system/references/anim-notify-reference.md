# Animation Notify Contracts

This page covers UE 5.7 notify callback surfaces and their evidence boundary.

## Instant notify

Derive an instant event from UAnimNotify. UE 5.7 exposes a callback overload that carries FAnimNotifyEventReference.

```cpp fragment
void Notify(
    USkeletalMeshComponent* MeshComp,
    UAnimSequenceBase* Animation,
    const FAnimNotifyEventReference& EventReference) override;
```

Treat MeshComp, Animation, and the event reference as callback inputs; validate pointers before reaching gameplay owners.

## Notify state

UAnimNotifyState defines begin, tick, and end callbacks. The event-reference overloads preserve context across the notify-state window.

```cpp fragment
void NotifyBegin(USkeletalMeshComponent* MeshComp, UAnimSequenceBase* Animation,
    float TotalDuration, const FAnimNotifyEventReference& EventReference) override;
void NotifyTick(USkeletalMeshComponent* MeshComp, UAnimSequenceBase* Animation,
    float FrameDeltaTime, const FAnimNotifyEventReference& EventReference) override;
void NotifyEnd(USkeletalMeshComponent* MeshComp, UAnimSequenceBase* Animation,
    const FAnimNotifyEventReference& EventReference) override;
```

## Branching and replay

Notify delivery depends on animation evaluation, montage or sequence position changes, branching behavior, and network execution. A callback implementation compiling does not prove a notify fired exactly once in every playback path.

## Gameplay ownership

Use notifies to signal a narrow event. Keep durable gameplay state and authority decisions in gameplay-owned objects. Cosmetic effects may remain local; authoritative damage or inventory mutation belongs on the server-owned path.

## Validation checklist

- Compile the selected overload against UE 5.7.4.
- Exercise normal playback, interruption, section jumps, and replay in a runtime test.
- Record visual or audible timing separately as human evidence.
