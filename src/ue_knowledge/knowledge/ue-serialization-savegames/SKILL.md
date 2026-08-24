---
title: ue-serialization-savegames
description: Use when designing a UE 5.7 USaveGame payload, slot flow, schema migration, or synchronous/asynchronous GameplayStatics save/load boundary.
---

# UE Serialization and Save Games

Use this guide to separate persistent data, runtime ownership, disk operations, and restore logic.

## SaveGame is an explicit snapshot

`USaveGame` is a payload type used by the SaveGame APIs. Unreal does not automatically discover and persist an arbitrary world, Actor graph, or subsystem state. Project code must copy stable data into a save object and apply it after load.

## Define a versioned payload

Store a schema version and stable identifiers rather than live Actor pointers. Keep presentation objects and transient caches out of the persistent contract.

```cpp fragment
// Fragment: generated header and project-specific records are omitted.
UPROPERTY(SaveGame)
int32 SchemaVersion = 1;

UPROPERTY(SaveGame)
TMap<FName, int32> ProgressById;
```

The `SaveGame` property flag identifies fields intended for save-game serialization paths; it is not a command that writes a slot by itself.

## Create and write a slot

`UGameplayStatics::CreateSaveGameObject` constructs a save object of the requested class. `SaveGameToSlot` performs a synchronous write and returns a boolean result. Check the result and keep failure handling outside the payload type.

```cpp fragment
// Fragment: ownership, slot policy, and error reporting are project-specific.
USaveGame* Payload = UGameplayStatics::CreateSaveGameObject(UMySaveGame::StaticClass());
const bool bSaved = UGameplayStatics::SaveGameToSlot(Payload, SlotName, UserIndex);
```

## Verified object construction

The validation Automation creates `UUEKBSaveGameFixture` through `CreateSaveGameObject` and checks that the returned object has the requested class. It does not write a slot or prove a disk round-trip.

## Load a slot

Use `DoesSaveGameExist` when the distinction between a missing slot and a load failure matters. `LoadGameFromSlot` returns a `USaveGame*`; validate it and cast to the expected payload class before applying data.

## Prefer async operations on interactive paths

`AsyncSaveGameToSlot` and `AsyncLoadGameFromSlot` schedule slot operations and report completion through delegates. Treat completion as the point to update UI or release an in-progress guard. A scheduled call is not a success result.

## Restore in phases

Load and validate the payload, migrate older schema versions, create or locate runtime owners, then apply state. World references should be resolved from stable IDs after the relevant level or subsystem is available.

## Validation boundary

A type/compile fixture proves the UE API surface. A temporary-slot Automation test is required before claiming a specific payload round-trips on UE 5.7; project gameplay correctness still needs scenario tests.

See `references/save-system-architecture.md` for ownership and migration boundaries.
