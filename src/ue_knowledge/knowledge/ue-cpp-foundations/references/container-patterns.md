# Container Patterns Reference

Source: headers under `Engine/Source/Runtime/Core/Public/Containers/`.

## TArray

`TArray` stores an ordered sequence contiguously. `Add` appends, `Emplace` constructs in
place, `RemoveAt` preserves order, and `RemoveAtSwap` may change order.

```cpp fragment
TArray<int32> Values;
Values.Reserve(8);
Values.Add(10);
Values.Emplace(20);
Values.RemoveAtSwap(0);
```

## TMap

`TMap` associates unique keys with values. `Find` returns a pointer that is null when
the key is absent; it must not be retained across mutations that can reallocate.
In Chinese: 修改 `TMap` 后不要继续保存或使用 `Find` 返回的指针。

```cpp fragment
TMap<FName, int32> Counts;
Counts.Add(TEXT("Ammo"), 3);
if (const int32* Count = Counts.Find(TEXT("Ammo")))
{
}
```

## TSet

`TSet` stores unique values without stable iteration order. Use it for membership, not
for presentation ordering.

```cpp fragment
TSet<FName> Tags;
Tags.Add(TEXT("Ready"));
const bool bReady = Tags.Contains(TEXT("Ready"));
```

## Removal while iterating

Use the container's iterator removal API or a reverse index loop where supported. Do
not invalidate a range-for iterator by removing from the same container.

```cpp fragment
for (auto It = Counts.CreateIterator(); It; ++It)
{
    if (It.Value() <= 0)
    {
        It.RemoveCurrent();
    }
}
```

## UObject elements

A container field that must keep UObjects reachable uses a reflected property and a
tracked pointer type.

```cpp fragment
UPROPERTY()
TArray<TObjectPtr<UObject>> Objects;
```
