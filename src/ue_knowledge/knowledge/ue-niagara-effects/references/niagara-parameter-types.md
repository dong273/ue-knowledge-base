# Niagara Runtime Parameter Types

This page covers the public UE 5.7 parameter identifiers used by runtime callers.

## Variable identity

FNiagaraVariableBase stores a Niagara type definition and name. FNiagaraVariable adds value storage for supported use cases. Runtime component setters still require the name and value type to match the system parameter.

## Float parameter

Use UNiagaraComponent::SetVariableFloat for a float override.

```cpp fragment
NiagaraComponent->SetVariableFloat(ParameterName, Value);
```

## Vector parameter

Use SetVariableVec3 for FVector-compatible three-component data.

```cpp fragment
NiagaraComponent->SetVariableVec3(ParameterName, Direction);
```

## Boolean parameter

Use SetVariableBool for boolean overrides.

```cpp fragment
NiagaraComponent->SetVariableBool(ParameterName, bEnabled);
```

## Object and data-interface boundary

Object, texture, actor, and data-interface parameters have distinct setter and lifetime requirements. Prefer the most specific public API available for the parameter type.

## Namespace boundary

User parameters conventionally use the User namespace in Niagara assets. Runtime APIs receive an FName; verify the actual exposed parameter name instead of relying on display text.

## Validation checklist

- Compile the component setter signatures.
- Runtime-test missing names, wrong types, reset, pooling, and asset replacement.
- Inspect the Niagara parameter panel and observed simulation output.
