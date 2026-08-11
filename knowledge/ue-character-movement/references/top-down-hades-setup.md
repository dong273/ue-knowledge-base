# Hades-Style Top-Down Character Setup

This reference documents the complete setup for a Hades-style top-down action character
in UE 5.7, built entirely in C++ without Content Browser assets.

## Character Class Pattern

`cpp
ARoguePlayerCharacter(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer.SetDefaultSubobjectClass<UCharacterMovementComponent>(TEXT("CharMoveComp")))
{
    PrimaryActorTick.bCanEverTick = true;

    //—— Camera ——
    CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
    CameraBoom->bUsePawnControlRotation = false;
    CameraBoom->TargetArmLength = 1000.f;
    CameraBoom->SetRelativeRotation(FRotator(-60.f, 0.f, 0.f));   // overhead angle
    CameraBoom->bInheritPitch = false;  // CRITICAL: fixed camera
    CameraBoom->bInheritRoll = false;
    CameraBoom->bInheritYaw = false;

    FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
    FollowCamera->bUsePawnControlRotation = false;

    //—— Movement ——
    UCharacterMovementComponent* MoveComp = GetCharacterMovement();
    MoveComp->bOrientRotationToMovement = false;              // NOT movement-direction
    MoveComp->bUseControllerDesiredRotation = true;           // faces aim direction
    MoveComp->RotationRate = FRotator(0.f, 360.f, 0.f);
    MoveComp->MaxWalkSpeed = 600.f;
    MoveComp->GravityScale = 1.75f;
    MoveComp->JumpZVelocity = 0.f;                            // no jumping in Hades
    MoveComp->bCanWalkOffLedges = true;
    MoveComp->AirControl = 1.0f;
}
`

**Key rotation choices:**
- `bOrientRotationToMovement = false` — character does NOT rotate toward velocity
- `bUseControllerDesiredRotation = true` — character smoothly rotates toward the aim direction
- Rotation is set manually each tick via `FaceMouseCursor()`

## Mouse-Based Aiming (FaceMouseCursor)

`cpp
void ARoguePlayerCharacter::Tick(float DeltaTime)
{
    Super::Tick(DeltaTime);
    FaceMouseCursor();
}

void ARoguePlayerCharacter::FaceMouseCursor()
{
    if (!Controller) return;
    FVector MouseLocation = GetMouseTargetLocation();
    FVector AimDir = (MouseLocation - GetActorLocation()).GetSafeNormal2D();
    if (!AimDir.IsNearlyZero())
    {
        SetActorRotation(AimDir.Rotation());
    }
}

FVector ARoguePlayerCharacter::GetMouseTargetLocation() const
{
    if (ARoguePlayerController* PC = Cast<ARoguePlayerController>(Controller))
    {
        FHitResult Hit;
        PC->GetHitResultUnderCursor(ECC_Visibility, false, Hit);
        if (Hit.bBlockingHit) return Hit.Location;
    }
    return GetActorLocation() + GetActorForwardVector() * 500.f;
}
`

**Prerequisites:**
- Controller must have `bShowMouseCursor = true`
- Controller must use `FInputModeGameAndUI()` mode (mouse is free, not locked)

## Movement Input (Absolute World Direction)

In top-down with a fixed camera, WASD maps to **absolute world directions** (not camera-relative):

`cpp
void OnMoveTriggered(const FInputActionValue& Value)
{
    FVector2D Input = Value.Get<FVector2D>();
    FVector WorldDir = FVector(Input.Y, Input.X, 0.f).GetSafeNormal();
    AddMovementInput(WorldDir, 1.0f);
}
`

**WASD mapping:**
- W → +Y (North/Forward in world space)
- S → -Y (South/Backward)
- A → -X (West/Left)
- D → +X (East/Right)

This is correct for a fixed top-down camera where Y is "up" on screen.

## Inline Enhanced Input (No Content Browser)

Create all `UInputAction` and `UInputMappingContext` as `CreateDefaultSubobject` in the
constructor, then map keys programmatically:

`cpp
// In constructor:
IMC = CreateDefaultSubobject<UInputMappingContext>(TEXT("RogueIMC"));
IA_Move = CreateDefaultSubobject<UInputAction>(TEXT("IA_Move"));
// ... create all InputActions ...

// In SetupInputMappings():
void ARoguePlayerCharacter::SetupInputMappings()
{
    // WASD for Move:
    IMC->MapKey(IA_Move, FKey("W"));
    IMC->MapKey(IA_Move, FKey("S"));
    IMC->MapKey(IA_Move, FKey("A"));
    IMC->MapKey(IA_Move, FKey("D"));

    // Dash:
    IMC->MapKey(IA_Dash, FKey("SpaceBar"));
    IMC->MapKey(IA_Dash, FKey("RightMouseButton"));

    // Combat:
    IMC->MapKey(IA_Attack, FKey("LeftMouseButton"));
    IMC->MapKey(IA_Special, FKey("Q"));
    IMC->MapKey(IA_Cast, FKey("R"));
    IMC->MapKey(IA_Call, FKey("E"));
}
`

