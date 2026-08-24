#include "Components/AudioComponent.h"
#include "Components/SceneComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

// Validation ID: UEKB.Compile.Audio

namespace UEKBAudio
{
void CompileComponentSurface(UAudioComponent& Component, USoundBase& Sound)
{
    Component.SetSound(&Sound);
    Component.SetVolumeMultiplier(0.8f);
    Component.Play();
    Component.FadeIn(0.25f, 1.0f);
    Component.FadeOut(0.25f, 0.0f);
    Component.Stop();
}

void CompileGameplayStaticsSurface(
    UObject& WorldContext,
    USoundBase& Sound,
    USceneComponent& AttachComponent)
{
    UGameplayStatics::PlaySoundAtLocation(
        &WorldContext,
        &Sound,
        FVector::ZeroVector,
        FRotator::ZeroRotator);
    (void)UGameplayStatics::SpawnSoundAttached(
        &Sound,
        &AttachComponent,
        NAME_None,
        FVector::ZeroVector,
        FRotator::ZeroRotator,
        EAttachLocation::KeepRelativeOffset);
}
} // namespace UEKBAudio
