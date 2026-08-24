# Material Parameter Contracts

This page covers stable UE 5.7 runtime parameter surfaces.

## Scalar parameter

Use SetScalarParameterValue for one floating-point parameter.

```cpp fragment
MID->SetScalarParameterValue(ParameterName, ScalarValue);
```

## Vector parameter

Use SetVectorParameterValue for FLinearColor, FVector, or FVector4-compatible values.

```cpp fragment
MID->SetVectorParameterValue(ParameterName, Tint);
```

## Texture parameter

Use SetTextureParameterValue with a UTexture pointer whose lifetime and streaming behavior are understood.

```cpp fragment
MID->SetTextureParameterValue(ParameterName, Texture);
```

## Parameter identity

Parameter names belong to the parent material graph. Check names against the actual material or instance hierarchy; a typo can leave the visible result unchanged without a C++ compile error.

## Material slots

A primitive can expose multiple material elements. Create or assign the MID on the intended element index and define behavior for an invalid slot.

## Parameter collections

UKismetMaterialLibrary::SetScalarParameterValue and SetVectorParameterValue update a UMaterialParameterCollection for the supplied world context.

## Validation checklist

- Compile the selected MID and collection methods.
- Runtime-test object lifetime, material element selection, and parameter readback where available.
- Verify visible output on the target renderer and platform.
