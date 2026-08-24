# StateTree with Mass Entity

Mass StateTree integration is provided by the `MassAIBehavior` module, not by the core `StateTreeModule` alone.

## Schema and trait

`UMassStateTreeSchema` is the Mass-specific schema. `UMassStateTreeTrait` associates a StateTree asset with a Mass entity template and requires a compatible schema.

## Node bases

Mass-specific nodes derive from `FMassStateTreeTaskBase`, `FMassStateTreeEvaluatorBase`, or `FMassStateTreeConditionBase`. These extend the corresponding core StateTree node bases for the Mass execution context.

## Instance ownership

`UMassStateTreeSubsystem` owns instance-data allocation. `FMassStateTreeInstanceHandle` identifies an allocated instance, while `FMassStateTreeInstanceFragment` stores the per-entity handle and `FMassStateTreeSharedFragment` stores shared StateTree data.

## Processor boundary

Mass StateTree activation and ticking are processor-driven. `UMassStateTreeActivationProcessor` and `UMassStateTreeProcessor` bridge entity queries with StateTree execution; gameplay code should not emulate that lifecycle with per-entity actor ticks.

## Dependency boundary

`UMassStateTreeSchema` records Mass fragment dependencies used by linked nodes. A StateTree task may only read or write fragments declared through its Mass dependency contract.

## Verification boundary

Compile evidence proves the MassAIBehavior types and inheritance relationships. Entity-template setup, processor scheduling, signal delivery, and selected StateTree behavior require a Mass-enabled runtime test.
