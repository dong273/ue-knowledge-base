# Replication Patterns

These patterns are intentionally focused. Code fences are fragments compiled through
the validation fixture; they are not standalone translation units.

## Replicated property with notification

Declare the property and notification in the reflected class, register the property in
`GetLifetimeReplicatedProps`, and keep the notification safe to run more than once.

```cpp fragment
UPROPERTY(ReplicatedUsing=OnRep_Health)
int32 Health = 100;

UFUNCTION()
void OnRep_Health();

DOREPLIFETIME(AValidatedReplicationActor, Health);
```

## Per-connection condition

Use a lifetime condition when the property has a stable recipient policy. `COND_OwnerOnly`
is appropriate only when actor ownership is established for the intended connection.

```cpp fragment
DOREPLIFETIME_CONDITION(AValidatedReplicationActor, PrivateValue, COND_OwnerOnly);
```

## Fast-array surface

`FFastArraySerializer` and `FFastArraySerializerItem` provide the engine surface for
delta serialization of item collections. A real implementation must call the matching
dirty-marking functions whenever authoritative items or the array change.

```cpp fragment
struct FValidatedItem : public FFastArraySerializerItem
{
    int32 Value = 0;
};

struct FValidatedArray : public FFastArraySerializer
{
    TArray<FValidatedItem> Items;
};
```

## Registered subobject

Register a live subobject on the authority and remove it before the owner releases it.

```cpp fragment
AddReplicatedSubObject(SubObject, COND_None);
RemoveReplicatedSubObject(SubObject);
```

## Movement and dormancy

`SetReplicateMovement` enables the actor movement replication surface. Dormancy is a
separate bandwidth policy; waking or flushing an actor must be tested against the
project's actual update and relevancy expectations.

## Runtime acceptance

Compilation establishes that declarations and symbols match UE 5.7. Runtime evidence
must separately observe the replicated state in a valid world/network setup. A state
readback on an uninitialized actor is not proof of network delivery.
