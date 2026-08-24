# Enhanced Input Trigger and Modifier Reference

Source: `InputAction.h`, `InputTriggers.h`, and `InputModifiers.h` in the Enhanced Input
plugin's public headers.

## Value types

`EInputActionValueType` supports Boolean, Axis1D, Axis2D, and Axis3D actions. Read the
matching type from `FInputActionValue`; a mismatched interpretation is a contract bug.

```cpp fragment
void AExampleController::HandleMove(const FInputActionValue& Value)
{
    const FVector2D Axis = Value.Get<FVector2D>();
}
```

## Trigger events

`ETriggerEvent` includes Started, Ongoing, Triggered, Canceled, and Completed. Choose the
event that matches whether gameplay needs edge, continuous, success, cancellation, or
completion behavior.

## Built-in triggers

Enhanced Input supplies trigger classes such as pressed, released, hold, tap, pulse,
chord, and combo variants. Their exact thresholds and interaction are asset settings;
verify the configured action rather than assuming the class name proves behavior.

## Built-in modifiers

Modifiers transform input values before trigger evaluation and binding delivery.
Common modifiers include dead zone, scalar, negate, response curve, and axis swizzle.
Modifier ordering can change the result.

## Custom triggers and modifiers

Custom trigger/modifier classes override the documented calculation functions. Keep
them deterministic for the supplied value and delta time, and expose tunable fields
through supported reflection specifiers.

```cpp fragment
UCLASS()
class UExampleModifier : public UInputModifier
{
    GENERATED_BODY()
    virtual FInputActionValue ModifyRaw_Implementation(
        const UEnhancedPlayerInput* PlayerInput,
        FInputActionValue CurrentValue,
        float DeltaTime) override;
};
```

## Debug boundary

Enhanced Input debugging can show evaluated actions and mappings, but a visible debug
line alone does not prove the resulting gameplay state or control quality.
