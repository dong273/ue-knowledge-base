---
title: ue-input-system
description: Use for Unreal Engine Enhanced Input actions, mapping contexts, bindings, triggers, modifiers, and local-player setup. See references/input-action-reference.md.
---

# UE Enhanced Input System

## Core assets and runtime types

`UInputAction` describes a logical action and value type. `UInputMappingContext` maps
hardware inputs to actions. `UEnhancedInputComponent` binds action events, and
`UEnhancedInputLocalPlayerSubsystem` owns mapping contexts for a local player.

Source: headers under
`Engine/Plugins/EnhancedInput/Source/EnhancedInput/Public/`.

## Add a mapping context

Add contexts through the local-player subsystem. Priority resolves mappings when
multiple active contexts compete.

```cpp fragment
if (UEnhancedInputLocalPlayerSubsystem* Subsystem =
    ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(LocalPlayer))
{
    Subsystem->AddMappingContext(DefaultContext, 0);
}
```

## Bind an action

Bind on `UEnhancedInputComponent` using the action and an `ETriggerEvent`. The handler
signature must match the selected binding overload.

```cpp fragment
EnhancedInput->BindAction(MoveAction, ETriggerEvent::Triggered,
    this, &AExampleController::HandleMove);
```

## Input ownership

Mapping contexts are local-player state. Do not add them from authority-only code and
expect a remote client to receive them. Gameplay requests triggered by input still
need authoritative server validation when they affect replicated state.

## Context lifecycle

Add contexts when the local player enters the relevant mode and remove them when that
mode ends. Repeatedly adding a context without an ownership rule makes input state
hard to reason about.

## Verification boundary

Compilation proves Enhanced Input types and binding overloads. Device mappings,
priority conflicts, focus, and perceived controls require runtime or human input tests.
