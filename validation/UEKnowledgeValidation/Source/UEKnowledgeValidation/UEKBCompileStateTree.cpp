#include "Components/StateTreeComponent.h"
#include "MassStateTreeFragments.h"
#include "MassStateTreeProcessors.h"
#include "MassStateTreeSchema.h"
#include "MassStateTreeSubsystem.h"
#include "MassStateTreeTrait.h"
#include "MassStateTreeTypes.h"
#include "StateTree.h"
#include "StateTreeConditionBase.h"
#include "StateTreeEvaluatorBase.h"
#include "StateTreeEvents.h"
#include "StateTreeTaskBase.h"

// Validation ID: UEKB.Compile.StateTree

namespace UEKBStateTree
{
static_assert(TIsDerivedFrom<UStateTree, UDataAsset>::Value);
static_assert(TIsDerivedFrom<UStateTreeComponent, UBrainComponent>::Value);
static_assert(TIsDerivedFrom<FMassStateTreeTaskBase, FStateTreeTaskBase>::Value);
static_assert(TIsDerivedFrom<FMassStateTreeEvaluatorBase, FStateTreeEvaluatorBase>::Value);
static_assert(TIsDerivedFrom<FMassStateTreeConditionBase, FStateTreeConditionBase>::Value);
static_assert(TIsDerivedFrom<UMassStateTreeSchema, UStateTreeSchema>::Value);
static_assert(TIsDerivedFrom<UMassStateTreeTrait, UMassEntityTraitBase>::Value);
static_assert(TIsDerivedFrom<FMassStateTreeInstanceFragment, FMassFragment>::Value);
static_assert(TIsDerivedFrom<FMassStateTreeSharedFragment, FMassConstSharedFragment>::Value);
static_assert(TIsDerivedFrom<UMassStateTreeActivationProcessor, UMassProcessor>::Value);

void CompileComponentSurface(UStateTreeComponent& Component, const FGameplayTag EventTag)
{
    Component.SetStartLogicAutomatically(false);
    Component.StartLogic();
    Component.SendStateTreeEvent(EventTag, FConstStructView(), TEXT("UEKB"));
    Component.StopLogic(TEXT("UEKB validation"));
}

void CompileMassStateTreeSurface(UMassStateTreeSubsystem& Subsystem, const UStateTree& Tree)
{
    const FMassStateTreeInstanceHandle Handle = Subsystem.AllocateInstanceData(&Tree);
    (void)Subsystem.IsValidHandle(Handle);
    Subsystem.FreeInstanceData(Handle);
}
} // namespace UEKBStateTree
