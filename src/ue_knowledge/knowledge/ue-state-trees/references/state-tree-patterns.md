# StateTree Node Patterns

This page covers stable node and execution boundaries in UE 5.7.

## Task boundary

Derive native tasks from `FStateTreeTaskBase`. Task instance data and external data are accessed through the execution context and linked handles; do not retain unowned pointers across callbacks.

```cpp fragment
struct FWaitForSignalTask : public FStateTreeTaskBase
{
    EStateTreeRunStatus EnterState(FStateTreeExecutionContext& Context,
        const FStateTreeTransitionResult& Transition) const;
};
```

## Evaluator boundary

Derive evaluators from `FStateTreeEvaluatorBase`. Evaluators expose data to bindings; they do not select states by themselves.

## Condition boundary

Derive native conditions from `FStateTreeConditionBase`. Conditions answer the selection question presented by the tree; side effects belong in tasks or explicit gameplay services.

## Schema and external data

The selected `UStateTreeSchema` defines valid context and node types. Link external data with handles and verify handle validity before reading through an execution context.

## Event boundary

`FStateTreeEvent` carries a gameplay tag, optional typed payload, and optional origin. Event delivery does not guarantee a transition unless the compiled asset contains a matching event transition whose other conditions pass.

## Blueprint nodes

Blueprint task, evaluator, and condition base classes exist beside the native structs. Choose Blueprint or C++ from authoring and performance needs; both still depend on the asset's schema and bindings.

## Validation checklist

- Compile the asset after node or binding changes.
- Verify schema, context data, and external-data handles.
- Observe active states and transition reason at runtime.
- Keep visual behavior and usability as separate human evidence.
