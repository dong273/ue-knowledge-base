# Third-Person Character Setup

Complete C++ pattern for a third-person character with camera, Enhanced Input, and sprint.

## ⚠️ WASD Input: DO NOT use single Vector2D action

**The trap**: Mapping W/A/S/D to one `Axis2D` InputAction causes all keys to move in the same direction. Keyboard keys produce `FVector(1,0,0)` when pressed — no axis separation. The `SwizzleAxis`/`Negate` modifier chain cannot fix this because `EInputAxisSwizzle` has no identity operation (only YXZ, ZYX, XZY, YZX, ZXY). UE 5.7 `UInputModifierNegate` uses `bX`/`bY`/`bZ` booleans (not a `Negate` vector). `EInputActionValueType::Scalar` ignores modifiers on boolean input.

**The fix**: Use 4 separate `Boolean` InputActions, one per direction. Each callback calls `AddMovementInput(Dir, ±1.f)` directly. Zero modifier chain, zero ambiguity.

## Component Layout

`
CapsuleComponent (root)
├─ CameraBoom (SpringArmComponent, attach to capsule)
│   └─ FollowCamera (CameraComponent, attach to boom socket)
└─ Mesh (SkeletalMeshComponent — inherited from ACharacter)
CharacterMovementComponent (inherited from ACharacter)
`

### Constructor pattern

`cpp
//—— 旋转模式 ——
bUseControllerRotationPitch = false;
bUseControllerRotationYaw = false;
bUseControllerRotationRoll = false;

//—— 弹簧臂 ——
CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
CameraBoom->SetupAttachment(GetCapsuleComponent());
CameraBoom->TargetArmLength = 600.0f;
CameraBoom->SetRelativeRotation(FRotator(-30.f, 0.f, 0.f));
CameraBoom->bUsePawnControlRotation = true;     // 跟随鼠标/手柄右摇杆
CameraBoom->bEnableCameraLag = true;
CameraBoom->CameraLagSpeed = 10.0f;

//—— 摄像机 ——
FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
FollowCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
FollowCamera->bUsePawnControlRotation = false;

//—— CMC 配置 ——
UCharacterMovementComponent* MoveComp = GetCharacterMovement();
MoveComp->bOrientRotationToMovement = true;          // 面向移动方向
MoveComp->RotationRate = FRotator(0.f, 500.f, 0.f);  // 转身速度
MoveComp->MaxWalkSpeed = WalkSpeed;
MoveComp->JumpZVelocity = JumpZSpeed;
MoveComp->GravityScale = 1.75f;
MoveComp->AirControl = 0.35f;
MoveComp->MaxAcceleration = 2048.f;
MoveComp->BrakingDecelerationWalking = 2048.f;
`

### Dependencies (Build.cs)

`csharp
PrivateDependencyModuleNames.AddRange(new string[]
{
    "EnhancedInput",
    "InputCore",
});
`

## Inline Enhanced Input (No Asset Files)

Create 6 separate Boolean InputActions + 1 MappingContext. Each direction is independent — no modifier chain needed.

`cpp
#include "InputMappingContext.h"

// In constructor:
IMC = CreateDefaultSubobject<UInputMappingContext>(TEXT("IMC_Default"));

IA_MoveForward  = CreateDefaultSubobject<UInputAction>(TEXT("IA_MoveForward"));
IA_MoveBackward = CreateDefaultSubobject<UInputAction>(TEXT("IA_MoveBackward"));
IA_MoveRight    = CreateDefaultSubobject<UInputAction>(TEXT("IA_MoveRight"));
IA_MoveLeft     = CreateDefaultSubobject<UInputAction>(TEXT("IA_MoveLeft"));
IA_Jump         = CreateDefaultSubobject<UInputAction>(TEXT("IA_Jump"));
IA_Sprint       = CreateDefaultSubobject<UInputAction>(TEXT("IA_Sprint"));

// All Boolean
IA_MoveForward ->ValueType = EInputActionValueType::Boolean;
IA_MoveBackward->ValueType = EInputActionValueType::Boolean;
IA_MoveRight   ->ValueType = EInputActionValueType::Boolean;
IA_MoveLeft    ->ValueType = EInputActionValueType::Boolean;
IA_Jump        ->ValueType = EInputActionValueType::Boolean;
IA_Sprint      ->ValueType = EInputActionValueType::Boolean;

// Map keys
IMC->MapKey(IA_MoveForward,  EKeys::W);
IMC->MapKey(IA_MoveBackward, EKeys::S);
IMC->MapKey(IA_MoveRight,    EKeys::D);
IMC->MapKey(IA_MoveLeft,     EKeys::A);
IMC->MapKey(IA_MoveForward,  EKeys::Up);      // Arrow keys
IMC->MapKey(IA_MoveBackward, EKeys::Down);
IMC->MapKey(IA_MoveRight,    EKeys::Right);
IMC->MapKey(IA_MoveLeft,     EKeys::Left);
IMC->MapKey(IA_Jump,         EKeys::SpaceBar);
IMC->MapKey(IA_Jump,         EKeys::Gamepad_FaceButton_Bottom);
IMC->MapKey(IA_Sprint,       EKeys::LeftShift);
IMC->MapKey(IA_Sprint,       EKeys::Gamepad_RightTrigger);
`

