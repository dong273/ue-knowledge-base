// Validation ID: UEKB.Compile.GasApi
#include "AbilitySystemComponent.h"
#include "Abilities/GameplayAbility.h"
#include "Abilities/Tasks/AbilityTask_PlayMontageAndWait.h"
#include "Abilities/Tasks/AbilityTask_WaitDelay.h"
#include "GameplayEffect.h"
#include "GameplayEffectTypes.h"

static_assert(TIsDerivedFrom<UAbilitySystemComponent, UActorComponent>::Value, "ASC must remain an actor component");
static_assert(TIsDerivedFrom<UGameplayAbility, UObject>::Value, "Gameplay abilities must remain UObject types");
static_assert(TIsDerivedFrom<UAbilityTask_WaitDelay, UAbilityTask>::Value, "WaitDelay must remain an ability task");
static_assert(TIsDerivedFrom<UAbilityTask_PlayMontageAndWait, UAbilityTask>::Value, "PlayMontageAndWait must remain an ability task");

class UUEKBValidationAbility : public UGameplayAbility
{
public:
    virtual void ActivateAbility(
        const FGameplayAbilitySpecHandle Handle,
        const FGameplayAbilityActorInfo* ActorInfo,
        const FGameplayAbilityActivationInfo ActivationInfo,
        const FGameplayEventData* TriggerEventData) override;

    virtual void EndAbility(
        const FGameplayAbilitySpecHandle Handle,
        const FGameplayAbilityActorInfo* ActorInfo,
        const FGameplayAbilityActivationInfo ActivationInfo,
        bool bReplicateEndAbility,
        bool bWasCancelled) override;

    void ProbeTaskSurface(UAnimMontage* Montage);
};

void UUEKBValidationAbility::ActivateAbility(
    const FGameplayAbilitySpecHandle Handle,
    const FGameplayAbilityActorInfo* ActorInfo,
    const FGameplayAbilityActivationInfo ActivationInfo,
    const FGameplayEventData* TriggerEventData)
{
    (void)Handle;
    (void)ActorInfo;
    (void)ActivationInfo;
    (void)TriggerEventData;
}

void UUEKBValidationAbility::EndAbility(
    const FGameplayAbilitySpecHandle Handle,
    const FGameplayAbilityActorInfo* ActorInfo,
    const FGameplayAbilityActivationInfo ActivationInfo,
    bool bReplicateEndAbility,
    bool bWasCancelled)
{
    UGameplayAbility::EndAbility(Handle, ActorInfo, ActivationInfo, bReplicateEndAbility, bWasCancelled);
}

void UUEKBValidationAbility::ProbeTaskSurface(UAnimMontage* Montage)
{
    UAbilityTask_WaitDelay* DelayTask = UAbilityTask_WaitDelay::WaitDelay(this, 0.1f);
    DelayTask->ReadyForActivation();
    UAbilityTask_PlayMontageAndWait* MontageTask =
        UAbilityTask_PlayMontageAndWait::CreatePlayMontageAndWaitProxy(this, NAME_None, Montage, 1.0f);
    MontageTask->ReadyForActivation();
}

static void UEKBValidateGasPointers(
    UAbilitySystemComponent* ASC,
    AActor* OwnerActor,
    AActor* AvatarActor,
    const FGameplayAttribute& Attribute,
    const FGameplayTagContainer* WithTags,
    TSubclassOf<UGameplayAbility> AbilityClass,
    TSubclassOf<UGameplayEffect> EffectClass,
    const FGameplayTag& DataTag)
{
    if (ASC)
    {
        ASC->SetReplicationMode(EGameplayEffectReplicationMode::Mixed);
        ASC->InitAbilityActorInfo(OwnerActor, AvatarActor);
        (void)ASC->GetNumericAttribute(Attribute);
        ASC->CancelAbilities(WithTags);
        ASC->TryActivateAbilitiesByTag(*WithTags);
        (void)ASC->GiveAbility(FGameplayAbilitySpec(AbilityClass, 1, 0));
        FGameplayEffectSpecHandle Spec = ASC->MakeOutgoingSpec(EffectClass, 1.0f, ASC->MakeEffectContext());
        if (Spec.IsValid())
        {
            Spec.Data->SetSetByCallerMagnitude(DataTag, 1.0f);
            (void)ASC->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get());
        }
    }
}
