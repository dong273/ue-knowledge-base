---
description: Use for UE 5.7 plugin discovery, descriptor inspection, project enablement, module dependencies, compatibility checks, and packaging verification.
---

# UE Plugin Installation

Use this workflow to distinguish plugin discovery, project enablement, module dependencies, loading, and packaged availability.

## Discover installed plugins

IPluginManager::Get returns the plugin manager. FindPlugin returns a shared plugin pointer by name, and GetEnabledPlugins enumerates enabled plugins.

```cpp fragment
TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(PluginName);
if (!Plugin.IsValid())
{
    return;
}
```

## Inspect descriptors

IPlugin exposes GetDescriptor, GetBaseDir, and GetMountedAssetPath. FPluginDescriptor contains plugin metadata and module descriptors. Do not infer compatibility from a friendly name alone.

## Enable for a project

A project plugin reference belongs in the Plugins array of the .uproject file.

```json config
{
  "Name": "PluginName",
  "Enabled": true
}
```

Project enablement does not automatically add a C++ module dependency.

## Add module dependencies

A C++ module that includes plugin public headers must add the required plugin module to its Build.cs dependency list. Keep editor-only plugin modules out of runtime modules.

## Compatibility checks

Verify engine version support, target platform, plugin modules, loading phases, dependencies, source or binary availability, and licensing. Rebuild source plugins with the target toolchain.

## Packaging boundary

Editor discovery and successful PIE loading do not prove a plugin is included or functional in a packaged target. Run the target build and inspect staging or runtime logs.

## Time-sensitive discovery

- [Time-sensitive plugin discovery](references/free-ue57-plugins-2026.md)

## Verification boundary

Compile a public plugin-manager probe and the actual dependent module. Runtime-test loading where applicable. Marketplace availability, licensing, and packaged behavior need current external and target-build evidence.
