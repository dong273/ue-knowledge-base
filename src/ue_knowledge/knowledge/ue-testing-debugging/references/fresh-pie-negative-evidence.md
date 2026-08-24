# Fresh PIE Negative Scenarios and Evidence Layers

This document defines an evidence-recording method. It does not claim that a particular
gameplay route, visual result, or first-player experience has passed.

## Fresh-session method

- Start from the documented PlayerStart or checkpoint.
- Use the same input path available to a player.
- Do not teleport, inject coordinates, mutate gameplay state, or call the success path.
- End the run explicitly and preserve the post-baseline log tail.

## Separate evidence layers

Record state/route assertions, visible-window evidence, and a human walkthrough as
separate results. A deterministic state assertion cannot replace a visual or human
result. Keep `NOT_RUN` explicit for any layer that was not executed.

## Negative-result record

Record the scenario, fresh-session identifier, starting state, input events, forbidden
actions, expected guard, actual result, relevant media references, and runtime errors.
This is a reporting template; it is not proof that any project-specific scenario ran.
