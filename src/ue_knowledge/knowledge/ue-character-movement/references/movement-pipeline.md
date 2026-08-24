# Character Movement Pipeline

This page describes the stable inspection boundaries used to debug CMC in UE 5.7 without claiming an exact private call sequence for every mode.

## Input accumulation

`APawn::AddMovementInput` accumulates a world-space input vector. `GetPendingMovementInputVector`, `ConsumeMovementInputVector`, and `GetLastMovementInputVector` expose the pending, consumed, and last-consumed boundaries.

## Character movement update

CMC converts consumed input into acceleration, applies the active movement mode, and updates its `UpdatedComponent` through collision-aware movement. The exact internal branches depend on the movement mode, root motion, network role, and floor state.

## Floor state

Walking and falling decisions use CMC floor-query state. `FindFloor` writes an `FFindFloorResult`; its result distinguishes a blocking floor from a walkable floor. `CurrentFloor` is useful diagnostic state but should not be mutated as an external movement command.

## Mode transitions

`SetMovementMode` is the supported transition entry point. `OnMovementModeChanged` is the corresponding extension point for reacting to old/new modes; avoid scattering raw writes to movement-mode fields.

## Collision result

Collision-aware movement reports `FHitResult`. Inspect `bBlockingHit`, `Time`, `ImpactPoint`, `ImpactNormal`, and the hit component when diagnosing stopped or sliding motion.

## Debug snapshot

A useful per-frame snapshot records movement mode, custom mode, velocity, acceleration, pending input, network role, and whether CMC considers the character on the ground. A log snapshot explains state; it does not by itself prove feel, responsiveness, or multiplayer correctness.
