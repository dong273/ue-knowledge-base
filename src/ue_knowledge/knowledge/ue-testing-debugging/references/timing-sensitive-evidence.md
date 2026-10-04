# Timing-Sensitive Evidence

For anything that must happen before, during, or within a short window, a
success receipt is not timing proof. Sample the actual state at the moment the
event should be in effect.

## Pre-armed calls: receipt vs effect

A "pre-armed" call (register now, act at the event) can report success while
its effect never landed inside the window:

- Verify with the event-moment state, not the call's return value. Example
  shape: record whether the pause/preset was actually held at the first tick
  of the observed event, alongside the pawn's position/velocity at that tick.
- Two verified failure shapes worth keeping as evidence: the trigger did not
  fire at all, and the pre-arm landed after the event had already started.
  Both look like "the feature is broken" but have different fixes.

## Single-frame sampling artifacts

Strict same-frame assertions can fail on presentation/tick-order delay: a
frame-by-frame sample shows a few rows where the indicator is empty for one
frame while the adjacent two-frame-stable sample shows zero empty rows. Report
the sampling caliber with the result; require two consecutive stable frames
when that is the contract, and label single-frame gaps as sampling artifacts
unless proven otherwise.

## Keep the failed probes

Timing probes that failed are evidence of the window's sensitivity. Preserve
them (with the state they did capture) instead of deleting them after a later
passing run.
