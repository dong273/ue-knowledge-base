---
title: ue-module-build-system
description: Covers Build.cs, Target.cs, Unreal modules, dependency visibility, IWYU, runtime/editor separation, or UBT diagnostics.
---

# UE Module and Build System

Use the Unreal Build Tool (UBT) module graph as the source of dependency visibility.
Identify the header being included, the module that owns it, and whether the include is
part of this module's public API before editing a `Build.cs` file.

## Public and private dependencies

Put a dependency in `PublicDependencyModuleNames` when this module's public headers
expose that dependency. Put an implementation-only dependency in
`PrivateDependencyModuleNames`. A transitive include that happens to compile is not a
declared dependency contract.

The following is a `ModuleRules` fragment compiled by the runtime fixture.

```csharp fragment
PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine" });
PrivateDependencyModuleNames.AddRange(new[] { "GameplayAbilities" });
```

## Runtime and editor modules

Do not add editor-only modules such as `UnrealEd` to a runtime module that must build for
game targets. Put editor code in an Editor module and make that module privately depend
on the runtime module plus its editor dependencies.

## IWYU and includes

Include the header that owns the symbol and declare the module that owns that header.
Do not repair a missing dependency with broad `PublicIncludePaths`, parent-directory
relative includes, or reliance on a shared PCH.

## Platform conditions

Use `Target.Platform` conditions only for genuinely platform-specific dependencies or
definitions. Keep portable dependencies outside the branch so every target sees the
same base module contract.

## Validation boundary

A clean runtime/editor target build proves the positive module matrix. A negative probe
must fail for the registered reason and must never be exported as a successful validation
ID. Packaging and runtime loading remain separate checks.

## References

- `references/build-cs-reference.md`
- `references/common-build-errors.md`
- `references/windows-non-ascii-project-paths.md`
