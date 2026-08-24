# Component Types Reference

Source: headers under
`Engine/Source/Runtime/Engine/Classes/Components/`.

## UActorComponent

`UActorComponent` is the base for reusable actor-owned behavior. It has no transform.
Ticking is opt-in through the component tick settings, and activation is a separate
state from registration.

```cpp fragment
PrimaryComponentTick.bCanEverTick = true;
bAutoActivate = true;
```

## USceneComponent

`USceneComponent` adds relative/world transform and attachment. Attach with
`SetupAttachment` for constructor-time default subobjects and with
`AttachToComponent` for an already registered runtime hierarchy.

```cpp fragment
Visual = CreateDefaultSubobject<USceneComponent>(TEXT("Visual"));
Visual->SetupAttachment(GetRootComponent());
```

## UPrimitiveComponent

`UPrimitiveComponent` extends `USceneComponent` with render and collision interfaces.
Collision enabled state, object type, and response channels are separate settings;
one successful API call does not prove the final gameplay response.

## Registration and activation

Registration connects a component to a world. Activation controls the component's
active state when that component implements active behavior. `RegisterComponent` and
`Activate` are not interchangeable.

## Ownership and attachment

`GetOwner` returns the owning actor. `GetAttachParent` describes scene attachment.
Ownership and attachment can point to different relationships and must not be used as
synonyms.

## Selection rule

Choose the lowest base type that provides the required contract: behavior only uses
`UActorComponent`; transform uses `USceneComponent`; rendering or collision uses a
suitable `UPrimitiveComponent` subclass.
