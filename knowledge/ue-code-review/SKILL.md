---
title: ue-code-review
description: UE C++ 代码审查：检查 UCLASS 宏、GC 安全、碰撞预设、复制同步、C++ 规范等 UE 特有的审查点。用于提交前/PR 前的 UE 项目代码审查。
tags: [ue, code-review, cpp, unreal, security, quality]
---

# UE C++ 代码审查规则

每次审查 UE C++ 代码时执行以下检查项。分 6 个维度：宏/反射安全、GC/内存安全、碰撞/物理规范、复制/同步检查、C++ 通用质量、性能/加载。

## 1. 宏 & 反射安全

### UCLASS/USTRUCT/UENUM 检查
- [ ] UCLASS 标记了正确的分类（Blueprintable、Abstract、Within 等）
- [ ] GENERATED_BODY() 存在（UE5 不用 GENERATED_UCLASS_BODY/GENERATED_USTRUCT_BODY）
- [ ] API 宏存在（如 MYGAME_API），头文件被模块导出
- [ ] 对应的 `.generated.h` 已 include
- [ ] UENUM 是 `uint8` 类型（enum class ... : uint8）

### UPROPERTY 检查
- [ ] 所有需要 GC 跟踪的 UObject 指针有 UPROPERTY()
- [ ] UE5 使用 TObjectPtr<> 而非原始 UObject*
- [ ] EditAnywhere/VisibleAnywhere/EditDefaultsOnly 选对了（EditDefaultsOnly=配置, EditAnywhere=实例, VisibleAnywhere=只读）
- [ ] Replicated 属性有 ReplicatedUsing=OnRep_ 函数
- [ ] Transient 属性确实不需要序列化
- [ ] meta=(ClampMin/ClampMax) 用了数值范围

### UFUNCTION 检查
- [ ] BlueprintCallable/BlueprintPure/BlueprintNativeEvent 选对了
- [ ] BlueprintImplementableEvent 只在纯蓝图接口用（C++ 端无 _Implementation）
- [ ] RPC 函数有 _Implementation 和 _Validate（Server 必须有 _Validate）
- [ ] 网络函数标注了正确可靠级别（Reliable/Unreliable）
- [ ] Exec 函数只在合法类上（PlayerController/Pawn/CheatManager/GameMode 等）

## 2. GC & 内存安全

### UObject 生命周期
- [ ] 无原始 UObject* 成员缺少 UPROPERTY（会导致 GC 悬空指针）
- [ ] TWeakObjectPtr 使用前检查 IsValid()
- [ ] NewObject 创建的对象要么有 Outer 关联，要么 AddToRoot（推荐用 FGCObject）
- [ ] 没有在 UObject 上使用 TSharedPtr（GC + 引用计数冲突，双杀）
- [ ] AddToRoot 有对应的 RemoveFromRoot（或明确生命周期）
- [ ] 非 UObject 类持有 UObject 引用 → 继承 FGCObject + AddReferencedObjects

### TArray/TMap 安全
- [ ] 没有在 ranged-for 循环中修改容器（增删改）
- [ ] TMap::Find 检查返回非 nullptr
- [ ] TArray::RemoveAtSwap 只在可接受顺序变化的场景使用
- [ ] 没有隐式拷贝大容器（传参用 const TArray&）

### 智能指针
- [ ] TSharedRef 初始化不能为空
- [ ] TWeakPtr 使用前 Pin()
- [ ] 循环引用记得用 TWeakPtr 打破

## 3. 碰撞 & 物理规范

### Collision 预设
- [ ] 碰撞预设使用项目定义的 Profile，而非裸写 Channel/Trace/Overlap
- [ ] 自定义碰撞通道有明确用途（如 WeaponTrace、PawnOverlap）
- [ ] OnComponentBeginOverlap/OnHit 有正确的参数签名
- [ ] Trace 查询指定了正确的 ObjectType 和 CollisionChannel

### Physics
- [ ] Simulate Physics 只在需要物理模拟时开启
- [ ] 物理材质有 proper Friction/Restitution
- [ ] Chaos 相关的约束配置检查

## 4. 复制 & 网络同步

### 复制声明
- [ ] GetLifetimeReplicatedProps 调用了 Super::GetLifetimeReplicatedProps
- [ ] DOREPLIFETIME/DOREPLIFETIME_CONDITION 正确使用
- [ ] COND_ 条件选对了（OwnerOnly/SkipOwner/SimulatedOnly/InitialOnly）
- [ ] 属性变化回调 OnRep_ 有 UFUNCTION() 标记
- [ ] 自定义条件使用了 FDoRepLifetimeParams

### RPC 检查
- [ ] Server RPC 有 _Validate 函数，返回 bool
- [ ] 验证函数不产生副作用
- [ ] Client RPC 只调用在拥有该 Actor 的客户端允许的操作
- [ ] NetMulticast 谨慎使用（可能产生大量带宽）
- [ ] 没有不必要的 Unreliable RPC 用于关键状态

### 预测
- [ ] 运动预测相关的 FSavedMove 子类正确实现
- [ ] ServerMove/ClientAdjust 处理正确
- [ ] 客户端预测的补偿/回滚逻辑正确

