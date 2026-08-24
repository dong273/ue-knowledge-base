# Asset Loading Patterns

Source: `Engine/Source/Runtime/Engine/Classes/Engine/AssetManager.h` and
`Engine/Source/Runtime/Engine/Classes/Engine/StreamableManager.h`.

## Asset Manager access

`UAssetManager::Get()` returns the configured global Asset Manager. Its
`FStreamableManager` can service soft-path load requests.

```cpp fragment
FStreamableManager& Streamable = UAssetManager::GetStreamableManager();
```

## RequestAsyncLoad

`RequestAsyncLoad` accepts soft object paths and a completion delegate, and returns a
streamable handle. Completion means the requested objects are available to resolve; it
does not prove gameplay initialization or visual readiness.

```cpp fragment
TSharedPtr<FStreamableHandle> Handle = Streamable.RequestAsyncLoad(
    Icon.ToSoftObjectPath(),
    FStreamableDelegate::CreateUObject(this, &UExampleObject::OnIconLoaded));
```

## Handle lifetime

Keep the handle when the caller needs cancellation, progress, grouping, or an explicit
loaded lifetime. Releasing a handle does not necessarily unload an asset immediately;
other hard references and handles participate in reachability.

## Resolving a soft pointer

After a successful load, `TSoftObjectPtr::Get` resolves to the loaded object or null.
Always handle null because configuration, cook rules, or load failure can invalidate
the assumption.

```cpp fragment
if (UTexture2D* LoadedIcon = Icon.Get())
{
}
```

## Synchronous loading

`LoadSynchronous` is an explicit blocking operation. Use it only where the stall is
understood and measured; async loading is the normal choice for gameplay-time content.
