---
description: Use for UE 5.7 Game Feature plugins, UGameFeaturesSubsystem state requests, UGameFeatureData actions, activation/deactivation cleanup, or modular gameplay integration. Treat experience-style layers as project architecture.
---

# UE Game Features

Use this workflow to separate plugin state, feature data, actions, and project-specific composition.

## Core ownership

`UGameFeaturesSubsystem` is an engine subsystem that manages Game Feature plugin state. `UGameFeatureData` is a primary data asset containing feature actions and primary-asset scan definitions. `UGameFeatureAction` is the lifecycle extension base.

## State requests

`LoadAndActivateGameFeaturePlugin` requests loading and activation for a plugin URL and reports completion through a delegate. `DeactivateGameFeaturePlugin` requests deactivation. Completion, failure, and cancellation must be handled explicitly.

```cpp fragment
UGameFeaturesSubsystem& Features = UGameFeaturesSubsystem::Get();
Features.LoadAndActivateGameFeaturePlugin(PluginURL, CompletionDelegate);
```

A submitted request is not proof that the plugin reached the active state.

## Action lifecycle

`UGameFeatureAction` exposes registering, loading, activating, deactivating, and unregistering hooks. Allocate activation-owned resources in the activation path and release them through the matching deactivation context.

## Feature data

`UGameFeatureData::GetActions` exposes configured actions. `GetPrimaryAssetTypesToScan` exposes the feature's asset-scan declarations. These are data contracts; actual asset discovery still depends on plugin and Asset Manager configuration.

## Module boundary

Runtime code using these public types depends on the `GameFeatures` module. Action implementations may require additional modules such as `ModularGameplay` or `DataRegistry`; declare only the APIs used by the module.

## Focused references

- [Game Feature patterns](references/game-feature-patterns.md) covers state and cleanup boundaries.
- [Experience-style project layer](references/experience-system.md) separates project architecture from engine API.

## Verification boundary

Compile evidence proves public types and calls. Plugin descriptor validity, state-machine completion, mounted content, action side effects, rollback, and player-visible behavior require project-specific runtime or human evidence.
