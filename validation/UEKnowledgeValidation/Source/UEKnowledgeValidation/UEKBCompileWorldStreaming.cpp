#include "Engine/LevelStreaming.h"
#include "Engine/LevelStreamingDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "Subsystems/WorldSubsystem.h"
#include "WorldPartition/WorldPartitionSubsystem.h"

// Validation ID: UEKB.Compile.WorldStreaming

namespace UEKBWorldStreaming
{
static_assert(TIsDerivedFrom<UWorldPartitionSubsystem, UTickableWorldSubsystem>::Value);
static_assert(TIsDerivedFrom<UWorldSubsystem, USubsystem>::Value);
static_assert(TIsDerivedFrom<ULevelStreamingDynamic, ULevelStreaming>::Value);

void CompileStreamingStateSurface(ULevelStreaming& StreamingLevel)
{
    (void)StreamingLevel.GetLevelStreamingState();
    StreamingLevel.SetShouldBeLoaded(true);
    StreamingLevel.SetShouldBeVisible(true);
}

void CompileLatentStreamingSurface(
    UObject& WorldContext,
    const FName LevelName,
    FLatentActionInfo LatentInfo)
{
    UGameplayStatics::LoadStreamLevel(
        &WorldContext,
        LevelName,
        true,
        false,
        LatentInfo);
    UGameplayStatics::UnloadStreamLevel(
        &WorldContext,
        LevelName,
        LatentInfo,
        false);
}

void CompileDynamicInstanceSurface(UObject& WorldContext, const FString& PackageName)
{
    bool bRequestCreated = false;
    (void)ULevelStreamingDynamic::LoadLevelInstance(
        &WorldContext,
        PackageName,
        FVector::ZeroVector,
        FRotator::ZeroRotator,
        bRequestCreated);
}
} // namespace UEKBWorldStreaming
