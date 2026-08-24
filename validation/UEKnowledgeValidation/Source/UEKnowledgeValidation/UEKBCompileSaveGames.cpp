#include "Kismet/GameplayStatics.h"
#include "UEKBCompileSaveGameFixture.h"

// Validation ID: UEKB.Compile.SaveGameApi

namespace UEKBSaveGames
{
void CompileSaveGameSurface(
    UUEKBSaveGameFixture& Payload,
    const FString& SlotName,
    int32 UserIndex)
{
    USaveGame* Created = UGameplayStatics::CreateSaveGameObject(
        UUEKBSaveGameFixture::StaticClass()
    );
    (void)Cast<UUEKBSaveGameFixture>(Created);
    (void)UGameplayStatics::SaveGameToSlot(&Payload, SlotName, UserIndex);
    (void)UGameplayStatics::DoesSaveGameExist(SlotName, UserIndex);
    (void)UGameplayStatics::LoadGameFromSlot(SlotName, UserIndex);

    FAsyncSaveGameToSlotDelegate SavedDelegate;
    UGameplayStatics::AsyncSaveGameToSlot(
        &Payload,
        SlotName,
        UserIndex,
        MoveTemp(SavedDelegate)
    );

    FAsyncLoadGameFromSlotDelegate LoadedDelegate;
    UGameplayStatics::AsyncLoadGameFromSlot(
        SlotName,
        UserIndex,
        MoveTemp(LoadedDelegate)
    );
}
} // namespace UEKBSaveGames