This approach produces zero dependencies on Content Browser assets — everything is
code-defined.

## Dash Ability (Hades-Style)

Dash is a short burst of movement via `LaunchCharacter` followed by a timer:

`cpp
void UGA_Dash::ActivateAbility(...)
{
    FVector DashDir = Character->GetLastMovementInputVector();
    if (DashDir.IsNearlyZero()) DashDir = -Character->GetActorForwardVector();
    DashDir.Z = 0.f; DashDir.Normalize();

    // Launch with fixed distance / duration
    float DashDistance = 600.f;
    float DashDuration = 0.25f;
    FVector DashVelocity = DashDir * (DashDistance / DashDuration);
    Character->LaunchCharacter(DashVelocity, true, true);

    // Lock to Flying mode to prevent floor walking interference
    MoveComp->SetMovementMode(MOVE_Flying);
    MoveComp->Velocity = DashVelocity;

    // Timer to end dash
    Avatar->GetWorld()->GetTimerManager().SetTimer(
        DashEndTimer, this, &UGA_Dash::OnDashFinished, DashDuration, false);
}

void UGA_Dash::OnDashFinished()
{
    Character->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    EndAbility(CurrentSpecHandle, CurrentActorInfo, CurrentActivationInfo, true, false);
}
`

**Why `MOVE_Flying` during dash?** Without it, `PhysWalking` computes a velocity from
input each tick and fights the launch velocity. Flying mode preserves the dash trajectory
until the timer fires.

## Melee Attack (Sector Trace)

Hades-style attacks are broad arc sweeps. Use multiple line traces in a fan pattern:

`cpp
void UGA_Attack::PerformDamageCheck()
{
    FVector Start = Char->GetActorLocation();
    FVector Forward = Char->GetAimDirection();
    float AttackRange = 200.f;
    float AttackAngle = 90.f;

    int32 NumTraces = 5;
    for (int32 i = 0; i < NumTraces; i++)
    {
        float Angle = -AttackAngle/2 + (AttackAngle/(NumTraces-1)) * i;
        FVector Dir = Forward.RotateAngleAxis(Angle, FVector::UpVector);
        FVector End = Start + Dir * AttackRange;

        FHitResult Hit;
        UKismetSystemLibrary::LineTraceSingle(World, Start, End,
            UEngineTypes::ConvertToTraceType(ECC_Pawn), false,
            IgnoreActors, EDrawDebugTrace::ForOneFrame, Hit, true);

        if (AActor* HitActor = Hit.GetActor())
            UGameplayStatics::ApplyDamage(HitActor, BaseDamage, Controller, Char, nullptr);
    }
}
`

## 5-Slot Ability System

`cpp
// In character class:
TArray<FGameplayAbilitySpecHandle> AbilitySlots;
// Slots: 0=Attack, 1=Special, 2=Cast, 3=Call, 4=Dash

void GrantAbilityToSlot(TSubclassOf<UGameplayAbility> AbilityClass, int32 SlotIndex)
{
    ClearSlot(SlotIndex);
    FGameplayAbilitySpec Spec(AbilityClass, 1);
    FGameplayAbilitySpecHandle Handle = AbilitySystem->GiveAbility(Spec);
    AbilitySlots[SlotIndex] = Handle;
}

void ActivateSlotAbility(int32 SlotIndex)
{
    if (!AbilitySlots.IsValidIndex(SlotIndex)) return;
    FGameplayAbilitySpecHandle Handle = AbilitySlots[SlotIndex];
    if (!Handle.IsValid()) return;
    AbilitySystem->TryActivateAbility(Handle);
}
`

Each input callback maps to a slot:
- `OnAttackStarted()` → `ActivateSlotAbility(0)`
- `OnDashStarted()` → `ActivateSlotAbility(4)`

## Room Layout for Hades-Style

Rooms are programmatically generated floor tiles + wall cubes + door actors using
`/Engine/BasicShapes/` meshes:

- **Plane** (`/Engine/BasicShapes/Plane.Plane`) for floors — scale to room size
- **Cube** (`/Engine/BasicShapes/Cube.Cube`) for walls — scale X to segment length
- Wall gaps for doors (door width gap, typically 200cm)
- `ARoomDoor` actor at each gap — BoxComponent collision, opens/closes

Room manager generates a linear sequence: Hub → Combat[3-8] → Boss, with difficulty
ramping per room index.

## Key Differences from Third-Person

| Aspect | Third-Person | Hades Top-Down |
|--------|-------------|----------------|
| Camera angle | Behind shoulder, ~15° | Overhead, ~60° |
| Movement | Camera-relative | World-absolute (Y=N, S=-Y, E=+X, W=-X) |
| Rotation | Follows velocity or controller | Follows mouse cursor |
| Jump | Yes | No (replaced by Dash) |
| Dash | Optional, momentum-based | Core mechanic, launch-based |
| Aiming | Crosshair on screen center | Mouse cursor in world |
| Collision hit | `OnHit` for weapons | `LineTrace` fan pattern |
| Input scheme | Keyboard + mouse look | Keyboard + mouse point |
