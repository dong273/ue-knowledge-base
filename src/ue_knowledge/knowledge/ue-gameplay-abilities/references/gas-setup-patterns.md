# GAS Setup Patterns

## Owner and avatar lifetime

Use a PlayerState-owned ASC when abilities and attributes must survive Pawn replacement.
Use a character-owned ASC when the component should share the character lifetime. In
both cases, initialize owner/avatar after the actors are valid and repeat initialization
when the avatar changes.

```cpp fragment
ASC->InitAbilityActorInfo(OwnerActor, AvatarActor);
```

## Replication mode

Set the gameplay-effect replication mode deliberately with `SetReplicationMode` and keep
the component itself replicated. The appropriate Full, Mixed, or Minimal policy depends
on the owner type and which gameplay-effect details remote clients require.

```cpp fragment
ASC->SetIsReplicated(true);
ASC->SetReplicationMode(EGameplayEffectReplicationMode::Mixed);
```

## Granting abilities

Granting with `GiveAbility(FGameplayAbilitySpec(...))` is an authoritative operation.
Store returned handles when later removal or direct lookup is required.

```cpp fragment
const FGameplayAbilitySpecHandle Handle = ASC->GiveAbility(
    FGameplayAbilitySpec(AbilityClass, Level, InputId));
```

## Runtime acceptance

Compile evidence proves the setup calls exist. Runtime evidence must separately cover
the chosen owner/avatar lifetime, component replication, avatar replacement, and any
effect or attribute state expected to survive respawn.
