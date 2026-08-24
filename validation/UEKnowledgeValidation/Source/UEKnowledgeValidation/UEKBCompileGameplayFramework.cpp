// Validation ID: UEKB.Compile.GameplayFramework
#include "GameFramework/Character.h"
#include "GameFramework/GameMode.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/GameStateBase.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerState.h"
#include "Engine/GameInstance.h"

static_assert(TIsDerivedFrom<ACharacter, APawn>::Value, "ACharacter must remain an APawn type");
static_assert(TIsDerivedFrom<APlayerController, AController>::Value, "APlayerController must remain an AController type");
static_assert(TIsDerivedFrom<AGameMode, AGameModeBase>::Value, "AGameMode must remain a GameModeBase type");
static_assert(TIsDerivedFrom<AGameStateBase, AInfo>::Value, "GameStateBase must remain an Info actor type");
static_assert(TIsDerivedFrom<APlayerState, AInfo>::Value, "PlayerState must remain an Info actor type");
static_assert(TIsDerivedFrom<UGameInstance, UObject>::Value, "GameInstance must remain a UObject type");

static void ProbeGameplayFramework(APlayerController* Controller, AGameModeBase* GameMode)
{
    (void)Controller->GetPawn();
    (void)Controller->PlayerState;
    GameMode->RestartPlayer(Controller);
}
