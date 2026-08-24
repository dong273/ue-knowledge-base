---
title: ue-gameplay-abilities
description: Covers Gameplay Ability System, GameplayAbility, GameplayEffect, AttributeSet, AbilityTask, GAS input, prediction, or replication.
---

# Gameplay Ability System (GAS)

Use this skill for UE 5.7 GAS work. Confirm where the Ability System Component (ASC)
lives, which actor is owner/avatar, the replication mode, and whether the operation is
authority-only, predicted, or local presentation.

## Ability System Component setup

Call `InitAbilityActorInfo(OwnerActor, AvatarActor)` after both actors are valid and
again when the avatar changes. Choose the ASC owner according to the required lifetime;
a PlayerState-owned ASC can survive Pawn replacement, while a character-owned ASC has
the character lifetime.

The calls below are fragments compiled by `UEKB.Compile.GasApi`.

```cpp fragment
AbilitySystemComponent->SetReplicationMode(EGameplayEffectReplicationMode::Mixed);
AbilitySystemComponent->InitAbilityActorInfo(OwnerActor, AvatarActor);
```

## Gameplay ability signature

UE 5.7 declares `ActivateAbility` and `EndAbility` with
`FGameplayAbilityActivationInfo` as the third parameter. Match the declaration exactly
when overriding either method.

```cpp fragment
virtual void ActivateAbility(
    FGameplayAbilitySpecHandle Handle,
    const FGameplayAbilityActorInfo* ActorInfo,
    FGameplayAbilityActivationInfo ActivationInfo,
    const FGameplayEventData* TriggerEventData) override;
```

## Attributes and gameplay effects

Read a `FGameplayAttribute` through `GetNumericAttribute`. Build an outgoing effect spec,
set any SetByCaller magnitude on the valid spec, then apply that spec through the ASC.

```cpp fragment
const float Value = AbilitySystemComponent->GetNumericAttribute(Attribute);
FGameplayEffectSpecHandle Spec = AbilitySystemComponent->MakeOutgoingSpec(
    EffectClass, Level, AbilitySystemComponent->MakeEffectContext());
if (Spec.IsValid())
{
    Spec.Data->SetSetByCallerMagnitude(DataTag, Magnitude);
    AbilitySystemComponent->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get());
}
```

## Ability tasks and input

Ability tasks are owned by an active ability and require task activation/lifecycle
handling. Map Enhanced Input actions to gameplay tags or ability spec handles in a
separate input layer; let the ASC perform activation and cancellation.

```cpp fragment
AbilitySystemComponent->TryActivateAbilitiesByTag(InputTags);
AbilitySystemComponent->CancelAbilities(&CancelTags);
```

## Evidence boundary

Compilation validates the UE 5.7 type surface. Runtime tests must separately cover ASC
initialization, replication state, effect application, prediction, and task delegate
behavior used by the project. A component flag readback does not prove network delivery.

## References

- `references/ue5.7-api-migration.md`
- `references/gas-setup-patterns.md`
- `references/gameplay-effect-reference.md`
- `references/ability-task-reference.md`
- `references/gas-input-integration.md`
