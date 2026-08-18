# Actor-Level Collision Enable State and Component Readback

Use this contract when a validator mutates collision at the Actor level in Unreal Engine 5.7.4.

## Two different states

`SetActorEnableCollision(false)` changes the Actor-level enable switch. `UPrimitiveComponent::GetCollisionEnabled()` reports a component's collision mode such as `NoCollision`, `QueryOnly`, or `QueryAndPhysics`. These values are related but are not interchangeable.

| Mutation | Correct readback | What it proves |
|---|---|---|
| Actor collision enable switch | Actor-level enable-collision getter/property | The Actor gate is enabled or disabled |
| Component collision mode | `GetCollisionEnabled()` | The component's query/physics mode |
| Per-channel response | Component response query | The response for the selected channel |

## Validator rule

Read back the same abstraction that the test mutates. A component can report `QueryAndPhysics` while its owning Actor-level collision switch is disabled. Conversely, an Actor-level switch can be enabled while one component still has `NoCollision`.

For a negative scenario, log both the mutation target and the readback abstraction. If the acceptance contract is Actor-level, do not silently substitute a component field because it is easier to query.

## Practical sequence

1. Capture the precondition at the Actor and component levels.
2. Apply exactly one collision mutation.
3. Read back the same level immediately and after the relevant frame or transition.
4. Run the gameplay trace/overlap that should change behavior.
5. Restore the state and verify restoration through the same getter.

This keeps state assertions, physical behavior, and evidence labels separate instead of allowing a passing component readback to mask an Actor-level regression.
