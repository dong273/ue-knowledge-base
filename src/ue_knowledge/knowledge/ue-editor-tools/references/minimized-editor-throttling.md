# Minimized Editor Throttling

When the editor main window is minimized (or loses foreground), UE throttles
CPU usage and the effective tick rate drops to a few frames per second
(verified UE 5.7: `GetMaxTickRate` returns 3 under
`ShouldThrottleCPUUsage`). PIE keeps running — physics, animation, and
time-based logic all advance — but at 3 fps.

## What breaks

Anything that assumes wall-clock frame timing:

- Short gameplay windows (sub-second state changes) pass before the next tick
  is observed; captures and samples miss them.
- Time-sensitive validation (narrow trigger windows, per-frame sampling,
  high-rate capture) fails or records distorted data while the editor is in
  the background.
- A validation that failed in the background and passed once the window came
  to the foreground is a throttle signature, not a code fix.

## Mitigations

- Run the editor unattended (`-unattended`) when the session drives PIE
  automatically; verify with a tick-rate probe instead of assuming.
- Keep the window in the foreground during foreground-sensitive validation.
- In time-sensitive scripts, reject samples whose game-time and recorded
  elapsed windows disagree (same-period check), and persist the failing
  sample with its hashes before retrying.

## Diagnostic rule

When a frame-window validation fails, check background throttling first
(expected tick rate vs measured) before touching gameplay logic.
