#include "Camera/CameraComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/PostProcessVolume.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialParameterCollection.h"

// Validation ID: UEKB.Compile.MaterialsRendering

namespace UEKBMaterialsRendering
{
void CompileMaterialSurface(
    UObject& WorldContext,
    UPrimitiveComponent& Primitive,
    UMaterialInterface& SourceMaterial,
    UMaterialParameterCollection& Collection,
    UTexture& Texture)
{
    UMaterialInstanceDynamic* MID =
        Primitive.CreateDynamicMaterialInstance(0, &SourceMaterial);
    if (MID)
    {
        MID->SetScalarParameterValue(TEXT("Scalar"), 1.0f);
        MID->SetVectorParameterValue(TEXT("Tint"), FLinearColor::White);
        MID->SetTextureParameterValue(TEXT("Texture"), &Texture);
    }
    UKismetMaterialLibrary::SetScalarParameterValue(
        &WorldContext, &Collection, TEXT("GlobalScalar"), 1.0f);
    UKismetMaterialLibrary::SetVectorParameterValue(
        &WorldContext, &Collection, TEXT("GlobalVector"), FLinearColor::White);
}

void CompilePostProcessSurface(
    UCameraComponent& Camera,
    APostProcessVolume& Volume,
    TScriptInterface<IBlendableInterface> Blendable)
{
    Camera.SetPostProcessBlendWeight(1.0f);
    Camera.AddOrUpdateBlendable(Blendable, 1.0f);
    Volume.BlendWeight = 1.0f;
    Volume.bUnbound = true;
    (void)Volume.Settings;
}
} // namespace UEKBMaterialsRendering
