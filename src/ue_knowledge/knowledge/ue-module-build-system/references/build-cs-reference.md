# Build.cs Reference

## Minimal runtime module

This fragment is represented by the validation project's runtime `ModuleRules` fixture.

```csharp fragment
public class UEKnowledgeValidation : ModuleRules
{
    public UEKnowledgeValidation(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[]
        {
            "Core", "CoreUObject", "Engine"
        });
        PrivateDependencyModuleNames.AddRange(new[]
        {
            "GameplayAbilities", "GameplayTags", "GameplayTasks"
        });
    }
}
```

## Editor companion module

An Editor module can privately depend on the runtime module and `UnrealEd`. Keeping that
edge in the Editor module prevents a game target from inheriting editor-only code.

```csharp fragment
PrivateDependencyModuleNames.AddRange(new[]
{
    "UEKnowledgeValidation",
    "UnrealEd"
});
```

## Public API rule

If a public header exposes a type from another module, that dependency must be visible to
consumers. If only private implementation includes the type, keep the dependency private.
Verify the actual include owner instead of guessing from the C++ namespace or class prefix.

## Platform condition

```csharp fragment
if (Target.Platform == UnrealTargetPlatform.Win64)
{
    PrivateDefinitions.Add("UEKB_PLATFORM_WINDOWS=1");
}
```

The positive fixture compiles this condition. Platform packaging behavior requires its
own target/package test.
