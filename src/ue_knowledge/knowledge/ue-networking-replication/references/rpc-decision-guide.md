# RPC Decision Guide

Use this guide after identifying the authority, owning connection, and whether the
information is durable state or a transient event.

## State before event

Use a replicated property for durable state that a late joiner or newly relevant actor
must reconstruct. Use an RPC for an action request or transient notification. Do not
use NetMulticast as the sole storage mechanism for persistent state.

## Server RPC

A client-originated request belongs on an object owned by that client connection. The
server implementation must re-check permission, range, rate, and current authoritative
state before applying effects.

These are declaration fragments. `UEKB.Compile.NetworkingRpc` supplies the enclosing
reflected class and compiles both contracts.

```cpp fragment
UFUNCTION(Server, Reliable)
void ServerPlain(int32 Value);

UFUNCTION(Server, Reliable, WithValidation)
void ServerValidated(int32 Value);
```

## WithValidation boundary

Only a Server RPC explicitly declared with `WithValidation` requires a boolean
`_Validate` method. Returning false rejects that call. An ordinary Server RPC remains
valid without the specifier, but its `_Implementation` still needs equivalent
authoritative input checks when the request can affect game state.

```cpp fragment
bool AValidatedRpcActor::ServerValidated_Validate(int32 Value)
{
    return Value >= 0 && Value <= 100;
}
```

## Client and multicast routing

A Client RPC is sent by the authority to the owning connection. A NetMulticast RPC is
originated by the authority and executes for currently relevant recipients. Neither
route replaces property replication for persistent state.

## Reliable and unreliable

Choose Reliable when dropping the individual call would break the protocol. Choose
Unreliable for replaceable, high-frequency notifications. Reliability does not make an
invalid ownership route valid and does not remove the need for server-side checks.

## Review checklist

- Identify caller, executor, and owning connection.
- Decide whether the payload represents state or an event.
- Compile the exact declaration form in the target UE version.
- Validate untrusted input without side effects.
- Prove important runtime routing with Automation or a controlled multiplayer test.
