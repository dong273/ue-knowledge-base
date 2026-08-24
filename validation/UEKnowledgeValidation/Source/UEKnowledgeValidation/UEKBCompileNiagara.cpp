#include "NiagaraComponent.h"
#include "NiagaraDataInterface.h"
#include "NiagaraDataInterfaceArrayFloat.h"
#include "NiagaraDataInterfaceArrayInt.h"
#include "NiagaraDataInterfaceSkeletalMesh.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "NiagaraTypes.h"

// Validation ID: UEKB.Compile.Niagara

namespace UEKBNiagara
{
void CompileComponentSurface(UNiagaraComponent& Component, UNiagaraSystem& System)
{
    Component.SetAsset(&System);
    Component.SetVariableFloat(TEXT("User.Float"), 1.0f);
    Component.SetVariableVec3(TEXT("User.Vector"), FVector::OneVector);
    Component.SetVariableBool(TEXT("User.Bool"), true);
    Component.Activate();
    Component.Deactivate();
}

void CompileSpawnAndInterfaceSurface(
    UObject& WorldContext,
    UNiagaraSystem& System,
    UNiagaraComponent& Component)
{
    (void)UNiagaraFunctionLibrary::SpawnSystemAtLocation(
        &WorldContext,
        &System,
        FVector::ZeroVector);
    (void)UNiagaraFunctionLibrary::GetSkeletalMeshDataInterface(
        &Component,
        TEXT("User.SkeletalMesh"));

    static_assert(TIsDerivedFrom<UNiagaraDataInterfaceSkeletalMesh, UNiagaraDataInterface>::Value);
    static_assert(TIsDerivedFrom<UNiagaraDataInterfaceArrayFloat, UNiagaraDataInterface>::Value);
    static_assert(TIsDerivedFrom<UNiagaraDataInterfaceArrayInt32, UNiagaraDataInterface>::Value);
    (void)sizeof(FNiagaraVariable);
}
} // namespace UEKBNiagara
