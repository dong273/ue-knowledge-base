# GameplayEffect Reference

## Create and apply a spec

Use the ASC to create an effect context and outgoing spec. Check the
`FGameplayEffectSpecHandle` before accessing `Spec.Data`, then apply the contained spec.

```cpp fragment
FGameplayEffectContextHandle Context = ASC->MakeEffectContext();
FGameplayEffectSpecHandle Spec = ASC->MakeOutgoingSpec(EffectClass, Level, Context);
if (Spec.IsValid())
{
    ASC->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get());
}
```

## SetByCaller magnitude

Set a caller-provided magnitude on the valid `FGameplayEffectSpec` with either the tag or
name overload, matching how the GameplayEffect modifier is configured.

```cpp fragment
Spec.Data->SetSetByCallerMagnitude(DataTag, Magnitude);
```

## Active-effect handle

`ApplyGameplayEffectSpecToSelf` returns `FActiveGameplayEffectHandle`. Treat handle
validity and later removal/query behavior as runtime concerns; compilation alone does
not prove the effect changed an attribute.

## Runtime acceptance

For duration, periodic, stacking, immunity, or execution-calculation behavior, create a
focused Automation test using the actual GameplayEffect configuration. Do not use a
generic ASC construction test as evidence for those behaviors.
