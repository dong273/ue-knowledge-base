#include "Modules/ModuleManager.h"

#include "AbilitySystemComponent.h"
#include "Blueprint/UserWidget.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Character.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "UEKBCompileNetworkingFixture.h"
#include "UEKBCompileSaveGameFixture.h"

// Validation IDs: UEKB.Compile.ActorCollision and UEKnowledgeValidation.*

IMPLEMENT_MODULE(FDefaultModuleImpl, UEKnowledgeValidation)

#if WITH_DEV_AUTOMATION_TESTS

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FUEKBActorCollisionEnableState,
    "UEKnowledgeValidation.ActorCollisionEnableState",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter
)

bool FUEKBActorCollisionEnableState::RunTest(const FString& Parameters)
{
    (void)Parameters;
    AActor* Actor = NewObject<AActor>(GetTransientPackage());
    TestNotNull(TEXT("A transient actor can be created"), Actor);
    if (!Actor)
    {
        return false;
    }

    Actor->SetActorEnableCollision(false);
    TestFalse(
        TEXT("Actor-level collision readback follows SetActorEnableCollision(false)"),
        Actor->GetActorEnableCollision()
    );

    Actor->SetActorEnableCollision(true);
    TestTrue(
        TEXT("Actor-level collision readback follows SetActorEnableCollision(true)"),
        Actor->GetActorEnableCollision()
    );
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FUEKBActorReplicationState,
    "UEKnowledgeValidation.ActorReplicationState",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter
)

bool FUEKBActorReplicationState::RunTest(const FString& Parameters)
{
    (void)Parameters;
    const FName WorldName = MakeUniqueObjectName(
        nullptr,
        UWorld::StaticClass(),
        TEXT("UEKBReplicationStateWorld"),
        EUniqueObjectNameOptions::GloballyUnique
    );
    FWorldContext& WorldContext = GEngine->CreateNewWorldContext(EWorldType::Game);
    UWorld* World = UWorld::CreateWorld(EWorldType::Game, false, WorldName, GetTransientPackage());
    TestNotNull(TEXT("A validation world can be created"), World);
    if (!World)
    {
        return false;
    }
    World->AddToRoot();
    WorldContext.SetCurrentWorld(World);
    World->InitializeActorsForPlay(FURL());

    AUEKBValidationReplicationActor* Actor = World->SpawnActor<AUEKBValidationReplicationActor>();
    TestNotNull(TEXT("A world-owned actor can be spawned for replication state"), Actor);
    if (!Actor)
    {
        World->DestroyWorld(true);
        GEngine->DestroyWorldContext(World);
        World->RemoveFromRoot();
        return false;
    }
    Actor->SetReplicates(true);
    TestTrue(TEXT("SetReplicates(true) is observable through GetIsReplicated"), Actor->GetIsReplicated());
    Actor->SetReplicates(false);
    TestFalse(TEXT("SetReplicates(false) is observable through GetIsReplicated"), Actor->GetIsReplicated());

    World->DestroyWorld(true);
    GEngine->DestroyWorldContext(World);
    World->RemoveFromRoot();
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FUEKBGasComponentReplicationState,
    "UEKnowledgeValidation.GasComponentReplicationState",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter
)

bool FUEKBGasComponentReplicationState::RunTest(const FString& Parameters)
{
    (void)Parameters;
    UAbilitySystemComponent* Component = NewObject<UAbilitySystemComponent>(GetTransientPackage());
    TestNotNull(TEXT("A transient AbilitySystemComponent can be created"), Component);
    if (!Component)
    {
        return false;
    }
    Component->SetIsReplicated(true);
    TestTrue(TEXT("AbilitySystemComponent replication state is enabled"), Component->GetIsReplicated());
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FUEKBWidgetObjectCreation,
    "UEKnowledgeValidation.WidgetObjectCreation",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter
)

bool FUEKBWidgetObjectCreation::RunTest(const FString& Parameters)
{
    (void)Parameters;
    TestTrue(
        TEXT("UserWidget remains a Widget type; concrete widgets require a project class"),
        UUserWidget::StaticClass()->IsChildOf(UWidget::StaticClass())
    );
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FUEKBGameplayFrameworkTypeSurface,
    "UEKnowledgeValidation.GameplayFrameworkTypeSurface",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter
)

bool FUEKBGameplayFrameworkTypeSurface::RunTest(const FString& Parameters)
{
    (void)Parameters;
    TestTrue(TEXT("ACharacter derives from APawn"), ACharacter::StaticClass()->IsChildOf(APawn::StaticClass()));
    TestTrue(TEXT("AActor is a UObject"), AActor::StaticClass()->IsChildOf(UObject::StaticClass()));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FUEKBSaveGameObjectCreation,
    "UEKnowledgeValidation.SaveGameObjectCreation",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter
)

bool FUEKBSaveGameObjectCreation::RunTest(const FString& Parameters)
{
    (void)Parameters;
    USaveGame* Payload = UGameplayStatics::CreateSaveGameObject(
        UUEKBSaveGameFixture::StaticClass()
    );
    TestNotNull(TEXT("CreateSaveGameObject returns the requested fixture type"), Payload);
    TestTrue(
        TEXT("The created save object has the requested class"),
        Payload && Payload->IsA<UUEKBSaveGameFixture>()
    );
    return true;
}

#endif
