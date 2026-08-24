# Editor Module Setup

An editor module isolates editor dependencies from code that must load in games or packaged builds.

## Target and module ownership

Include the editor module only in editor targets. Keep runtime types in a runtime module and editor extensions in a separate editor module.

## Build dependencies

Editor-only dependencies belong in the editor module's private dependency list.

```csharp config
PrivateDependencyModuleNames.AddRange(new[]
{
    "UnrealEd",
    "PropertyEditor",
    "ToolMenus"
});
```

## Module implementation

Implement `IModuleInterface` and perform registration in `StartupModule`.

```cpp fragment
class FMyEditorModule final : public IModuleInterface
{
public:
    virtual void StartupModule() override;
    virtual void ShutdownModule() override;
};
```

## Shutdown symmetry

Unregister class layouts, commands, menu owners, delegates, and callbacks that the module registered. Guard teardown when another editor module may already be unavailable.

## Loading phase

Choose the plugin module loading phase from the dependency needed by registration. A loading phase is ordering policy, not proof that every dependent subsystem is ready.

## Runtime isolation check

Build a non-editor target or inspect its dependency graph. Successful editor compilation alone cannot prove that editor-only dependencies are absent from runtime code.

## Verification boundary

Use a clean editor-target build for API evidence and a runtime-target build for isolation evidence. Menu layout and workflow quality remain editor observations.
