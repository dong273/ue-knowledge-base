---
description: Use for UE 5.7 AudioComponent playback, one-shot sounds, attachment, attenuation, concurrency, fades, and audible-result verification.
---

# UE Audio System

Use this workflow to separate sound assets, playback ownership, spatialization settings, and audible outcomes.

## Playback owners

Use UAudioComponent when playback needs lifetime control, attachment, fades, parameter changes, or completion handling. Use UGameplayStatics helpers for concise one-shot requests.

## Component playback

UAudioComponent exposes SetSound, Play, Stop, FadeIn, FadeOut, and SetVolumeMultiplier.

```cpp fragment
AudioComponent->SetSound(Sound);
AudioComponent->SetVolumeMultiplier(0.8f);
AudioComponent->FadeIn(0.25f, 1.0f);
```

A successful call only proves the request reached a valid component; it does not prove the sound was audible.

## One-shot requests

UGameplayStatics::PlaySoundAtLocation submits a fire-and-forget spatial request. SpawnSoundAttached returns a UAudioComponent for an attached sound when later control is required.

## Spatial settings

USoundAttenuation describes distance and spatialization behavior. USoundConcurrency limits or resolves competing active sounds. Both are policy inputs; runtime voice selection and the listener state determine the observed result.

## Lifetime boundary

Define whether a spawned component auto-destroys, stops with its attachment owner, or is retained by another owner. Avoid keeping raw pointers after auto-destroyed playback completes.

## Focused reference

- [Audio setup patterns](references/audio-setup-patterns.md)

## Verification boundary

Compile the API surface and runtime-test component state or completion callbacks. Loudness, mix balance, localization, occlusion quality, and perceived timing require listening tests.
