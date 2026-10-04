# Editor World vs PIE Runtime State

Editor-utility APIs resolve the editor world, not the PIE world. A value read
through an editor-side channel during PIE is the editor copy's value and does
not reflect the running game instance.

## Symptom

PIE is clearly running (its own tick, log output, movement), but property reads
through editor tooling stay at authored editor-time values for the whole PIE
session. The channel looks healthy because writes through it read back
correctly — you are only ever reading and writing the editor-world actor.

## Verified behavior (UE 5.7)

- Editor-side level utilities resolve editor-world actors. The editor copy does
  not tick, so runtime state is never visible through it.
- World accessors on editor-utility libraries can resolve the editor world even
  while PIE is active. Verify which world a returned handle refers to before
  trusting runtime reads.
- `UEditorActorSubsystem::GetAllLevelActors()` during an active PIE session can
  return an empty result; after stopping PIE the same call enumerates the level
  normally. Calling editor actor subsystems while in play mode can also raise
  explicit play-mode errors.
- The one deterministic signal that PIE is ticking is PIE-side output, e.g. a
  PrintString counter in the game world.

## Diagnostic discipline

- Prove the PIE instance ticks first: a log counter or a first-line sentinel
  that fires every tick.
- Prove the write channel separately: write, read back through the same
  channel, then check whether the value survives the next tick (see the
  silent-failure diagnosis reference for the full sequence).
- Read runtime state only through PIE-side channels: on-screen print/debug
  draw, console commands executed in the game context, or automation hooks
  attached to the game world.
- Treat a zero-count enumeration as suspect. Re-test through a second channel
  before drawing any conclusion from it.
