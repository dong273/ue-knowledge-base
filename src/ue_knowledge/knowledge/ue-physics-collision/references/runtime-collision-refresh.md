# Runtime Collision Refresh

A runtime write that reports success can still leave collision behavior
unchanged. Verified failure shapes (UE 5.7), each with a distinct fix:

## Shapes

1. Direct property write "succeeds" but the downstream behavior never
   triggers. The component state shows the new value; the interaction does not
   happen.
2. Writing the same value the component already has does not refresh anything.
   Even a legitimate setter is a no-op when the value is identical, so a
   "just call the setter again" recovery silently does nothing.

## Fix: force a real state transition

Toggle through a state change rather than re-assigning the target value — for
an enable gate, `false → true` (or `true → false → true`) forces the update
path to run. Verified working shape: toggle the component's collision enable
off then on at runtime, after which the expected interaction fires.

## Verification boundary

- Prove the fix by the interaction itself (the trace, overlap, or movement
  that was missing), not by reading back the property you just set.
- Runtime-only fixes are not map edits: if the change was made in a running
  PIE session or via tooling, record that the level asset itself was not
  modified.
- Keep the failed attempts (property-write timeout, same-value timeout) as
  named artifacts; they are the reason the toggle shape is trusted.
