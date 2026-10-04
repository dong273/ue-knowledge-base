# PIE Visual Capture Channels

Different capture paths answer different claims. Match the channel to the
claim, and record what each capture does not prove.

## Editor viewport screenshot can be stale

An editor-side capture can return success while writing a stale frame: two
captures from different camera positions produced byte-identical files in a
verified UE 5.7 session. Treat a screenshot API result as unverified until you
have a change test (move the camera, recapture, expect different bytes).

## HighResShot semantics

`HighResShot` executed via `SystemLibrary.ExecuteConsoleCommand` (UE 5.7):

- Produces files only while PIE is actually running; nothing is written after
  PIE stops.
- Emits two files per request (an empty pre-render buffer and the real frame);
  keep the larger one.
- Renders the scene only — no Slate/UMG UI, no window chrome. A UI claim needs
  a different channel.
- It captures the editor viewport, not the player camera: moving the editor
  camera with `SetLevelViewportCameraInfo` changes the output, which is the
  test for which viewpoint you are actually getting.

## OS-level window capture

`PrintWindow` with `PW_RENDERFULLCONTENT` (flag 2) captures a real window,
including PIE preview windows:

- The image includes window borders and is scaled by the system DPI factor.
  Image pixel size is not the game resolution; the authoritative size is
  `PlayerController.GetViewportSize()`.
- `PrintWindow` can block. Run it in a separate helper process with a timeout
  so a hung capture cannot stall the session.
- Snapshot the window (handle, rect, visible, minimized) before and after the
  capture and bind both to the evidence, so the capture proves the window was
  not changed underneath it.

## Say what the capture does not verify

A successful capture does not by itself verify: the live PIE world identity,
the pawn path or view target, same-frame player-camera binding, a fresh GPU
frame, the render viewport size, or any pixel-review/gameplay acceptance.
List those as explicitly not verified, and gate them through separate checks.

## Programmatic pixels vs human review

Automated pixel statistics and per-frame capture readiness are one evidence
layer. Readability judgments (HUD legible, target feedback visible, text
truncation, white blockout) are a human layer and cannot be upgraded from
programmatic counts. Keep `PENDING_MANUAL` until a person actually reviewed
the frames.
