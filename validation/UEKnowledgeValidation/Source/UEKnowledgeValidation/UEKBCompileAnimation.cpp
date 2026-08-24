#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimNotifies/AnimNotify.h"
#include "Animation/AnimNotifies/AnimNotifyState.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Pawn.h"

// Validation ID: UEKB.Compile.Animation

namespace UEKBAnimation
{
void CompileAnimationSurface(
    UAnimInstance& AnimInstance,
    UAnimMontage& Montage,
    UCharacterMovementComponent& Movement)
{
    (void)AnimInstance.Montage_Play(&Montage);
    (void)AnimInstance.Montage_IsPlaying(&Montage);
    AnimInstance.Montage_Stop(0.2f, &Montage);
    (void)AnimInstance.TryGetPawnOwner();
    AnimInstance.SetRootMotionMode(ERootMotionMode::RootMotionFromMontagesOnly);
    (void)Movement.IsFalling();
}

void CompileNotifyOverloads()
{
    using FNotify = void (UAnimNotify::*)(
        USkeletalMeshComponent*,
        UAnimSequenceBase*,
        const FAnimNotifyEventReference&);
    using FNotifyBegin = void (UAnimNotifyState::*)(
        USkeletalMeshComponent*,
        UAnimSequenceBase*,
        float,
        const FAnimNotifyEventReference&);
    using FNotifyTick = FNotifyBegin;
    using FNotifyEnd = void (UAnimNotifyState::*)(
        USkeletalMeshComponent*,
        UAnimSequenceBase*,
        const FAnimNotifyEventReference&);

    FNotify Notify = static_cast<FNotify>(&UAnimNotify::Notify);
    FNotifyBegin Begin = static_cast<FNotifyBegin>(&UAnimNotifyState::NotifyBegin);
    FNotifyTick Tick = static_cast<FNotifyTick>(&UAnimNotifyState::NotifyTick);
    FNotifyEnd End = static_cast<FNotifyEnd>(&UAnimNotifyState::NotifyEnd);
    (void)Notify;
    (void)Begin;
    (void)Tick;
    (void)End;
}
} // namespace UEKBAnimation
