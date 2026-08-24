#include "Interfaces/IPluginManager.h"
#include "PluginDescriptor.h"

// Validation ID: UEKB.Compile.PluginManager

namespace UEKBPluginManager
{
void CompilePluginManagerSurface(const FString& PluginName)
{
    TSharedPtr<IPlugin> Plugin = IPluginManager::Get().FindPlugin(PluginName);
    TArray<TSharedRef<IPlugin>> Enabled = IPluginManager::Get().GetEnabledPlugins();
    if (Plugin.IsValid())
    {
        const FPluginDescriptor& Descriptor = Plugin->GetDescriptor();
        (void)Descriptor.Modules;
        (void)Plugin->GetBaseDir();
        (void)Plugin->GetMountedAssetPath();
    }
    (void)Enabled;
}
} // namespace UEKBPluginManager
