# GAS and Enhanced Input Layering

## Responsibility boundary

Enhanced Input converts device input into actions. A thin gameplay-input layer maps
those actions to gameplay tags or ability spec handles. The ASC owns ability activation,
cancellation, prediction, costs, cooldowns, and authoritative outcomes.

## Tag-driven activation

UE 5.7 exposes `TryActivateAbilitiesByTag` for a gameplay-tag container. Keep the input
mapping explicit so changing a key binding does not change the ability contract.

```cpp fragment
ASC->TryActivateAbilitiesByTag(InputTags);
```

## Release and cancellation

Use the exact ability/input policy chosen by the project. `CancelAbilities` accepts
optional include/exclude tag-container pointers and an ability to ignore; it matches
ability tags according to the ASC contract, not arbitrary actor tags.

```cpp fragment
ASC->CancelAbilities(&CancelTags, nullptr, nullptr);
```

## Runtime acceptance

Compilation proves the GAS calls and Enhanced Input types are available from declared
modules. Runtime evidence must separately cover press, hold, release, remote activation,
prediction, and cancellation for the chosen mapping. A direct call to the ASC is not
proof that physical input was delivered.
