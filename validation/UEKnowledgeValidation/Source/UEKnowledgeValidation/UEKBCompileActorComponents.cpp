// Validation ID: UEKB.Compile.ActorComponents
#include "Components/ActorComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/SceneComponent.h"
#include "GameFramework/Actor.h"

static_assert(TIsDerivedFrom<USceneComponent, UActorComponent>::Value, "Scene components remain actor components");
static_assert(TIsDerivedFrom<UPrimitiveComponent, USceneComponent>::Value, "Primitive components remain scene components");

class AUEKBActorComponentProbe : public AActor
{
public:
    AUEKBActorComponentProbe()
    {
        Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
        SetRootComponent(Root);
        Logic = CreateDefaultSubobject<UActorComponent>(TEXT("Logic"));
        Root->SetupAttachment(GetRootComponent());
        PrimaryActorTick.bCanEverTick = true;
    }

    virtual void PostInitializeComponents() override
    {
        AActor::PostInitializeComponents();
    }

    virtual void BeginPlay() override
    {
        AActor::BeginPlay();
    }

    virtual void EndPlay(const EEndPlayReason::Type Reason) override
    {
        AActor::EndPlay(Reason);
    }

    static void ProbeRuntimeComponent(AActor* Owner, USceneComponent* RuntimePart)
    {
        Owner->AddInstanceComponent(RuntimePart);
        RuntimePart->RegisterComponent();
        RuntimePart->AttachToComponent(
            Owner->GetRootComponent(),
            FAttachmentTransformRules::KeepRelativeTransform);
        RuntimePart->Activate();
        (void)RuntimePart->GetOwner();
        (void)RuntimePart->GetAttachParent();
    }

private:
    TObjectPtr<USceneComponent> Root;
    TObjectPtr<UActorComponent> Logic;
};
