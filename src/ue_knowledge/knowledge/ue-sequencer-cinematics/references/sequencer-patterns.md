# Sequencer Runtime Patterns

This page covers stable UE 5.7 runtime control boundaries.

## Playback state

Call Play, Pause, or Stop on a valid UMovieSceneSequencePlayer. Observe the player state or completion delegate separately from the command call.

```cpp fragment
Player->Play();
Player->Pause();
Player->Stop();
```

## Position updates

SetPlaybackPosition accepts FMovieSceneSequencePlaybackParams. Choose EUpdatePositionMethod deliberately because jump, scrub, and play-style evaluation have different event behavior.

```cpp fragment
Player->SetPlaybackPosition(
    FMovieSceneSequencePlaybackParams(2.0f, EUpdatePositionMethod::Jump));
```

## Binding replacement

Use SetBinding to replace the runtime objects for a binding, AddBinding to append an object, and ResetBinding to return to asset-defined binding behavior.

```cpp fragment
SequenceActor->SetBinding(BindingId, Actors, false);
SequenceActor->AddBinding(BindingId, Actor, false);
SequenceActor->ResetBinding(BindingId);
```

## Lifetime

Keep references to the player and actor for as long as the sequence is controlled. Define who stops playback and clears bindings during world teardown or owner destruction.

## Network boundary

Replicating sequence state does not automatically make every bound actor, media source, or cosmetic effect deterministic. Test the chosen authority and synchronization model.

## Validation checklist

- Compile player creation, position updates, and binding APIs.
- Runtime-test state changes and interruption.
- Review camera cuts, framing, lighting, focus, and audio synchronization manually.
