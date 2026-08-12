# GAS + Enhanced Input 层分离架构

## 问题

UE 项目同时使用 GAS (GameplayAbilitySystem) 和 Enhanced Input 时，容易陷入两个极端：
- **全 GAS** → 所有输入走 GAS，但 WASD 轴输入不适合 GAS 的事件模型，且 `CommitAbility` 的 GC 延迟影响跳跃手感
- **全直调** → 绕过 GAS，失去标签阻断、冷却、属性驱动的 BUFF/DEBUFF 能力

## 方案：三层分离架构

```
┌──────────────────────────────────────────┐
│          能力层 (GAS)                      │
│  GA_Sprint(耐力/标签) GA_Jump(冷却)      │
│  GE_SprintSpeedBoost → MovementSpeed*N    │
│  标签: State.Stunned, State.Exhausted     │
└────────────┬─────────────────────────────┘
             │ 属性变化
             ▼
┌──────────────────────────────────────────┐
│          桥接层 (Bridge)                   │
│  OnAttributeChanged(MovementSpeed)        │
│    → CharacterMovement::MaxWalkSpeed       │
│    = BaseWalkSpeed * MovementSpeed         │
└────────────┬─────────────────────────────┘
             │ MaxWalkSpeed
             ▼
┌──────────────────────────────────────────┐
│          运动层 (CharacterMovement)        │
│  WASD 轴输入 → AddMovementInput(直调)     │
│  Jump 物理 → CharacterMovement 原生       │
│  MaxWalkSpeed ← 桥接层写入                │
└──────────────────────────────────────────┘
```

### 各层职责

| 层 | 职责 | 不做什么 |
|----|------|---------|
| **运动层** (Character) | WASD `AddMovementInput`(直调), Jump 的 `bPressedJump` | 不管理冷却/标签/资源 |
| **能力层** (GAS) | Sprint 耐力消耗/疲劳, Jump 冷却/地面检测, 所有 BUFF/DEBUFF | 不直接调 `MaxWalkSpeed` |
| **桥接层** (Attribute callback) | `MovementSpeed` 属性变化 → `MaxWalkSpeed` | 不做游戏逻辑决策 |

## 具体实现模式

### 输入绑定 (Enhanced Input → GAS)

```cpp
// .h
void OnJumpStarted();      // Space → GAS
void OnJumpReleased();      // Space release (空)
void OnSprintStarted();     // Shift → GAS
void OnSprintReleased();    // Shift → Cancel GAS

// .cpp — SetupPlayerInputComponent
// WASD: 直调运动层
EIC->BindAction(IA_MoveForward, ETriggerEvent::Triggered, this, &AMyChar::OnMoveForward);
// Jump: GAS 能力层
EIC->BindAction(IA_Jump, ETriggerEvent::Started, this, &AMyChar::OnJumpStarted);
// Sprint: GAS 能力层
EIC->BindAction(IA_Sprint, ETriggerEvent::Started, this, &AMyChar::OnSprintStarted);
EIC->BindAction(IA_Sprint, ETriggerEvent::Completed, this, &AMyChar::OnSprintReleased);
```

### Jump — GAS 即时技能

```cpp
void AMyCharacter::OnJumpStarted()
{
    if (AbilitySystem)
        AbilitySystem->TryActivateAbilityByClass(UGA_Jump::StaticClass());
}

// GA_Jump.cpp
void UGA_Jump::ActivateAbility(...)
{
    if (!CommitAbility(Handle, ActorInfo, ActivationInfo))
    {
        EndAbility(Handle, ActorInfo, ActivationInfo, true, true);
        return;
    }
    // LaunchCharacter 保留水平速度，覆盖 Z
    ACharacter* Char = Cast<ACharacter>(ActorInfo->AvatarActor.Get());
    if (Char) Char->LaunchCharacter(FVector(0,0,JumpVelocity), false, true);
    EndAbility(Handle, ActorInfo, ActivationInfo, true, false);
}
```

**关键决策**：使用 `LaunchCharacter`（非 `bPressedJump`）的原因是 GAS 不需要依赖 CharacterMovement 下一帧的 Tick 消费 `bPressedJump`。`LaunchCharacter` 立刻生效，适合即时技能。

### Sprint — GAS 维持技能（Input Release 取消）

```cpp
void AMyCharacter::OnSprintStarted()
{
    if (AbilitySystem)
        AbilitySystem->TryActivateAbilityByClass(UGA_Sprint::StaticClass());
}

void AMyCharacter::OnSprintReleased()
{
    if (!AbilitySystem) return;
    const FGameplayTagContainer SprintCancelTags(
        FGameplayTag::RequestGameplayTag("Ability.Player.Sprint")
    );
    // UE 5.7: CancelAbilities（取指针），不是 CancelAbilitiesByTag
    AbilitySystem->CancelAbilities(&SprintCancelTags);
}

// GA_Sprint.cpp — ActivateAbility 中:
// 1. CommitAbility (cost)
// 2. Apply GE_SprintSpeedBoost (Infinite, MovementSpeed *= 1.8)
// 3. 启动耐力消耗定时器 (0.1s tick)
// 4. WaitInputRelease (监听 ASC 的输入释放)

// GA_Sprint.cpp — EndAbility 中:
// 1. 停止耐力消耗定时器
// 2. RemoveActiveGameplayEffect(SpeedBoostHandle) → MovementSpeed 恢复
// 3. 检查耐力 ≤ 0 → Apply GE_Exhaustion (State.Exhausted 标签 1.5s)
```

