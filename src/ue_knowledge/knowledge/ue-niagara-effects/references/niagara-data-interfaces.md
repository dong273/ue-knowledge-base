# Niagara Data Interface Boundaries

This page describes stable UE 5.7 ownership rules for Niagara data interfaces.

## Base contract

UNiagaraDataInterface is the UObject base for data interfaces exposed to Niagara scripts. Concrete interfaces define their own CPU, GPU, per-instance, and resource-lifetime contracts.

## Skeletal-mesh interface

UNiagaraDataInterfaceSkeletalMesh exposes skeletal-mesh data to Niagara. UNiagaraFunctionLibrary::GetSkeletalMeshDataInterface retrieves a named override from a Niagara component when that override exists.

```cpp fragment
UNiagaraDataInterfaceSkeletalMesh* Interface =
    UNiagaraFunctionLibrary::GetSkeletalMeshDataInterface(
        NiagaraComponent,
        OverrideName);
```

The returned pointer can be null; the override name and system asset must agree.

## Array interfaces

Niagara includes typed array data interfaces such as UNiagaraDataInterfaceArrayFloat and UNiagaraDataInterfaceArrayInt32. Use the public array function library or supported user-parameter path instead of mutating internal storage.

## Static-mesh boundary

Static-mesh data interfaces can depend on mesh render data, sampling regions, CPU-access settings, or GPU resources. Validate the chosen concrete interface and target platform rather than assuming every mesh is sampleable.

## Thread and render boundary

A data interface can maintain game-thread, simulation-thread, and render-thread state. UObject availability alone does not prove its GPU proxy or per-instance data is ready.

## Validation checklist

- Compile only public headers and supported access functions.
- Runtime-test missing overrides, owner destruction, and system reset.
- Validate CPU and GPU simulations separately where the interface supports both.
