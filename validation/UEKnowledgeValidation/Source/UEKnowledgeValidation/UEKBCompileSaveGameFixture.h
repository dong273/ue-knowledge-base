#pragma once

#include "GameFramework/SaveGame.h"
#include "UEKBCompileSaveGameFixture.generated.h"

// Validation ID: UEKB.Compile.SaveGameTypes

UCLASS()
class UUEKBSaveGameFixture : public USaveGame
{
    GENERATED_BODY()

public:
    UPROPERTY(SaveGame)
    int32 SchemaVersion = 1;

    UPROPERTY(SaveGame)
    TMap<FName, int32> ProgressById;
};
