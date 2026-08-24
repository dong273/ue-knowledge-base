---
description: Use for UE 5.7 StateTree assets, UStateTreeComponent lifecycle, tasks, evaluators, conditions, events, schemas, or Mass StateTree integration. Read the Mass reference only for entity-scale execution.
---

# UE StateTree

Use this workflow to separate the StateTree asset, execution owner, node contracts, and project-specific behavior evidence.

## Asset and component

`UStateTree` is a `UDataAsset` in `StateTreeModule`. `UStateTreeComponent` is a `UBrainComponent` in `GameplayStateTreeModule`; it owns component-style execution and implements the StateTree schema-provider boundary.

## Lifecycle surface

`UStateTreeComponent::StartLogic` and `StopLogic` control component execution. `SetStartLogicAutomatically` configures automatic startup. Treat a start call as a lifecycle request, not proof that a particular state or task succeeded.

```cpp fragment
StateTreeComponent->SetStartLogicAutomatically(false);
StateTreeComponent->StartLogic();
StateTreeComponent->StopLogic(TEXT("Owner shutdown"));
```

## Events

`SendStateTreeEvent` accepts either an `FStateTreeEvent` or a gameplay tag with optional payload and origin. The event enters the component's StateTree event path; transition selection remains asset-defined.

```cpp fragment
StateTreeComponent->SendStateTreeEvent(EventTag, FConstStructView(), TEXT("Gameplay"));
```

## Node types

- `FStateTreeTaskBase` defines task behavior.
- `FStateTreeEvaluatorBase` supplies evaluated data.
- `FStateTreeConditionBase` participates in selection or transition conditions.
- `UStateTreeSchema` constrains allowed context and node types.

Keep instance data declared beside the node that owns it and bind external data through the selected schema.

## Status boundary

Node callbacks and execution contexts use StateTree status types. Return values describe the node contract at that point; final gameplay outcome still requires observation of the owning StateTree instance.

## Focused references

- [StateTree patterns](references/state-tree-patterns.md) covers task, evaluator, condition, and event boundaries.
- [StateTree with Mass](references/state-tree-mass-integration.md) covers `MassAIBehavior` ownership.

## Verification boundary

Compile evidence proves UE 5.7 public types and signatures. Asset compilation, selected states, transition ordering, external-data binding, and gameplay outcome require project-specific asset/runtime evidence.
