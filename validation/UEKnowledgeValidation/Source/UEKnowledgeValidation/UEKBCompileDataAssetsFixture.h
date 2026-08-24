// Validation ID: UEKB.Compile.DataAssetTypes
#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "Engine/DataTable.h"
#include "Engine/Texture2D.h"
#include "UEKBCompileDataAssetsFixture.generated.h"

USTRUCT(BlueprintType)
struct FUEKBItemRow : public FTableRowBase
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere)
    int32 Cost = 0;
};

UCLASS(BlueprintType)
class UUEKBItemDefinition : public UPrimaryDataAsset
{
    GENERATED_BODY()

public:
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly)
    FText DisplayName;

    UPROPERTY(EditDefaultsOnly)
    TSoftObjectPtr<UTexture2D> Icon;

    UPROPERTY(EditDefaultsOnly)
    FDataTableRowHandle ItemRow;
};
