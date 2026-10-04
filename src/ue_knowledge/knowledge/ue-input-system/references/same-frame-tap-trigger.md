# Same-Frame Tap Trigger

A press and release completed within a single frame is a different input shape
from a held key, and logic that assumes "Started then still down" can miss it
entirely (verified against UE 5.7 Enhanced Input).

## Shape of the miss

One-frame native key tap: the action reports pressed and released in the same
frame, with no frame where the key is down. Logic that samples key-down state,
or that requires the action to still be held when its handler runs, sees
nothing — the tap is silently dropped while longer presses work.

## Fix shape

Handle the tap as its own path: act on the Started edge even when the key is
already up by the time the handler runs. In Blueprint, a dedicated tick-driven
tap handler that consumes the same-frame pulse and then calls the normal
action entry point keeps the public input mapping untouched.

## Test caliber

An automated test that holds the key for a fixed time (e.g. 250 ms) verifies a
held press, not a tap. It is a control experiment. The tap path is only proven
by reproducing the same input edge — press and release inside one frame — and
observing the red-to-green change on that path.
