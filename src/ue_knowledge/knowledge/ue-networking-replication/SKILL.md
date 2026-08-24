---
title: ue-networking-replication
description: Covers working on multiplayer networking, replication, RPC calls, net role logic, server/client authority, prediction, or synchronizing game state. Also use when the user mentions DOREPLIFETIME, dedicated server, replicated, or net role.
---

# UE Networking & Replication

Use this skill to review UE 5.7 replication contracts. Establish the server topology,
the owning connection, the replicated actor/component, and whether the requested value
is persistent state or a transient event before choosing an API.

## Authority checks

For a replicated actor, the authority owns the authoritative gameplay state. Use
`HasAuthority()` for an actor-side authority check and `IsLocallyControlled()` for
local-control behavior; they answer different questions.

## Actor replication state

On an actor spawned into a valid `UWorld`, `SetReplicates(bool)` changes the value
reported by `GetIsReplicated()`. This state readback is useful evidence for actor setup,
but it does not by itself prove delivery to another network connection.

The following is an intentionally incomplete declaration fragment. The compile fixture
provides the surrounding `AActor` subclass and generated header.

```cpp fragment
bReplicates = true;
SetReplicateMovement(true);

void AValidatedReplicationActor::GetLifetimeReplicatedProps(
    TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AValidatedReplicationActor, Health);
}
```

## RPC declaration contract

An RPC implementation uses the generated `_Implementation` entry point. In UE 5.7,
an ordinary Server RPC does not require `_Validate`. Adding `WithValidation` opts into
the generated validation entry point and therefore requires a matching `_Validate`.

This is a declaration fragment; the networking fixture compiles both forms.

```cpp fragment
UFUNCTION(Server, Reliable)
void ServerPlain(int32 Value);

UFUNCTION(Server, Reliable, WithValidation)
void ServerValidated(int32 Value);

void ServerPlain_Implementation(int32 Value);
void ServerValidated_Implementation(int32 Value);
bool ServerValidated_Validate(int32 Value);
```

Treat all client input as untrusted. `WithValidation` is one validation hook, not a
substitute for authoritative gameplay checks in the server implementation.

## Ownership and routing

A client can send a Server RPC only through an object whose ownership resolves to that
client connection. A Client RPC routes to the owning connection. NetMulticast is for a
server-originated transient event; persistent state belongs in replicated properties so
that a later-relevant or late-joining connection can receive the current value.

## Replicated subobjects

UE 5.7 exposes the registered-subobject API on `AActor`. The calls below are fragments;
the owner must keep the object alive and unregister it before destruction.

```cpp fragment
AddReplicatedSubObject(SubObject, COND_None);
RemoveReplicatedSubObject(SubObject);
```

Use the registered list when `IsUsingRegisteredSubObjectList()` is true. The legacy
`ReplicateSubobjects` override is a separate path and must not be mixed accidentally.

## Runtime evidence

A successful compile proves only the reflected declarations and API surface. A runtime
replication assertion must create a valid actor/world context and observe the intended
state or network behavior. The validation project keeps compile and Automation IDs
separate for this reason.

## Review checklist

- Confirm actor/component replication is enabled on the authority.
- Call `Super::GetLifetimeReplicatedProps` before registering local fields.
- Confirm RPC ownership and call direction.
- Keep validation side-effect free; make the implementation authoritative.
- Use replicated state, not multicast, for durable values.
- Report compile evidence separately from runtime and human evidence.

## References

- `references/rpc-decision-guide.md`
- `references/replication-patterns.md`
