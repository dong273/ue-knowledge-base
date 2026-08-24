---
title: ue-actor-component-architecture
description: Use when deciding Actor and component ownership, lifecycle, attachment, registration, or composition in Unreal Engine. See references/actor-lifecycle.md and references/component-types.md.
---

# UE Actor-Component Architecture

Use this guide to decide ownership and lifecycle before writing gameplay logic.

## Choose the owner

An `AActor` is a world object with an actor lifecycle and optional replication. A
`UActorComponent` adds reusable behavior to an owner. A `USceneComponent` adds a
transform and attachment relationship. A `UPrimitiveComponent` adds render and
collision surfaces.

Source: `Engine/Source/Runtime/Engine/Classes/GameFramework/Actor.h` and
`Engine/Source/Runtime/Engine/Classes/Components/ActorComponent.h`.

## Default subobjects

Create components owned by the class in the constructor with
`CreateDefaultSubobject`. This is a declaration fragment; the validation fixture
provides the enclosing reflected class.

```cpp fragment
Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
SetRootComponent(Root);
Logic = CreateDefaultSubobject<UActorComponent>(TEXT("Logic"));
```

## Runtime components

A component created after actor construction needs a valid owner and registration
with the world before it participates in ticking or rendering. Use the engine's
component creation and registration APIs rather than manually calling lifecycle
callbacks.

```cpp fragment
USceneComponent* RuntimePart = NewObject<USceneComponent>(Owner);
Owner->AddInstanceComponent(RuntimePart);
RuntimePart->RegisterComponent();
RuntimePart->AttachToComponent(Owner->GetRootComponent(), FAttachmentTransformRules::KeepRelativeTransform);
```

## Responsibilities

Keep reusable behavior in components and orchestration in the actor. Do not make a
component assume a specific owner subclass unless that dependency is part of its
public contract. Use an interface or an explicit required type when communication
crosses ownership boundaries.

## Verification boundary

Compilation proves the API surface, not scene behavior. Attachment transforms,
visual placement, collision response, and designer usability require a suitable
runtime or human check.
