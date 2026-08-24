#include "AIController.h"
#include "AITypes.h"
#include "BehaviorTree/BehaviorTree.h"
#include "BehaviorTree/BehaviorTreeComponent.h"
#include "BehaviorTree/BlackboardComponent.h"
#include "EnvironmentQuery/EnvQuery.h"
#include "EnvironmentQuery/EnvQueryInstanceBlueprintWrapper.h"
#include "EnvironmentQuery/EnvQueryManager.h"
#include "Navigation/PathFollowingComponent.h"
#include "NavigationSystem.h"

// Validation ID: UEKB.Compile.AINavigation

namespace UEKBAINavigation
{
void CompileMovementAndTreeSurface(
    AAIController& Controller,
    UBehaviorTree& Tree,
    UBehaviorTreeComponent& TreeComponent,
    UBlackboardComponent& Blackboard,
    const FVector& Goal)
{
    FAIMoveRequest Request;
    Request.SetGoalLocation(Goal);
    Request.SetAcceptanceRadius(75.0f);
    (void)Controller.MoveTo(Request);
    (void)Controller.RunBehaviorTree(&Tree);
    TreeComponent.StartTree(Tree, EBTExecutionMode::Looped);
    Blackboard.SetValueAsVector(TEXT("Goal"), Goal);
    Blackboard.SetValueAsBool(TEXT("Alert"), true);
}

void CompileNavigationAndEqsSurface(
    UWorld& World,
    UObject& Querier,
    UEnvQuery& QueryTemplate,
    const FVector& Point)
{
    UNavigationSystemV1* Navigation =
        FNavigationSystem::GetCurrent<UNavigationSystemV1>(&World);
    FNavLocation Projected;
    if (Navigation)
    {
        (void)Navigation->ProjectPointToNavigation(Point, Projected);
    }

    (void)UEnvQueryManager::RunEQSQuery(
        &World,
        &QueryTemplate,
        &Querier,
        EEnvQueryRunMode::SingleResult,
        UEnvQueryInstanceBlueprintWrapper::StaticClass());
}
} // namespace UEKBAINavigation
