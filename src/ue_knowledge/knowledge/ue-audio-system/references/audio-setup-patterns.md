# Audio Playback Patterns

This page covers stable UE 5.7 playback and ownership choices.

## Persistent component

Keep a UAudioComponent when the caller must stop, fade, attach, or update playback.

```cpp fragment
AudioComponent->Play(0.0f);
AudioComponent->FadeOut(0.3f, 0.0f);
AudioComponent->Stop();
```

## Sound at a location

PlaySoundAtLocation does not return a component and is suitable for an unmanaged one-shot request.

```cpp fragment
UGameplayStatics::PlaySoundAtLocation(
    WorldContext,
    Sound,
    Location,
    FRotator::ZeroRotator,
    1.0f,
    1.0f);
```

## Attached sound

SpawnSoundAttached returns a UAudioComponent. Choose attachment point, relative transform, owner-destruction behavior, attenuation, concurrency, and auto-destroy policy deliberately.

```cpp fragment
UAudioComponent* Spawned = UGameplayStatics::SpawnSoundAttached(
    Sound,
    AttachComponent,
    NAME_None,
    FVector::ZeroVector,
    FRotator::ZeroRotator,
    EAttachLocation::KeepRelativeOffset);
```

## Completion boundary

OnAudioFinished is a component event, but interruption, concurrency eviction, explicit Stop, and natural completion must be distinguished by the gameplay contract when the difference matters.

## Replication boundary

Audio playback is normally a local cosmetic effect. Replicate the authoritative gameplay event or state, then decide which clients issue the local sound request.

## Validation checklist

- Compile component and gameplay-static call signatures.
- Runtime-test lifetime, interruption, attachment destruction, and completion.
- Listen on the target device and mix; program state cannot prove audibility.
