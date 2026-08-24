# Top-Down Action Movement Setup

This page separates movement, facing, navigation, and camera responsibilities for a top-down action character.

## Choose the movement basis

For a fixed camera, map the two-dimensional input action onto two stable world directions. For a rotating camera, derive the planar basis from camera/controller yaw. Pass normalized directions to `AddMovementInput` and let CMC apply speed and acceleration.

```cpp fragment
// Fragment: choose WorldForward/WorldRight from the project's camera policy.
AddMovementInput(WorldForward, MoveValue.Y);
AddMovementInput(WorldRight, MoveValue.X);
```

## Keep movement and facing separate

A character can move through CMC while facing an aim point. Decide whether facing is controller-driven, movement-driven, or explicitly set by gameplay code; do not enable multiple competing rotation owners.

## Cursor or stick aiming

Convert the aim source to a world-space direction, project it onto the movement plane, reject near-zero vectors, and compute the desired yaw. Screen deprojection, ground intersection, and controller-stick aiming are separate input concerns.

## Click navigation versus direct movement

`SimpleMoveToLocation`/navigation requests and direct `AddMovementInput` serve different control models. Do not issue both continuously for the same pawn without an explicit arbitration rule.

## Network boundary

Local cursor coordinates are not authoritative gameplay state. In multiplayer, send a validated aim intent or world direction appropriate to the game, and keep server-owned actions separate from camera-only presentation.

## Acceptance boundary

Input and API fixtures can verify the wiring surface. Responsiveness, aim readability, and action-game feel remain playtest outcomes.
