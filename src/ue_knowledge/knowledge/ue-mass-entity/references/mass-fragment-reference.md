# Mass Fragment Categories

Choose the narrowest Mass data category that matches ownership and update frequency.

## Entity fragment

Derive per-entity data from `FMassFragment`. Each matching entity has its own value in the archetype chunk.

## Tag

Derive presence-only state from `FMassTag`. Tags participate in archetype matching without storing a per-entity payload.

## Chunk fragment

Derive per-chunk data from `FMassChunkFragment`. The value belongs to the chunk, so it must not encode identity for a single entity.

## Shared fragment

Derive mutable archetype-shared data from `FMassSharedFragment`. Entities with the same shared-fragment value can share archetype storage.

## Const shared fragment

Derive immutable shared configuration from `FMassConstSharedFragment`. Use it for configuration shared by entities rather than transient per-entity state.

## Query selection

Fragment and tag requirements define which archetypes match a query. Presence, optionality, and access mode must reflect the processor's actual code path.

## Review checklist

- Per-entity changing data: `FMassFragment`.
- Presence-only state: `FMassTag`.
- Per-chunk metadata: `FMassChunkFragment`.
- Shared mutable data: `FMassSharedFragment`.
- Shared immutable configuration: `FMassConstSharedFragment`.
