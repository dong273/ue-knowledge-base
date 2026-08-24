---
description: Use for UE 5.7 dynamic material instances, material parameters, parameter collections, post-process ownership, and visual-result verification.
---

# UE Materials and Rendering

Use this workflow to separate material assets, per-instance parameters, world-wide parameters, post process, and visible output.

## Material ownership

A UMaterialInterface is an asset-level material surface. Use UMaterialInstanceDynamic for runtime parameter changes that belong to one component or caller.

## Create a dynamic instance

UPrimitiveComponent::CreateDynamicMaterialInstance creates and assigns a MID for one material element.

```cpp fragment
UMaterialInstanceDynamic* MID =
    Primitive->CreateDynamicMaterialInstance(ElementIndex, SourceMaterial);
```

Keep the returned object through a UObject-owned reference when later updates are required.

## Parameter updates

UMaterialInstanceDynamic exposes scalar, vector, and texture setters by parameter name. A setter call does not prove the parent material contains or visibly uses that parameter.

## Global parameters

UKismetMaterialLibrary updates UMaterialParameterCollection values for a world context. Use a collection only when shared world-level state is intended; use a MID for per-object variation.

## Post-process boundary

Post-process volumes, components, and cameras own blend settings and weights. The same FPostProcessSettings structure can participate in different blend stacks.

## Focused references

- [Material parameter contracts](references/material-parameter-reference.md)
- [Post-process settings](references/post-process-settings.md)

## Verification boundary

Compile parameter and post-process APIs. Rendered color, exposure, shading, temporal artifacts, and platform quality require captured frames and human visual review.
