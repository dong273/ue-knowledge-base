# Unattended Editor Automation and Window State

Applies to Unreal Engine 5.7.4 on Windows and similar editor-driven validation setups.

## The failure pattern

An automation run can be logically correct while an external capture or watchdog times out. A minimized, unfocused, or otherwise backgrounded Editor may throttle its tick rate. The PIE world can remain alive, but helper processes that expect a responsive game window receive stale frames or no usable window.

## A reliable validation contract

1. Start a fresh Editor process for unattended automation when the run must be reproducible.
2. Use the Editor's unattended command-line mode for machine-driven validation. Keep the project path and map selection explicit.
3. Start PIE in a separate game window when evidence depends on real window pixels.
4. Wait for a stable window and frame before capturing; do not treat process existence as proof of visual readiness.
5. Record the process mode, PIE mode, capture target, timeout, and final log offset in the result.

`-unattended` reduces interactive-editor interference; it does not replace a pixel-level check. A passing object query or JSON state readback proves object state only. User-visible evidence still requires a real game-window capture, and human review remains a separate gate.

## Diagnostic split

| Symptom | Likely class | Check |
|---|---|---|
| PIE state is correct but capture times out | Window/tick throttling | Fresh unattended process, separate PIE window, stable-frame wait |
| Capture is black or targets the wrong window | Window selection | Enumerate visible windows and select the game window explicitly |
| Automation completes but logs contain old failures | Log baseline | Take the tail baseline after the final save/restart, then scan only the post-baseline tail |

Keep historical errors with their timestamps. “No errors” must always mean no matching errors after the stated baseline, not a claim about the entire Editor session.
