# Thread Safety Guide

## Classify accessed state

Separate immutable snapshots, worker-owned mutable data, game-thread-owned UObject state, and genuinely shared state. Write the owner and synchronization rule next to the shared structure.

## UObject boundary

Garbage collection, Actor/component mutation, Blueprint events, and most gameplay framework operations are game-thread concerns. Some engine APIs have explicit thread-safe contracts; verify those APIs individually rather than generalizing from one exception.

## Weak pointers are not locks

`TWeakObjectPtr` can avoid keeping a UObject alive and can be checked before use. It does not make background UObject access safe and does not prevent the object from becoming invalid between unrelated operations.

## Locks

`FCriticalSection` with `FScopeLock` protects a critical section. Keep locked work small, define lock ordering when more than one lock exists, and never assume a lock fixes a game-thread-only API call.

```cpp fragment
// Fragment: StateLock and SharedResult belong to the same documented owner.
{
    FScopeLock Guard(&StateLock);
    SharedResult = LocalResult;
}
```

## Atomics

Use `TAtomic` for small state with an explicit memory/ordering requirement. An atomic flag does not make a larger object graph safe to read or write concurrently.

## Container boundary

Treat ordinary `TArray`, `TMap`, and `TSet` mutation as owner-thread work unless external synchronization protects all readers and writers. Do not retain element pointers across a mutation that may reallocate or rehash.

## Shutdown

Define whether shutdown waits, cancels, drains, or abandons pending work. A callback must not apply results after its owner or world context has ended.
