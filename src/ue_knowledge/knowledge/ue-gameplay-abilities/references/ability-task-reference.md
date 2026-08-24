# Ability Task Reference

## Task ownership and lifecycle

An ability task is created for an owning `UGameplayAbility`, activated, and eventually
ended. Bind the task's documented delegates before activation and ensure cancellation or
ability ending cannot leave project-side state active.

## WaitDelay surface

UE 5.7 exposes `UAbilityTask_WaitDelay::WaitDelay(UGameplayAbility*, float)`.

```cpp fragment
UAbilityTask_WaitDelay* Task = UAbilityTask_WaitDelay::WaitDelay(this, DelaySeconds);
Task->ReadyForActivation();
```

## PlayMontageAndWait surface

UE 5.7 exposes `UAbilityTask_PlayMontageAndWait::CreatePlayMontageAndWaitProxy` for an
owning ability and montage. Delegate outcomes and montage interruption are runtime
behavior and require a project-specific test.

```cpp fragment
UAbilityTask_PlayMontageAndWait* Task =
    UAbilityTask_PlayMontageAndWait::CreatePlayMontageAndWaitProxy(
        this, NAME_None, Montage, Rate);
Task->ReadyForActivation();
```

## Custom tasks

A custom task must define a clear creation function, activation path, delegate contract,
and termination path. A compiled subclass does not prove that a delegate fires in the
intended order; cover that behavior with Automation.

## Acceptance boundary

The shared GAS compile fixture verifies the named task types and factories. Runtime task
timing, montage playback, target data, prediction, and cancellation remain separate
project-specific evidence obligations.
