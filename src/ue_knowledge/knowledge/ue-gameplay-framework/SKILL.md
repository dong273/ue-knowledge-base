---
title: ue-gameplay-framework
description: Use for GameMode, GameState, PlayerController, PlayerState, Pawn, Character, GameInstance, authority, ownership, and player spawning. See references/framework-class-map.md.
---

# UE Gameplay Framework

## Authority and presence

`AGameModeBase` exists on authority and defines game rules and spawning policy.
`AGameStateBase` exists on server and clients and represents replicated match state.
Do not read GameMode from a remote client.
In Chinese: 远程客户端读取 `GameState`，不能依赖只存在于权威端的 `GameMode`。

Source: headers under `Engine/Source/Runtime/Engine/Classes/GameFramework/`.

## Player ownership

`APlayerController` represents a connection and is present on the server plus its
owning client. `APlayerState` represents replicated player state and is visible beyond
the owning client. Put private connection commands on the controller and shared
replicated identity/state on PlayerState.

## Pawn and Character

`APawn` is a controllable actor. `ACharacter` adds `UCharacterMovementComponent` and a
capsule-oriented character framework. A controller can possess a pawn; possession is
not the same as UObject ownership.

```cpp fragment
APawn* ControlledPawn = Controller->GetPawn();
APlayerState* State = Controller->PlayerState;
```

## GameInstance

`UGameInstance` lives across map travel within one process. It is not replicated and
is not a shared network authority. Use it for process-local services and
travel-persistent state whose synchronization is handled elsewhere.

## Spawning flow

GameMode selects player starts and default pawn classes, then restarts players through
its spawning hooks. Override the narrowest documented hook and preserve the superclass
contract unless intentionally replacing it.

## Placement rule

Game rules belong to GameMode, replicated match facts to GameState, per-connection
commands to PlayerController, replicated player facts to PlayerState, controllable
world behavior to Pawn/Character, and process-lifetime services to GameInstance.
