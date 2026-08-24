# Delegate Patterns Reference

Source: `Engine/Source/Runtime/Core/Public/Delegates/Delegate.h` and
`DelegateCombinations.h`.

## Single-cast delegates

A single-cast delegate stores one binding. Check `IsBound` or use `ExecuteIfBound`
before invocation when an empty binding is valid.

```cpp fragment
DECLARE_DELEGATE_OneParam(FOnValue, int32);
FOnValue OnValue;
OnValue.BindUObject(this, &UExampleObject::HandleValue);
OnValue.ExecuteIfBound(42);
```

## Multicast delegates

A native multicast delegate stores multiple listeners and broadcasts to all current
bindings. Broadcast order is not a gameplay contract.

```cpp fragment
DECLARE_MULTICAST_DELEGATE_OneParam(FOnChanged, int32);
FDelegateHandle Handle = OnChanged.AddUObject(this, &UExampleObject::HandleChanged);
OnChanged.Broadcast(42);
OnChanged.Remove(Handle);
```

## Dynamic delegates

Dynamic delegate macros integrate with reflection and Blueprint. Bound functions need
`UFUNCTION`; dynamic invocation has more overhead than native delegates and is chosen
for reflection or serialization needs.

```cpp fragment
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnChangedDynamic, int32, Value);

UPROPERTY(BlueprintAssignable)
FOnChangedDynamic OnChanged;
```

## Binding lifetime

`AddUObject` and `BindUObject` track UObject validity. Lambda and raw-pointer bindings
need an explicit lifetime contract. Store `FDelegateHandle` when a specific listener
must be removed from a long-lived publisher.

## Cleanup

Unbind external publishers when the subscriber stops owning the relationship. Actor or
component subscribers commonly do this during `EndPlay`; plain objects need an
equivalent explicit shutdown path.
