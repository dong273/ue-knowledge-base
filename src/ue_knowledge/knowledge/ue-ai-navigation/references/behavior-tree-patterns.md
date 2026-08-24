# Behavior Tree Contracts

This page covers stable UE 5.7 Behavior Tree and blackboard API boundaries.

## Controller entry point

`AAIController::RunBehaviorTree` takes a `UBehaviorTree*` and returns whether the controller could run it. The asset and controller still need project-specific runtime validation.

```cpp fragment
const bool bStarted = Controller->RunBehaviorTree(BehaviorTreeAsset);
```

## Component entry point

`UBehaviorTreeComponent::StartTree` takes a `UBehaviorTree&` and an `EBTExecutionMode`. `StopTree` and restart behavior belong to the component lifecycle; centralize those calls in the AI owner.

```cpp fragment
BehaviorComp->StartTree(*BehaviorTreeAsset, EBTExecutionMode::Looped);
```

## Blackboard typing

`UBlackboardComponent` exposes typed name-based accessors. Match the key definition and accessor type; a key name alone does not carry its expected value type.

```cpp fragment
Blackboard->SetValueAsObject(TargetKey, TargetActor);
Blackboard->SetValueAsVector(LocationKey, TargetLocation);
Blackboard->SetValueAsBool(AlertKey, true);
```

## Task result boundary

Behavior Tree task completion is distinct from starting an asynchronous gameplay action. A task that launches movement, EQS, or another latent operation must finish or abort through the task's supported completion path after that operation reports back.

## Asset and runtime boundary

Source and compile evidence can prove class, method, and enum availability. Tree topology, decorator abort policy, blackboard asset compatibility, and observed task ordering require an asset-aware runtime test.

## Review checklist

- Identify the controller, tree asset, component, and blackboard owner.
- Match each blackboard key with its declared type.
- Separate request submission from asynchronous completion.
- Capture abort and restart policy in the project test.
