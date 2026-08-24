# Third-Person Character Setup

This page defines the UE 5.7 responsibilities of a conventional third-person character without prescribing project assets.

## Component roles

`ACharacter` supplies the capsule, mesh, and CMC. A camera boom and camera are optional presentation components; they do not replace the character movement component.

## Camera-relative input

Convert a two-dimensional input action into forward/right world directions derived from the controller or camera yaw, then call `AddMovementInput` for each axis.

```cpp fragment
// Fragment: input binding, null checks, and project camera policy are omitted.
const FRotator YawOnly(0.0f, Controller->GetControlRotation().Yaw, 0.0f);
AddMovementInput(FRotationMatrix(YawOnly).GetUnitAxis(EAxis::X), MoveValue.Y);
AddMovementInput(FRotationMatrix(YawOnly).GetUnitAxis(EAxis::Y), MoveValue.X);
```

## Choose a rotation policy

For movement-facing characters, `bOrientRotationToMovement` and `RotationRate` are the main CMC surfaces. For controller-facing characters, projects commonly enable pawn use of controller yaw instead. Enabling conflicting policies makes diagnosis harder.

## Jump and launch

`ACharacter::Jump` uses the character movement jump path. `LaunchCharacter` queues an explicit launch velocity. They are different commands and should have separate gameplay conditions and tests.

## Camera independence

Camera lag, arm length, and collision probing affect presentation, not CMC velocity. Debug locomotion with camera smoothing disabled before attributing a visual delay to movement.

## Acceptance boundary

Compile and state inspection verify the setup surfaces. Camera comfort and movement feel require an actual playtest and must not be inferred from numeric settings alone.
