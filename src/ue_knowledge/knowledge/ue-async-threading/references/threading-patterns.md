# Async and Task Patterns

## Async with a result

`Async` returns a `TFuture` whose result type is inferred from the callable.

```cpp fragment
// Fragment: do not block the game thread waiting for a slow result.
TFuture<int32> Future = Async(EAsyncExecution::ThreadPool, []
{
    return ComputeCount();
});
```

## Named-thread dispatch

`AsyncTask` accepts an `ENamedThreads::Type` and a move-only function. It is useful for an explicit handoff such as posting a completion to `ENamedThreads::GameThread`.

```cpp fragment
// Fragment: validate Owner on the game thread before applying the value.
AsyncTask(ENamedThreads::GameThread, [WeakOwner, Value]
{
    if (UObject* Owner = WeakOwner.Get())
    {
        ApplyToOwner(Owner, Value);
    }
});
```

## UE Tasks

`UE::Tasks::Launch` creates a task and returns a task handle. Use prerequisites or task events when the work has explicit dependencies instead of inventing polling flags.

```cpp fragment
// Fragment: the callable only reads a value snapshot.
UE::Tasks::TTask<int32> Task = UE::Tasks::Launch(
    UE_SOURCE_LOCATION,
    [Input] { return ComputeCount(Input); });
```

## Legacy async work

`FAsyncTask` and `FAutoDeleteAsyncTask` remain available for task types following the `DoWork` convention. Prefer one async model within a subsystem unless integration requirements justify mixing them.

## Completion and error policy

Every pattern needs a completion owner, failure representation, timeout or cancellation policy where appropriate, and a shutdown rule. A fire-and-forget call should be rare and must not hide required gameplay completion.
