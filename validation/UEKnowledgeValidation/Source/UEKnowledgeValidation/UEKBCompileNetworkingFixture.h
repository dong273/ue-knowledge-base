#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "UEKBCompileNetworkingFixture.generated.h"

UCLASS()
class AUEKBValidationRpcActor : public AActor
{
    GENERATED_BODY()

public:
    UFUNCTION(Server, Reliable, WithValidation)
    void ServerValidated(int32 Value);

    UFUNCTION(Server, Reliable)
    void ServerPlain(int32 Value);
};

UCLASS()
class AUEKBValidationReplicationActor : public AActor
{
    GENERATED_BODY()

public:
    AUEKBValidationReplicationActor();

    virtual void GetLifetimeReplicatedProps(
        TArray<FLifetimeProperty>& OutLifetimeProps) const override;

    UPROPERTY(ReplicatedUsing=OnRep_Health)
    int32 Health = 100;

    UPROPERTY(Replicated)
    int32 PrivateValue = 0;

    UFUNCTION()
    void OnRep_Health();

    void ProbeRegisteredSubobject(UObject* SubObject);
};
