---
title: ue-async-threading
description: Use when moving UE 5.7 work off the game thread with Async/AsyncTask or UE::Tasks, and when defining ownership, cancellation, and game-thread handoff boundaries.
---

# UE Async and Threading

Use this guide to choose an asynchronous primitive and make data ownership explicit before moving work off the game thread.

## Start from the data boundary

Identify the input snapshot, output value, owner lifetime, cancellation rule, and the thread on which completion may touch gameplay state. Moving a lambda to a worker does not make the captured objects thread-safe.

## Choose a primitive

`Async(EAsyncExecution, Callable)` returns a `TFuture` for a callable. `AsyncTask(ENamedThreads::Type, Function)` queues a function to a named Task Graph thread. UE Tasks exposes `UE::Tasks::Launch`, task prerequisites, and related structured task primitives. Choose the smallest surface that matches result, dependency, and lifetime needs.

## Keep UObject access explicit

Assume gameplay UObject and Actor mutation belongs on the game thread unless the specific API documents a different contract. Prefer copying plain input data for worker computation, then marshal the result back and revalidate the owner.

## Background compute with game-thread handoff

The following fragment shows the boundary, not cancellation or owner policy:

```cpp fragment
// Fragment: Input is an immutable value snapshot; ApplyResult runs on the game thread.
Async(EAsyncExecution::ThreadPool, [Input]()
{
    FComputedResult Result = ComputeFromSnapshot(Input);
    AsyncTask(ENamedThreads::GameThread, [Result = MoveTemp(Result)]() mutable
    {
        ApplyResult(MoveTemp(Result));
    });
});
```

## Lifetime and cancellation

Do not capture a raw owner pointer into delayed work without a lifetime contract. For UObject owners, a weak object pointer can be revalidated on the game thread; cancellation still needs project-owned state because invalidation and cancellation are different events.

## Avoid blocking handoffs

Waiting on the game thread for work whose completion needs the game thread can deadlock or stall. Prefer completion callbacks, task prerequisites, or a polled state appropriate to the subsystem.

## Thread-safe state

Protect mutable shared data with a documented ownership rule, a lock, an atomic, or a message/queue boundary appropriate to the data. A `UPROPERTY` annotation and a UE container type do not make concurrent mutation safe.

## Validation boundary

Compile fixtures prove signatures and captures. Runtime tests must control completion and timeout before claiming a task executes on a specific thread or a cancellation path is race-free.

See the references for safety and API patterns.
