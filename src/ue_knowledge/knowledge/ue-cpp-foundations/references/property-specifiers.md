# Property Specifiers Reference

Source: `Engine/Source/Runtime/CoreUObject/Public/UObject/ObjectMacros.h` and UHT
specifier tables in `Engine/Source/Programs/Shared/EpicGames.UHT`.

## Property visibility and editability

`EditDefaultsOnly`, `EditInstanceOnly`, and `EditAnywhere` control editor mutation.
`VisibleDefaultsOnly`, `VisibleInstanceOnly`, and `VisibleAnywhere` expose read-only
property UI. Blueprint read/write access is a separate choice.

```cpp fragment
UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Config")
float MaxSpeed = 600.0f;

UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="State")
float CurrentSpeed = 0.0f;
```

## Blueprint property access

`BlueprintReadOnly` exposes a getter to Blueprint; `BlueprintReadWrite` also exposes a
setter. Neither specifier makes a private native field public C++ API. Private fields
exposed to Blueprint use the supported `AllowPrivateAccess` metadata when appropriate.

## Function exposure

`BlueprintCallable` exposes an execution pin, while `BlueprintPure` represents a call
without an execution pin. Networking specifiers define RPC routing and belong with the
networking contract, including the optional `WithValidation` rule.

```cpp fragment
UFUNCTION(BlueprintCallable, Category="Example")
void ResetState();

UFUNCTION(BlueprintPure, Category="Example")
int32 GetCount() const;
```

## Class and struct declarations

A reflected UObject class uses `UCLASS`; a reflected value type uses `USTRUCT` and
`GENERATED_BODY`. Only supported reflected property types can participate in UHT,
serialization, replication, and Blueprint exposure.

## Metadata boundary

Metadata changes editor and tooling behavior; it is not generally a runtime gameplay
contract. Verify metadata-dependent UX in the editor when the document claims a visual
or workflow outcome.
