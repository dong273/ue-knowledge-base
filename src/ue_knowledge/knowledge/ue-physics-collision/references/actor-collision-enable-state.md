# Actor Collision Enable State

## What SetActorEnableCollision controls

`SetActorEnableCollision(bool)` writes the Actor-level collision gate. `GetActorEnableCollision()` returns that gate. UE 5.7 exposes both on `AActor`.

## What it does not replace

The Actor gate does not replace per-component `SetCollisionEnabled`, collision profiles, response containers, geometry, overlap generation, or hit-notification settings. An Actor may report its gate as enabled while a target primitive remains `NoCollision`.

## Verified readback

The validation Automation test toggles a transient Actor false/true and checks `GetActorEnableCollision` after each call. It proves only Actor-level state readback; it does not claim a world collision or overlap occurred.

## Diagnostic order

Read the Actor gate first, then inspect the exact `UPrimitiveComponent`, its collision mode/profile, object type, channel response, and collision geometry. Finally run the intended trace, sweep, overlap, or movement reproduction.
