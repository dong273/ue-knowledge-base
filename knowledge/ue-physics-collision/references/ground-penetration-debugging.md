# Character Ground Penetration Debugging Checklist

When a character (ACharacter / CMC) jumps and occasionally falls through the ground.

## Quick Wins (80%+ of cases)

1. **Enable physics substepping** — Project Settings → Physics → `MaxSubsteps=4`, `MaxSubstepDeltaTime=0.008`
2. **Thicken ground collision** — Use a box with height ≥ 10cm instead of a single-face Plane

## Systematic Debugging Flow

### Step 1: Enable CMC debug display
```cpp
GetCharacterMovement()->bShowDebug = true;
```
Watch the HUD for `MovementMode: Falling/Walking` and `Floor Z` values.

### Step 2: Check floor detection
```cpp
void UMyCMC::FindFloor(const FVector& CapsuleLocation,
    FFindFloorResult& OutFloorResult, bool bCanUseCachedLocation,
    const FHitResult* DownwardSweepResult)
{
    Super::FindFloor(CapsuleLocation, OutFloorResult,
        bCanUseCachedLocation, DownwardSweepResult);
    UE_LOG(LogTemp, Warning, TEXT("FloorDist=%.1f bBlockingHit=%d bWalkable=%d"),
        OutFloorResult.FloorDist, OutFloorResult.bBlockingHit,
        OutFloorResult.bWalkableFloor);
}
```

### Step 3: Console commands
```
ShowDebug MOVEMENT       # Real-time movement mode, velocity, floor
p.KillZ -1000000          # Prevent death from falling through
```

## Root Cause Reference

| Symptom | Likely Cause |
|---------|-------------|
| No blocking hit on floor | Collision channel mismatch, or ground too thin |
| Blocking hit + !WalkableFloor | `WalkableFloorAngle` too tight |
| Blocks fine walking, fails on jump | No physics substepping (high velocity misses collision in one tick) |
| Only on certain terrain spots | Complex collision gaps (`bTraceComplex=false` with complex ground mesh) |
| Multiplayer: client sees ground but server correction pulls through | Network prediction desync (saved move not capturing state) |
