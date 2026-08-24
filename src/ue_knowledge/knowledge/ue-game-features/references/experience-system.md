# Experience-Style Project Layer

“Experience” is not a required core Game Features type. It is a project architecture that can select configuration and request one or more Game Feature plugins.

## Project-owned contract

Define the experience asset, selection rules, loading UI, failure policy, and readiness signal in the project layer. Do not present project-specific class names or phase states as portable UE API.

## Engine boundary

The reusable engine contracts remain `UGameFeaturesSubsystem`, `UGameFeatureData`, and `UGameFeatureAction`. A project experience may coordinate them, but it does not change their plugin state-machine semantics.

## Readiness boundary

Separate these observations:

- the experience definition was selected;
- plugin state requests completed successfully;
- feature actions completed their activation work;
- project gameplay declared itself ready;
- player-visible behavior passed human validation.

Each layer needs its own evidence; a successful plugin request cannot substitute for project or human readiness.

## Failure policy

Project code decides whether a failed optional feature is skipped, retried, or treated as fatal. Record that policy with the project configuration rather than embedding it in the public UE core.

## Portability checklist

- Label project-owned types explicitly.
- Keep engine Game Feature calls behind a small project service.
- Test activation rollback and repeated world/session entry.
- Exclude project names, private asset paths, and acceptance status from the public corpus.
