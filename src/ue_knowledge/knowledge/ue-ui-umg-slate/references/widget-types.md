# Widget Type Boundaries

Choose the lowest layer that owns the behavior without duplicating state.

## UUserWidget

`UUserWidget` is the UObject-facing composition boundary for Widget Blueprints and C++ widget classes.

## UWidget

`UWidget` is the UObject wrapper for one widget. Use visibility, enabled state, and focus APIs according to the interaction contract.

## Panel widgets

`UPanelWidget` owns child slots. Adding a child establishes panel ownership; removing it changes the hierarchy.

## Common controls

`UTextBlock`, `UImage`, `UButton`, and related controls expose typed presentation and interaction APIs.

## BindWidget

`meta=(BindWidget)` requires a matching named widget in the generated Widget Blueprint hierarchy.

```cpp fragment
UPROPERTY(meta=(BindWidget))
TObjectPtr<UButton> ConfirmButton;
```

## Slate

Slate types such as `SWidget` use shared-pointer lifetime and are not UObjects. Use Slate directly for low-level or editor UI and bridge it deliberately when a UObject wrapper is required.

## Lifetime

Delegates, timers, and asynchronous callbacks must not assume a widget remains constructed or in the viewport. Unbind or use weak ownership where necessary.

## Verification boundary

Compile type relationships and binding declarations. Widget Blueprint compilation, runtime hierarchy, layout, text clipping, focus, and accessibility need separate evidence.
