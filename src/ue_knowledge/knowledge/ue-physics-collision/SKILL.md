---
title: ue-physics-collision
description: Use when configuring UE 5.7 collision modes, responses, overlaps, traces, sweeps, or diagnosing collision state across Actor and PrimitiveComponent layers.
---

# UE Physics and Collision

Use this guide to reason about collision state without treating a single checkbox or function as the whole collision contract.

## Separate the collision layers

Collision depends on multiple layers: the Actor-level enable flag, each `UPrimitiveComponent` collision mode, object type and channel responses, collision geometry, and the query/simulation being performed. Inspect all relevant layers before declaring collision enabled or disabled.

## Actor-level gate

`AActor::SetActorEnableCollision` changes the Actor-level collision gate, and `GetActorEnableCollision` reads it back. This does not rewrite every component's `ECollisionEnabled` mode or response table.

## Component collision mode

`UPrimitiveComponent::SetCollisionEnabled` selects query/physics participation through `ECollisionEnabled::Type`. `SetCollisionProfileName` applies a named profile. A component still needs suitable geometry and responses for the intended interaction.

## Channel response

`SetCollisionResponseToChannel` changes one response, while `SetCollisionResponseToAllChannels` and `SetCollisionResponseToChannels` change broader response state. The other participant or query channel also matters.

```cpp fragment
// Fragment: Component and the project-defined channel are supplied elsewhere.
Component->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
Component->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
```

## Overlap and hit notifications

Overlap generation and blocking-hit notification are separate from the response table. `SetGenerateOverlapEvents` controls overlap-event generation for a primitive component; physics hit notification uses the body-instance notification surface. A blocking response does not automatically mean every desired event delegate will fire.

## Scene queries

`UWorld` exposes channel-based line traces, sweeps, and overlap queries. Use `FCollisionQueryParams` to ignore the querying Actor when appropriate, and inspect the returned `FHitResult` rather than assuming the first visible object is the collision result.

## Runtime mutation boundary

After changing collision at runtime, read back the Actor/component state and run the intended query or movement scenario. A state readback proves configuration, not that geometry, paired responses, or gameplay events are correct.

## Debugging checklist

- Identify the exact primitive component expected to collide.
- Record Actor gate, component mode, object type, and response to the tested channel.
- Distinguish overlap, blocking, query, and physics-simulation expectations.
- Check initial penetration and the movement/query shape.
- Use a focused Automation test for any behavior claimed as verified.

## Focused references

- [Trace patterns](references/trace-patterns.md)
- [Actor collision enable state](references/actor-collision-enable-state.md)
- [Collision channel setup](references/collision-channel-setup.md)
- [Ground penetration debugging](references/ground-penetration-debugging.md)
- [Runtime collision refresh](references/runtime-collision-refresh.md)
