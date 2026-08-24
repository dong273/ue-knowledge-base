# CommonUI Setup

CommonUI builds screen stacks and input routing around activatable widgets.

## Plugin and module

Enable the CommonUI plugin and add the `CommonUI` module dependency to code that includes CommonUI types.

## Activatable widgets

`UCommonActivatableWidget` exposes `ActivateWidget`, `DeactivateWidget`, and `IsActivated`.

```cpp fragment
Screen->ActivateWidget();
const bool bActive = Screen->IsActivated();
Screen->DeactivateWidget();
```

Activation state is not proof that the intended screen is visible, focused, or topmost.

## Containers

Use a CommonUI activatable-widget container when navigation requires stack or switcher semantics. Define who pushes and removes screens.

## Input routing

Treat CommonUI action routing and Enhanced Input mapping ownership as an application policy. Test keyboard, mouse, and gamepad paths separately.

## Back behavior

Define which active screen handles back and what happens when the stack becomes empty. Avoid mixing several independent owners of the same back action.

## Verification boundary

Compile plugin types and exercise activation transitions. Inspect actual focus, navigation, layering, and platform input behavior before claiming the flow works.
