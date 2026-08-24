# Post-Process Ownership and Blending

This page separates UE 5.7 post-process data, blend ownership, and visual acceptance.

## Settings structure

FPostProcessSettings contains override flags and values. A value participates only when its corresponding override and the owning blend path make it active.

## Volume ownership

APostProcessVolume exposes Settings, BlendWeight, BlendRadius, BlendPriority, and bUnbound. Bound volumes depend on camera position; an unbound volume participates globally in its world.

## Component ownership

UPostProcessComponent exposes Settings, BlendWeight, and bUnbound. Attachment to a shape component can define a bounded influence.

## Camera ownership

UCameraComponent owns PostProcessSettings and PostProcessBlendWeight. SetPostProcessBlendWeight changes the contribution of that camera-owned settings set.

```cpp fragment
Camera->SetPostProcessBlendWeight(1.0f);
```

## Blendables

Camera and post-process components expose AddOrUpdateBlendable for IBlendableInterface objects. Blend weight remains part of the runtime composition contract.

```cpp fragment
Camera->AddOrUpdateBlendable(Blendable, Weight);
```

## Completion boundary

C++ state can prove that settings and weights were assigned. It cannot prove exposure, color grading, bloom, depth of field, or material blend output looked correct.

## Validation checklist

- Compile settings owners, weights, and blendable APIs.
- Runtime-test active owner selection and weight changes.
- Capture representative frames and perform human visual comparison.
