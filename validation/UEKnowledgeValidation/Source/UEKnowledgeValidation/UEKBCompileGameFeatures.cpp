#include "GameFeatureAction.h"
#include "GameFeatureAction_AddComponents.h"
#include "GameFeatureData.h"
#include "GameFeaturesSubsystem.h"

// Validation ID: UEKB.Compile.GameFeatures

namespace UEKBGameFeatures
{
static_assert(TIsDerivedFrom<UGameFeatureData, UPrimaryDataAsset>::Value);
static_assert(TIsDerivedFrom<UGameFeatureAction, UObject>::Value);
static_assert(TIsDerivedFrom<UGameFeatureAction_AddComponents, UGameFeatureAction>::Value);
static_assert(TIsDerivedFrom<UGameFeaturesSubsystem, UEngineSubsystem>::Value);

void CompileSubsystemSurface(const FString& PluginUrl)
{
    UGameFeaturesSubsystem& Features = UGameFeaturesSubsystem::Get();
    FGameFeaturePluginLoadComplete Completion;
    Features.LoadAndActivateGameFeaturePlugin(PluginUrl, Completion);
    Features.DeactivateGameFeaturePlugin(PluginUrl);
}

void CompileDataSurface(const UGameFeatureData& FeatureData)
{
    (void)FeatureData.GetActions();
    (void)FeatureData.GetPrimaryAssetTypesToScan();
}
} // namespace UEKBGameFeatures
