# Game Feature Lifecycle Patterns

This page covers stable UE 5.7 lifecycle boundaries.

## Plugin URL boundary

Game Feature state requests identify a plugin by URL. Resolve or obtain the URL through the subsystem/project policy used by the project; do not substitute a content path without verifying the expected protocol.

## Load and activate

`UGameFeaturesSubsystem::LoadAndActivateGameFeaturePlugin` is asynchronous and reports through `FGameFeaturePluginLoadComplete`. Branch on the completion result before depending on feature content or actions.

## Deactivate

`DeactivateGameFeaturePlugin` begins the matching deactivation path. Actions must release activation-owned registrations, components, delegates, and other resources before deactivation is considered complete.

## Action context

Override the context-aware `OnGameFeatureActivating(FGameFeatureActivatingContext&)` and `OnGameFeatureDeactivating(FGameFeatureDeactivatingContext&)` surfaces when cleanup participates in the feature state transition.

```cpp fragment
void UMyFeatureAction::OnGameFeatureActivating(FGameFeatureActivatingContext& Context)
{
    Super::OnGameFeatureActivating(Context);
    // register activation-owned resources
}
```

## Built-in action boundary

`UGameFeatureAction_AddComponents` is a built-in action type for component requests. Its presence does not prove that an arbitrary Actor class, world, or network role received a component; validate the configured action in the target runtime.

## Validation checklist

- Capture plugin URL and requested destination state.
- Inspect completion result before using feature content.
- Pair every activation-owned registration with deactivation cleanup.
- Exercise repeated activate/deactivate cycles.
- Verify server/client behavior in the intended network topology.
