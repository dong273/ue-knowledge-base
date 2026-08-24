---
description: Use for UE 5.7 UMG, Slate, CommonUI, widget ownership, input mode, focus, and UI validation.
---

# UE UI: UMG, Slate, and CommonUI

Separate widget lifetime, viewport membership, input routing, focus, and visual acceptance.

## Create and display

Create a `UUserWidget` with an owning player, keep a reference, and add it to the viewport.

```cpp fragment
UUserWidget* Widget =
    UWidgetBlueprintLibrary::Create(WorldContext, WidgetClass, PlayerController);
Widget->AddToViewport(ZOrder);
```

## Remove and release

Use `RemoveFromParent` to remove a widget from its parent or viewport. Removal does not force immediate UObject destruction.

## Input mode

Use `SetInputMode_UIOnlyEx`, `SetInputMode_GameAndUIEx`, or `SetInputMode_GameOnly` deliberately and coordinate mouse-cursor state with the player controller.

```cpp fragment
UWidgetBlueprintLibrary::SetInputMode_GameAndUIEx(
    PlayerController,
    Widget,
    EMouseLockMode::DoNotLock);
```

## Focus

Keyboard and gamepad behavior depends on focusability, navigation, and the focused widget. Viewport presence alone is not proof of focus.

## CommonUI boundary

CommonUI adds activatable-widget and input-routing conventions. Enable the plugin and module before using its types.

## Focused references

- [CommonUI setup](references/common-ui-setup.md)
- [Widget types](references/widget-types.md)

## Verification boundary

Compilation proves type and API visibility. Automation can inspect lifetime and state; layout, readability, focus feel, and accessibility require appropriate runtime or human evidence.
