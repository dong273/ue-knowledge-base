# Ground Penetration Debugging

## Identify the colliding shape

For `ACharacter`, locomotion collision normally uses the capsule, while the skeletal mesh is presentation. Confirm which primitive is expected to block the floor before changing mesh or animation settings.

## Inspect collision state

Record the Actor gate, primitive `ECollisionEnabled` value, object type, response to the floor's channel, capsule size, and floor geometry. A visible mesh and a blocking shape are not the same evidence.

## Check initial penetration

Inspect `FHitResult::bStartPenetrating` and `PenetrationDepth` in the failing movement or sweep. Starting overlapped is a different fault from tunnelling or an incorrect response.

## Preserve the movement path

Do not mask penetration by teleporting the character upward every frame. Reproduce with collision-aware movement, then correct the initial transform, collision shape, response, or movement configuration that caused the overlap.

## Evidence boundary

Logs and state snapshots can isolate the configuration layer. Visual absence of clipping and stable traversal require an actual movement reproduction; they are not proven by a static readback alone.
