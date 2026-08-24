---
title: ue-project-creation
description: Standard source workflow for creating and validating an Unreal Engine 5.7 C++ project on Windows.
tags: [ue, project, creation, setup]
---

# UE Project Creation

## Project descriptor

A `.uproject` JSON descriptor identifies the engine association, modules, and plugins.
Module entries must agree with the Source directory and module rules.

```json config
{
  "FileVersion": 3,
  "EngineAssociation": "5.7",
  "Modules": [
    {"Name": "ExampleGame", "Type": "Runtime", "LoadingPhase": "Default"}
  ]
}
```

## Source layout

A blank project can remain content-only, while a minimal C++ project has a target
file, an editor target, and a module directory with
`<Module>.Build.cs`, public/private headers as needed, and the module implementation.
The module name must match across descriptor, targets, rules, and implementation macro.

## Generate project files

On Windows, use the engine's `GenerateProjectFiles.bat` or UnrealVersionSelector for
the selected engine installation. The following is a command template, not a literal
machine path.

```powershell command
& '<ENGINE_ROOT>\Engine\Build\BatchFiles\GenerateProjectFiles.bat' -project='<PROJECT_ROOT>\ExampleGame.uproject' -game
```

## Build with UBT

Build the editor target through the engine batch wrapper. A successful target build is
the compile gate; IDE project generation alone is not compilation.
Recompile after changing native sources or module rules before treating editor startup
as validation.

```powershell command
& '<ENGINE_ROOT>\Engine\Build\BatchFiles\Build.bat' ExampleGameEditor Win64 Development -Project='<PROJECT_ROOT>\ExampleGame.uproject' -WaitMutex
```

## Editor and runtime validation

Open the exact `.uproject`, confirm the intended engine version, then run the project's
automation or smoke tests. Project creation is not complete merely because files exist
or the editor process starts.

## Path handling

Quote paths and pass explicit project/engine roots. When a tool fails on a path, record
the failing tool and diagnostic before moving the project; do not claim all non-ASCII
paths are unsupported from one failure.

## Scope boundary

Templates and plugin selections are project decisions. This guide defines the source
and build contract but does not choose gameplay features or acceptance criteria.
