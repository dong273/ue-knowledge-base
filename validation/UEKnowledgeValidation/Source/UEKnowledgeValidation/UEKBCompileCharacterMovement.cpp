#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Math/RotationMatrix.h"

// Validation ID: UEKB.Compile.CharacterMovement

namespace UEKBCharacterMovement
{
class FCustomMovementSignatureProbe : public UCharacterMovementComponent
{
protected:
    virtual void PhysCustom(float DeltaTime, int32 Iterations) override
    {
        UCharacterMovementComponent::PhysCustom(DeltaTime, Iterations);
    }

public:
    float ProbeSlideAlongSurface(
        const FVector& Delta,
        float Time,
        const FVector& Normal,
        FHitResult& Hit)
    {
        return SlideAlongSurface(Delta, Time, Normal, Hit, true);
    }
};

void CompileCharacterMovementSurface(
    ACharacter& Character,
    APawn& Pawn,
    UCharacterMovementComponent& Movement,
    const FVector2D& Input)
{
    Pawn.AddMovementInput(Pawn.GetActorForwardVector(), Input.Y);
    (void)Pawn.GetPendingMovementInputVector();
    (void)Pawn.GetLastMovementInputVector();
    (void)Pawn.ConsumeMovementInputVector();

    Movement.SetMovementMode(MOVE_Custom, 1);
    FFindFloorResult Floor;
    Movement.FindFloor(Character.GetActorLocation(), Floor, false);

    FHitResult Hit;
    const FVector Delta = FVector::ForwardVector;
    Movement.SafeMoveUpdatedComponent(Delta, FQuat::Identity, true, Hit);

    Character.LaunchCharacter(FVector::UpVector * 300.0f, false, true);
    Character.Jump();

    const FRotator YawOnly(0.0f, 45.0f, 0.0f);
    (void)FRotationMatrix(YawOnly).GetUnitAxis(EAxis::X);
    (void)FRotationMatrix(YawOnly).GetUnitAxis(EAxis::Y);
}

void CompileProtectedMovementSurface(
    FCustomMovementSignatureProbe& Movement,
    const FVector& Delta,
    FHitResult& Hit)
{
    Movement.ProbeSlideAlongSurface(Delta, 1.0f - Hit.Time, Hit.Normal, Hit);
}

void CompileObjectInitializerSurface(FObjectInitializer& ObjectInitializer)
{
    ObjectInitializer.SetDefaultSubobjectClass<UCharacterMovementComponent>(
        ACharacter::CharacterMovementComponentName
    );
}
} // namespace UEKBCharacterMovement