## 5. C++ 通用质量

### 代码规范
- [ ] UE 前缀正确（F=结构体, U=UObject, A=Actor, S=Slate, I=接口）
- [ ] 没有 using namespace 在头文件中
- [ ] 头文件引用最小化（前向声明代替 #include）
- [ ] UE_LOG 日志级别正确（Log/Warning/Error 区分）
- [ ] 没有残留的调试打印/断点

### 异常安全
- [ ] NewObject 可能返回 nullptr
- [ ] Cast<> 失败场景有处理（或确保一定成功）
- [ ] 文件/网络操作有 Try/catch 或返回值检查

### Modern C++
- [ ] 使用范围 for（`for (const auto& X : Container)`）替代索引循环（除非需要索引）
- [ ] 使用 `auto` 合理（不要 auto 基本类型）
- [ ] 使用 `const` 正确性
- [ ] Lambda 捕获正确（& 或 = 显式选择）
- [ ] 避免动态异常规范

## 6. 性能 & 加载

### Tick
- [ ] Tick 只在必要时启用（bCanEverTick=false 默认）
- [ ] Tick 函数中无耗时操作
- [ ] PrimaryActorTick.TickGroup 设置了正确分组

### 加载
- [ ] 运行时引用使用 TSoftObjectPtr/TSoftClassPtr（非硬引用）
- [ ] 同步加载（LoadObject/FStreamableManager::SynchronousLoad）只在初始化阶段
- [ ] FObjectFinder 只在构造函数/CDO 中使用
- [ ] Asset Manager 配置了正确的 Primary Asset Type

### 容器
- [ ] 频繁查询使用了 TSet/TMap 而非 TArray::Contains（O(n)）
- [ ] TArray::Reserve 在已知大小时预分配
- [ ] 频繁增删但不关心顺序 → RemoveAtSwap

---

## 使用方法

### 提交前审查（推荐）

每次完成 UE C++ 代码后运行：

`bash
# 获取改动
git diff --cached

# 或针对特定文件
git diff HEAD -- Source/MyProject/Character/MyCharacter.cpp
`

然后逐项检查上面的 6 个维度，报告发现的问题。

### PR 审查

对整个 PR 的 diff 执行同样的 6 维度检查，标注严重级别：
- **Critical**（必须修）：GC 悬空指针、缺少复制同步、碰撞通道穿透
- **High**（应修）：宏标记错误、不必要的硬引用、Tick 过量
- **Medium**（建议修）：命名规范、const 正确性
- **Low**（可选）：风格偏好、注释

### 与 requesting-code-review 配合

先用本 UE 技能做 UE 专项审查，如果有通用问题（安全扫描、测试覆盖等）再跑 requesting-code-review 做全量检查。

## 常见 UE 坑

| 模式 | 问题 | 修复 |
|------|------|------|
| 原始 UObject* 无 UPROPERTY | GC 悬空指针 | UPROPERTY() TObjectPtr<> |
| TSharedPtr<UObject> | GC+RC 冲突 | TObjectPtr / FGCObject |
| 修改 TArray for-range | 未定义行为/崩溃 | 逆向索引或备份后修改 |
| 没有 _Validate 的 Server RPC | 客户端可注入攻击 | 加 _Validate 校验参数 |
| 忘记 GetLifetimeReplicatedProps | 属性不同步 | 实现函数 + DOREPLIFETIME |
| 硬引用关卡中所有资产 | 加载时间爆涨 | TSoftObjectPtr + StreamableManager |
| EditAnywhere 配置属性 | 每个实例都有不同副本 | EditDefaultsOnly + Config |

## UE 版本特定检查项

### UE 5.7 API 迁移（检查新代码/移植代码时必查）

UE 5.7 有若干 GAS API 破坏性变更，如果代码在 5.3-5.5 环境编写则大概率命中。审查时检查以下 4 点：

- [ ] `ActivateAbility` / `EndAbility` 第三个参数是 `const FGameplayAbilityActivationInfo ActivationInfo`（不是 `FGameplayAbilitySpec`）。错误表现为 `error C3668: did not override any base class method`
- [ ] 没有使用 `UAbilitySystemBlueprintLibrary::GetFloatAttributeFromAbilitySystem()`（已移除）。改为 `ASC->GetNumericAttribute(Attr)`
- [ ] `UGameplayEffect` 构造器中没有 `GrantedTags.AddTag(...)`（已移除）。改为在应用处设 `Spec.Data->DynamicGrantedTags.AddTag(...)`
- [ ] 动态多播委托（如 `FInputReleaseDelegate`）没有 `AddLambda` / `AddUObject`。改为 `AddDynamic` + `UFUNCTION()` 标记的处理器

详细 API 迁移参考: `ue-gameplay-abilities` 技能的 "UE 5.7 API Migration" 章节及 `references/ue5.7-api-migration.md`

## Pitfalls

- **这个技能适合 UE C++（.h/.cpp），不适合蓝图**
- 大型 diff 建议按文件分割审查
- 部分检查项（如碰撞通道命名规范）需要项目级上下文才能准确判断
- 代码质量判断依赖审查者的 UE 经验，不确定时加载对应的 ue-* 技能补知识
