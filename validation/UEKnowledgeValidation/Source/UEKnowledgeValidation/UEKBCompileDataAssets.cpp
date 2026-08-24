// Validation ID: UEKB.Compile.DataAssets
#include "UEKBCompileDataAssetsFixture.h"

#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"

static void ProbeDataAssets(UUEKBItemDefinition* Definition)
{
    const FPrimaryAssetId AssetId = Definition->GetPrimaryAssetId();
    (void)AssetId.IsValid();

    FStreamableManager& Streamable = UAssetManager::GetStreamableManager();
    const TSharedPtr<FStreamableHandle> Handle = Streamable.RequestAsyncLoad(
        Definition->Icon.ToSoftObjectPath(),
        FStreamableDelegate());
    (void)Handle;
    (void)Definition->Icon.Get();
    (void)Definition->Icon.LoadSynchronous();
}
