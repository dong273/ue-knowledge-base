# Silent Failure Diagnosis

Some gameplay writes fail without any error. "No error, no state change" has
recurring root causes; check them in order before assuming the code did not
run.

## Static mobility swallows transforms (UE 5.7 verified)

`SetActorLocation` / `SetActorRotation` silently do nothing when the root
component's mobility is Static. The call returns without error and the actor
does not move or rotate.

- Actors spawned at runtime inherit class-default mobility; an authored
  instance of the same class may have been switched to Movable by hand. This is
  how "the same BP works in one map and freezes in another" happens.
- First check for any actor that should move or rotate at runtime: read the
  root component's mobility. Explicitly set Movable for actors that need it.
- Consequence for diagnosis: "position unchanged" never proves "the function
  did not execute".

## Per-frame overwrite looks like a frozen variable

Symptom: an external write succeeds and reads back correctly, but the next
observation shows the old value again — the variable appears frozen.

Discrimination sequence (verified pattern):

1. Prove the tick/function is running at all: log counter or first-line
   sentinel that fires every execution.
2. Write a deliberately absurd value (e.g. `99`, `-7777`) through the external
   channel. Immediate read-back confirms the write path works.
3. The next tick's read shows the old value → something writes the variable
   every tick. Locate the per-frame writer in the graph.
4. Related variables that "never change" may simply sit on a branch whose
   guard is always false — a frozen look without any writer.

## Choose a discriminative probe, not the suspect path

Test side effects that are unrelated to the suspect logic but execute on the
same path every tick (e.g. a rotation applied by the same tick function).
If the probe fires, the function runs and the failure is inside the suspect
branch. Pair every hypothesis with one measured exclusion, and keep the
exclusion table in the record.

## Self-hit traces always succeed

A downward line trace started from the capsule center hits the owning
capsule first, so a "grounded" check built on it is always true. Start the
trace at the capsule bottom, add the owner to `FCollisionQueryParams` ignore
list, or verify the first hit is not self before feeding the result into
gameplay gates.