### 桥接层 — MovementSpeed → MaxWalkSpeed

```cpp
// PlayerCharacterBase.h
UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Movement")
float BaseWalkSpeed = 500.f;  // 基础走速，桥接层引用

// TPCharacter.cpp — BeginPlay（ASC 初始化后）
if (AbilitySystem && StaminaSet)
{
    AbilitySystem->GetGameplayAttributeValueChangeDelegate(
        StaminaSet->GetMovementSpeedAttribute()
    ).AddUObject(this, &AMyChar::OnMovementSpeedChanged);
}

void AMyCharacter::OnMovementSpeedChanged(const FOnAttributeChangeData& Data)
{
    if (UCharacterMovementComponent* MoveComp = GetCharacterMovement())
    {
        // MaxWalkSpeed = BaseWalkSpeed * MovementSpeed(multiplier)
        // 常态: 500 * 1.0 = 500  冲刺: 500 * 1.8 = 900
        MoveComp->MaxWalkSpeed = BaseWalkSpeed * Data.NewValue;
    }
}
```

## 属性集设计示意

```cpp
UCLASS()
class UBAttributeSet_Stamina : public UAttributeSet
{
    UPROPERTY(Replicated) FGameplayAttributeData Stamina;           // 当前耐力
    UPROPERTY(Replicated) FGameplayAttributeData MaxStamina;       // 最大耐力
    UPROPERTY(Replicated) FGameplayAttributeData StaminaRegenRate; // 回复速率
    UPROPERTY(Replicated) FGameplayAttributeData MovementSpeed;    // 速度倍率(1.0→1.8)
    // GE_SprintSpeedBoost 用 Multiplicitive op 修改 MovementSpeed
};
```

## 扩展模式

### 加速 BUFF（拾取道具）

```
拾取加速道具 → ApplyGE: GE_SpeedBoost(Infinite, MovementSpeed *= 1.5)
             → 桥接层自动更新 MaxWalkSpeed = 500 * 1.5 = 750
             → 3 秒后 RemoveActiveGameplayEffect → MovementSpeed 恢复 1.0
             → 桥接层更新 MaxWalkSpeed = 500
```

只需一个 GE，不需要碰任何 `MaxWalkSpeed` 代码。

### 减速 DEBUFF（冰冻/泥沼）

```
触发冰冻 → ApplyGE: GE_Freeze(HasDuration, MovementSpeed *= 0.3)
         → 桥接层自动更新 MaxWalkSpeed = 500 * 0.3 = 150
         → 解冻时 Effect 过期 → 自动恢复
```

### 眩晕（全技能阻断）

```
触发眩晕 → ASC->AddLooseGameplayTag("State.Stunned")
         → GA_Jump::ActivationBlockedTags 包含 "State.Stunned" → 无法跳跃
         → GA_Sprint::ActivationBlockedTags 包含 "State.Stunned" → 无法冲刺
         → 眩晕结束时 RemoveLooseGameplayTag
```

## 常见陷阱

### 1. `CancelAbilities` 签名 (UE 5.7)

UE 5.7 中方法名是 `CancelAbilities`（不是 `CancelAbilitiesByTag`），参数是指针（不是引用）：
```cpp
ASC->CancelAbilities(&TagContainer);                      // 正确: 指针
ASC->CancelAbilities(&TagContainer, nullptr, Instance);   // 跳过某个实例
```

### 2. `CancelAbilities` 匹配的是 AbilityTags, 不是 ActivationOwnedTags

`CancelAbilities(&Tags)` 匹配的是在 Ability CDO 构造器中 `SetAssetTags()` 设置的标签。`ActivationOwnedTags` 不会被 CancelAbilities 检测。确保取消用标签和 SetAssetTags 的标签一致。

### 3. `FGameplayTagContainer` 变量名避免与 `AActor::Tags` 冲突

```cpp
// ❌ 编译错误: 与 AActor::Tags 冲突
FGameplayTagContainer Tags;
// ✅ 加前缀避免
FGameplayTagContainer SprintCancelTags;
```

### 4. BaseWalkSpeed 应该放在基类

`BaseWalkSpeed` 放在 `PlayerCharacterBase` 而非具体角色类，这样桥接层在基类中引用它时不需要 downcast。子类可通过构造函数或 `EditDefaultsOnly` 覆盖。

### 5. MovementSpeed 初始值必须为 1.0

`MovementSpeed` 是做乘法的属性（`EGameplayModOp::Multiplicitive`），初始值必须为 1.0（不是 0），否则常态速度会是 0。
