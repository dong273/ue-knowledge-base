# Save System Architecture

## Separate coordinator and payload

A project subsystem or other explicit coordinator can own slot selection, in-progress state, capture, migration, and restore. `USaveGame` remains a data payload and does not need to find every gameplay system itself.

## Capture stable data

Copy primitive values, names, gameplay tags, soft paths, and project-defined records that have stable meaning. Do not persist raw addresses or assume a runtime Actor name is a durable identity without a project contract.

## Slot policy

Treat slot name and user index as inputs to one documented policy. Autosave, manual save, checkpoint, and profile slots should not silently overwrite each other.

## Synchronous flow

The synchronous API is simple but performs work on the calling path. Use it only where the resulting stall is acceptable and always check the return value.

```cpp fragment
// Fragment: Payload was populated and validated earlier.
if (!UGameplayStatics::SaveGameToSlot(Payload, SlotName, UserIndex))
{
    ReportSaveFailure(SlotName);
}
```

## Asynchronous flow

Guard against overlapping requests, retain the payload for the operation, and clear the guard from the completion delegate. Define how shutdown, travel, and a late completion are handled by the coordinator.

## Schema migration

Read `SchemaVersion` before applying records. Migrate supported older versions in deterministic steps and reject unsupported future or corrupt data without partially mutating the live game.

## Restore ordering

Apply global/profile state before level-owned records that depend on a loaded world. Resolve stable IDs only after their registry or owning subsystem is ready.

## Test matrix

Cover new slot, existing slot, missing slot, incompatible schema, corrupt/failure path, repeated save, travel/reload, and any project-specific ownership transitions. A single successful write does not cover this matrix.
