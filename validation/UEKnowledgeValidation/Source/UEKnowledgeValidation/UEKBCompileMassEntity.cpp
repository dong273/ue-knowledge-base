#include "MassCommonFragments.h"
#include "MassEntityElementTypes.h"
#include "MassEntityManager.h"
#include "MassEntityQuery.h"
#include "MassExecutionContext.h"
#include "MassMovementFragments.h"
#include "MassProcessor.h"

// Validation ID: UEKB.Compile.MassEntity

namespace UEKBMassEntity
{
static_assert(TIsDerivedFrom<FTransformFragment, FMassFragment>::Value);
static_assert(TIsDerivedFrom<FMassVelocityFragment, FMassFragment>::Value);

void CompileQuerySurface(FMassEntityQuery& Query, FMassExecutionContext& Context)
{
    Query.AddRequirement<FTransformFragment>(EMassFragmentAccess::ReadOnly);
    Query.AddRequirement<FMassVelocityFragment>(EMassFragmentAccess::ReadWrite);
    Query.ForEachEntityChunk(Context, [](FMassExecutionContext& ChunkContext)
    {
        (void)ChunkContext.GetFragmentView<FTransformFragment>();
        (void)ChunkContext.GetMutableFragmentView<FMassVelocityFragment>();
        (void)ChunkContext.GetNumEntities();
    });
}

void CompileManagerSurface(
    FMassEntityManager& EntityManager,
    const FMassArchetypeHandle& Archetype)
{
    const FMassEntityHandle Entity = EntityManager.CreateEntity(Archetype);
    (void)EntityManager.IsEntityValid(Entity);
    EntityManager.DestroyEntity(Entity);
    (void)EntityManager.Defer();
}

void CompileProcessorSurface(UMassProcessor& Processor)
{
    Processor.SetProcessingPhase(EMassProcessingPhase::PrePhysics);
    (void)Processor.GetExecutionOrder();
}
} // namespace UEKBMassEntity
