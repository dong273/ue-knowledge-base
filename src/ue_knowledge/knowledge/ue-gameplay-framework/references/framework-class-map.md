# Gameplay Framework Class Map

Source: headers under `Engine/Source/Runtime/Engine/Classes/GameFramework/` and
`Engine/Source/Runtime/Engine/Classes/Engine/GameInstance.h`.

## Presence matrix

| Class | Authority | Owning client | Other clients | Role |
|---|---|---|---|---|
| `AGameModeBase` | yes | no | no | authoritative rules |
| `AGameStateBase` | yes | yes | yes | shared match state |
| `APlayerController` | yes | own controller | no remote controllers | connection commands |
| `APlayerState` | yes | yes | yes | shared player state |
| `APawn` / `ACharacter` | yes | relevant proxy | relevant proxy | controllable world actor |
| `UGameInstance` | process local | process local | separate instance | not replicated |

Relevancy and replication settings can further limit actor presence; the table
describes the framework role, not a guarantee that every actor is always relevant.

## Ownership chain

RPC routing depends on network ownership, commonly through a PlayerController-owned
chain. Actor attachment, possession, UObject outer, and network ownership are distinct
relationships.

## Match state

`AGameMode` adds the match state machine on top of `AGameModeBase`; projects that do not
need that flow can use the base class. Replicate observable match facts through
GameState rather than querying GameMode from clients.

## Player lifecycle hooks

GameMode exposes hooks such as `PreLogin`, `Login`, `PostLogin`, `Logout`, and
`RestartPlayer`. Network joins and seamless travel add context, so project code should
not invent a universal cross-machine timestamp order beyond the documented hooks.

## Verification boundary

Compilation proves type and method availability. Presence, ownership, spawning, and
travel behavior need a networked runtime test for the project's configuration.
