---
description: Use for UE 5.7 Level Sequence runtime playback, sequence actors, binding overrides, playback position, and cinematic verification boundaries.
---

# UE Sequencer and Cinematics

Use this workflow to separate sequence assets, runtime players, object bindings, and rendered outcomes.

## Runtime types

ULevelSequence is the level-sequence asset. ULevelSequencePlayer controls runtime playback, and ALevelSequenceActor owns runtime sequence and binding context in a world.

## Create a player

ULevelSequencePlayer::CreateLevelSequencePlayer creates a player and returns the spawned sequence actor through an output reference.

```cpp fragment
ALevelSequenceActor* SequenceActor = nullptr;
ULevelSequencePlayer* Player = ULevelSequencePlayer::CreateLevelSequencePlayer(
    WorldContext,
    Sequence,
    FMovieSceneSequencePlaybackSettings{},
    SequenceActor);
```

Validate both returned objects before issuing playback requests.

## Playback control

UMovieSceneSequencePlayer exposes Play, Pause, Stop, and SetPlaybackPosition. A call returning does not prove evaluation, camera cuts, media synchronization, or rendering completed.

## Binding overrides

ALevelSequenceActor::SetBinding, AddBinding, and ResetBinding operate on FMovieSceneObjectBindingID. Binding identity must come from the intended sequence and hierarchy.

## Editor boundary

Runtime playback APIs live in LevelSequence and MovieScene. Authoring tracks, sections, keys, and editor UI may require editor-only modules; keep those dependencies out of runtime modules.

## Focused reference

- [Sequencer runtime patterns](references/sequencer-patterns.md)

## Verification boundary

Compile the runtime surface and test player state or binding changes. Shot composition, camera continuity, focus, exposure, audio sync, and final render quality require human review.
