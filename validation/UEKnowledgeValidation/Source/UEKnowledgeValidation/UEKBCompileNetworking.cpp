// Validation ID: UEKB.Compile.NetworkingRpc
#include "GameFramework/Actor.h"
#include "Net/Serialization/FastArraySerializer.h"
#include "Net/UnrealNetwork.h"
#include "UEKBCompileNetworkingFixture.h"

static_assert(TIsDerivedFrom<AActor, UObject>::Value, "AActor must remain a UObject type");
static_assert(sizeof(FDoRepLifetimeParams) > 0, "replication lifetime parameters must be available");

struct FUEKBValidatedFastArrayItem : public FFastArraySerializerItem
{
    int32 Value = 0;
};

struct FUEKBValidatedFastArray : public FFastArraySerializer
{
    TArray<FUEKBValidatedFastArrayItem> Items;

    void ProbeDirtyMarking()
    {
        Items.Emplace();
        MarkItemDirty(Items[0]);
        MarkArrayDirty();
    }
};

void AUEKBValidationRpcActor::ServerValidated_Implementation(int32 Value)
{
    (void)Value;
}

bool AUEKBValidationRpcActor::ServerValidated_Validate(int32 Value)
{
    return Value >= 0;
}

void AUEKBValidationRpcActor::ServerPlain_Implementation(int32 Value)
{
    (void)Value;
}

AUEKBValidationReplicationActor::AUEKBValidationReplicationActor()
{
    bReplicates = true;
    SetReplicateMovement(true);
}

void AUEKBValidationReplicationActor::GetLifetimeReplicatedProps(
    TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AUEKBValidationReplicationActor, Health);
    DOREPLIFETIME_CONDITION(AUEKBValidationReplicationActor, PrivateValue, COND_OwnerOnly);
}

void AUEKBValidationReplicationActor::OnRep_Health()
{
}

void AUEKBValidationReplicationActor::ProbeRegisteredSubobject(UObject* SubObject)
{
    AddReplicatedSubObject(SubObject, COND_None);
    RemoveReplicatedSubObject(SubObject);
}