### Input binding in SetupPlayerInputComponent

`cpp
void ATPCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
    Super::SetupPlayerInputComponent(PlayerInputComponent);
    auto* EIC = Cast<UEnhancedInputComponent>(PlayerInputComponent);
    if (!EIC) return;

    EIC->BindAction(IA_MoveForward,  ETriggerEvent::Triggered, this, &ATPCharacter::OnMoveForward);
    EIC->BindAction(IA_MoveBackward, ETriggerEvent::Triggered, this, &ATPCharacter::OnMoveBackward);
    EIC->BindAction(IA_MoveRight,    ETriggerEvent::Triggered, this, &ATPCharacter::OnMoveRight);
    EIC->BindAction(IA_MoveLeft,     ETriggerEvent::Triggered, this, &ATPCharacter::OnMoveLeft);

    EIC->BindAction(IA_Jump,   ETriggerEvent::Started,   this, &ACharacter::Jump);
    EIC->BindAction(IA_Jump,   ETriggerEvent::Completed, this, &ACharacter::StopJumping);

    EIC->BindAction(IA_Sprint, ETriggerEvent::Started,   this, &ATPCharacter::OnSprintStarted);
    EIC->BindAction(IA_Sprint, ETriggerEvent::Completed, this, &ATPCharacter::OnSprintReleased);
}
`

### Register mapping context in BeginPlay

`cpp
void ATPCharacter::BeginPlay()
{
    Super::BeginPlay();
    if (const APlayerController* PC = Cast<APlayerController>(GetController()))
    {
        if (auto* Sub = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()))
        {
            if (IMC) Sub->AddMappingContext(IMC, 0);
        }
    }
}
`

## Input Callbacks

Each direction has its own function — direction from camera rotation, sign from callback.

`cpp
void ATPCharacter::OnMoveForward()
{
    if (Controller)
    {
        const FRotator Rot = Controller->GetControlRotation();
        const FVector Dir = FRotationMatrix(Rot).GetUnitAxis(EAxis::X);
        AddMovementInput(Dir, 1.f);
    }
}

void ATPCharacter::OnMoveBackward()
{
    if (Controller)
    {
        const FRotator Rot = Controller->GetControlRotation();
        const FVector Dir = FRotationMatrix(Rot).GetUnitAxis(EAxis::X);
        AddMovementInput(Dir, -1.f);
    }
}

void ATPCharacter::OnMoveRight()
{
    if (Controller)
    {
        const FRotator Rot = Controller->GetControlRotation();
        const FVector Dir = FRotationMatrix(Rot).GetUnitAxis(EAxis::Y);
        AddMovementInput(Dir, 1.f);
    }
}

void ATPCharacter::OnMoveLeft()
{
    if (Controller)
    {
        const FRotator Rot = Controller->GetControlRotation();
        const FVector Dir = FRotationMatrix(Rot).GetUnitAxis(EAxis::Y);
        AddMovementInput(Dir, -1.f);
    }
}
`

### Sprint (speed toggle)

`cpp
void ATPCharacter::OnSprintStarted() { GetCharacterMovement()->MaxWalkSpeed = SprintSpeed; }
void ATPCharacter::OnSprintReleased() { GetCharacterMovement()->MaxWalkSpeed = WalkSpeed; }
`

## UnrealMCP Caveats (Blueprint-from-C++)

When building via UnrealMCP tools:

1. **`create_blueprint` parent_class bug**: The C++ plugin prepends "A" before constructing the LoadClass path (`/Script/Engine.A{Name}`), then falls back to `/Script/Game.A{Name}` — neither works for project module classes (e.g. `/Script/MyModule.AMyClass`). The blueprint always shows "Actor" as parent class in read_blueprint_content, but the actual UE blueprint IS properly parented. Verify by checking the Blueprint's parent class dropdown in the editor.

2. **`add_component_to_blueprint` limitation**: `FindObject<UClass>` can't resolve most engine component classes (SpringArmComponent, CapsuleComponent, StaticMeshComponent all fail with "Unknown component type"). Workaround: create components in C++ via `CreateDefaultSubobject`, compile, then create a Blueprint child.

3. **Reliable workflow**: Write C++ → compile → open editor → manually create Blueprint child → assign at runtime. The Blueprint child created via MCP's create_blueprint WILL have the correct parent even if read_blueprint_content reports "Actor" — test by dragging into a level and checking the Details panel.

4. **Build requires editor closed**: Live Coding prevents builds when UE editor is running. Kill `UnrealEditor.exe` before building. `taskkill /F /IM UnrealEditor.exe` works from Git Bash.
