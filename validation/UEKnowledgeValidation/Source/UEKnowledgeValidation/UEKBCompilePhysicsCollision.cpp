#include "CollisionQueryParams.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/EngineTypes.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"

// Validation ID: UEKB.Compile.PhysicsCollision

namespace UEKBPhysicsCollision
{
void CompileCollisionState(AActor& Actor, UPrimitiveComponent& Component, ECollisionChannel Channel)
{
    Actor.SetActorEnableCollision(true);
    (void)Actor.GetActorEnableCollision();

    Component.SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Component.SetCollisionResponseToChannel(Channel, ECR_Block);
    Component.SetGenerateOverlapEvents(true);
    Component.SetNotifyRigidBodyCollision(true);
    (void)Component.GetCollisionEnabled();
    (void)Component.GetCollisionResponseToChannel(Channel);
}

void CompileSceneQueries(
    UWorld& World,
    AActor& Owner,
    const FVector& Start,
    const FVector& End,
    float Radius)
{
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(UEKBInteractionTrace), false);
    Params.AddIgnoredActor(&Owner);
    World.LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params);

    const FCollisionShape Shape = FCollisionShape::MakeSphere(Radius);
    World.SweepSingleByChannel(
        Hit,
        Start,
        End,
        FQuat::Identity,
        ECC_Visibility,
        Shape,
        Params
    );

    (void)Hit.GetActor();
    (void)Hit.GetComponent();
    (void)Hit.bStartPenetrating;
    (void)Hit.PenetrationDepth;
}
} // namespace UEKBPhysicsCollision
