---
description: Use for UE 5.7 AIController movement requests, Behavior Trees, blackboards, navigation-system queries, perception ownership, or EQS. Read the focused reference when the task is specifically BT or EQS.
---

# UE AI Navigation

Use this workflow to keep navigation requests, decision logic, and world-query ownership separate.

## Choose the control surface

- Use `AAIController` for possessed-pawn control and path-following requests.
- Use a Behavior Tree when decisions are authored as tree assets and blackboard state.
- Use EQS when the output is a scored set of world items rather than a direct movement command.
- Use `UNavigationSystemV1` for navigation-data queries such as projection and reachable-point lookup.

## Movement requests

`MoveTo`, `MoveToActor`, and `MoveToLocation` submit path-following requests. Their immediate result describes request submission; final movement completion is a separate controller/path-following event.

```cpp fragment
FAIMoveRequest Request;
Request.SetGoalLocation(TargetLocation);
Request.SetAcceptanceRadius(75.0f);
const FPathFollowingRequestResult Result = Controller->MoveTo(Request);
```

Keep the controller authoritative for the request and let the movement component move the pawn. A successful request is not proof that the pawn reached the goal.

## Behavior Tree ownership

`AAIController::RunBehaviorTree` accepts a `UBehaviorTree` asset. `UBehaviorTreeComponent::StartTree` is the component-level start surface. Blackboard keys are typed; use the matching `SetValueAsObject`, `SetValueAsVector`, `SetValueAsBool`, or other typed accessor.

See [Behavior Tree patterns](references/behavior-tree-patterns.md) for the focused contract.

## Navigation queries

Obtain the current navigation system through `FNavigationSystem::GetCurrent<UNavigationSystemV1>(World)`. Projection and reachable-point queries return explicit success values and output parameters; branch on the returned result.

```cpp fragment
UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
FNavLocation Projected;
const bool bProjected = Nav && Nav->ProjectPointToNavigation(Point, Projected);
```

## EQS queries

`UEnvQueryManager::RunEQSQuery` is the Blueprint-facing static launch surface. The query template, querier, run mode, and wrapper class are explicit inputs. Treat completion and item extraction as later steps.

See [EQS reference](references/eqs-reference.md) for the focused contract.

## Perception boundary

Perception supplies observations to an AI owner; it does not itself choose movement or guarantee a valid path. Record the sensed actor, sense class, age, and stimulus success before debugging downstream decisions.

## Verification boundary

Compile fixtures prove the public UE 5.7 types and calls used here. Navigation-data presence, path reachability, Behavior Tree asset correctness, and gameplay quality require project-specific runtime or human evidence.
