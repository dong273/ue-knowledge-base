---
description: Use for UE 5.7 editor modules, detail customization, tool menus, transactions, and unattended editor automation.
---

# UE Editor Tools

Keep editor-only code in editor modules and validate registration, teardown, and unattended behavior separately.

## Module boundary

Editor modules may depend on `UnrealEd`, `PropertyEditor`, and `ToolMenus`. Runtime modules must not depend on editor-only modules.

## Customization lifecycle

Load `FPropertyEditorModule` during editor-module startup, register named layouts, and unregister them during shutdown.

```cpp fragment
FPropertyEditorModule& PropertyEditor =
    FModuleManager::LoadModuleChecked<FPropertyEditorModule>("PropertyEditor");
PropertyEditor.RegisterCustomClassLayout(
    ClassName,
    FOnGetDetailCustomizationInstance::CreateStatic(&FMyDetails::MakeInstance));
```

## Transactions

Use `FScopedTransaction` for user-visible editor changes and call `Modify()` on every object whose state participates in undo and redo.

```cpp fragment
const FScopedTransaction Transaction(NSLOCTEXT("UEKB", "EditObject", "Edit Object"));
Object->Modify();
```

## Menus and commands

Use `UToolMenus` for menu and toolbar extension. Treat command registration, menu ownership, and shutdown cleanup as one lifecycle.

## Automation boundary

Commandlet or unattended execution has no interactive user contract. Avoid modal prompts and return an explicit process result.

## Focused references

- [Detail customization patterns](references/detail-customization-patterns.md)
- [Editor module setup](references/editor-module-setup.md)
- [Unattended editor automation](references/unattended-editor-automation.md)
- [Minimized editor throttling](references/minimized-editor-throttling.md)
- [Blueprint graph authoring pitfalls](references/blueprint-graph-authoring-pitfalls.md)

## Verification boundary

Compilation proves API and module visibility. It does not prove menu placement, detail-panel usability, undo ergonomics, or unattended task success; observe those outcomes separately.
