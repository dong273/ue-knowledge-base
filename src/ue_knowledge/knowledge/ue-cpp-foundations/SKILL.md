---
title: ue-cpp-foundations
description: Use when writing Unreal Engine C++ with reflection macros, UObject references, UE containers, delegates, names, text, or logging. For modules see ue-module-build-system.
---

# UE C++ Foundations

## Reflection declarations

`UCLASS`, `USTRUCT`, `UENUM`, `UFUNCTION`, and `UPROPERTY` are consumed by Unreal
Header Tool. A reflected type includes its generated header last among that header's
includes and places `GENERATED_BODY()` in the reflected declaration.

```cpp fragment
UCLASS()
class UExampleObject : public UObject
{
    GENERATED_BODY()

    UPROPERTY()
    TObjectPtr<UObject> ReferencedObject;
};
```

Source: `Engine/Source/Runtime/CoreUObject/Public/UObject/ObjectMacros.h` and
`Engine/Source/Runtime/CoreUObject/Public/UObject/ScriptMacros.h`.

## UObject references

Use a reflected `UPROPERTY` with `TObjectPtr` for an owning UObject field that garbage
collection must track. Use `TWeakObjectPtr` for a non-owning reference that may become
invalid. A raw pointer is appropriate only when its lifetime contract is independently
safe and reflection tracking is not required.

## FString, FName, and FText

Use `FString` for mutable string data, `FName` for identity-like names and keys, and
`FText` for localized user-facing text. Converting user-facing text to `FString` and
back can discard localization history.

```cpp fragment
const FName RowName(TEXT("Default"));
const FString DebugLabel = RowName.ToString();
const FText DisplayName = NSLOCTEXT("Example", "DisplayName", "Example");
```

## Logging

Declare a category in a header and define it in one translation unit. Choose verbosity
according to operational value; logs are runtime evidence only when the test also
asserts the expected state.

```cpp fragment
DECLARE_LOG_CATEGORY_EXTERN(LogExample, Log, All);
UE_LOG(LogExample, Verbose, TEXT("Value=%d"), Value);
```

## Related references

- `references/container-patterns.md`
- `references/delegate-patterns.md`
- `references/property-specifiers.md`
