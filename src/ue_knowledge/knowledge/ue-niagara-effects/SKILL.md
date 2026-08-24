---
description: Use for UE 5.7 Niagara systems, components, spawning, user parameters, data interfaces, pooling, and visual-result verification.
---

# UE Niagara Effects

Use this workflow to separate system assets, component lifetime, runtime parameters, data interfaces, and visible output.

## Runtime types

UNiagaraSystem is the effect asset. UNiagaraComponent owns one runtime system instance and exposes activation, deactivation, asset assignment, and user-parameter setters.

## Spawn at a location

UNiagaraFunctionLibrary::SpawnSystemAtLocation returns a UNiagaraComponent for the spawned system.

```cpp fragment
UNiagaraComponent* Component = UNiagaraFunctionLibrary::SpawnSystemAtLocation(
    WorldContext,
    System,
    Location,
    Rotation);
```

Choose auto-destroy, auto-activate, pooling, and pre-cull behavior deliberately.

## Spawn attached

SpawnSystemAttached creates an effect associated with a scene component and attachment transform. Define behavior when the attachment owner is destroyed.

## Component control

UNiagaraComponent::SetAsset changes the system asset. Activate and Deactivate control execution; a component being active is not proof that particles are visible.

## User parameters

SetVariableFloat, SetVariableVec3, and SetVariableBool update named component overrides. Parameter identity and type must match the Niagara system.

## Focused references

- [Data interface boundaries](references/niagara-data-interfaces.md)
- [Parameter types](references/niagara-parameter-types.md)

## Verification boundary

Compile runtime APIs and test component state or lifetime. Emitter output, bounds, translucency, collisions, GPU behavior, and visual quality require Niagara debugging tools and human frame review.
