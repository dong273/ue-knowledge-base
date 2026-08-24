# UE 5.7 GAS API Migration

This guide records only contracts compiled against UE 5.7.4, CL 51494982. Treat the
target engine source and a clean compile as authoritative when migrating older code.

## Ability override parameters

`UGameplayAbility::ActivateAbility` and `EndAbility` use
`FGameplayAbilityActivationInfo` as their third parameter. An override copied from an
older signature must be updated to match the UE 5.7 declaration exactly.

```cpp fragment
void ActivateAbility(
    FGameplayAbilitySpecHandle Handle,
    const FGameplayAbilityActorInfo* ActorInfo,
    FGameplayAbilityActivationInfo ActivationInfo,
    const FGameplayEventData* TriggerEventData) override;
```

## Attribute reads

For a `FGameplayAttribute`, UE 5.7 exposes
`UAbilitySystemComponent::GetNumericAttribute(Attribute)`.

```cpp fragment
const float CurrentValue = ASC->GetNumericAttribute(Attribute);
```

## Ability cancellation

UE 5.7 exposes `CancelAbilities` with optional include tags, exclude tags, and an ability
to ignore. Pass pointers to tag containers or `nullptr` according to the intended filter.

```cpp fragment
ASC->CancelAbilities(&WithTags, &WithoutTags, AbilityToIgnore);
```

## Outgoing gameplay-effect specs

Create a `FGameplayEffectSpecHandle` with `MakeOutgoingSpec`. Validate the handle before
dereferencing `Spec.Data`; apply the resulting `FGameplayEffectSpec` through the ASC.

```cpp fragment
FGameplayEffectSpecHandle Spec = ASC->MakeOutgoingSpec(EffectClass, Level, Context);
if (Spec.IsValid())
{
    ASC->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get());
}
```

## Module dependencies

Code using the public GAS surfaces in this guide requires the owning module to declare
`GameplayAbilities`, `GameplayTags`, and `GameplayTasks` according to where those public
headers appear in its own public/private API. Do not use ad-hoc include paths to hide a
missing module dependency.

## Migration acceptance

- Locate the UE 5.7 declaration for every changed symbol.
- Compile the exact override/call form in a focused fixture.
- Run project-specific behavior tests after the compile succeeds.
- Do not infer removal or replacement solely because an older helper is absent from one header.
