---
title: ue-project-creation
description: >-
tags: [ue, project, creation, setup, template]
---

# UE Project Creation — Standard Workflow

## 概述

在 UE 5.x 中创建一个新 C++ 项目的标准流程。分为三种方式：

| 方式 | 适用场景 | 步骤数 |
|------|----------|--------|
| **A. 编辑器图形界面** | 设计师/单人快速起步 | 3 步 |
| **B. 克隆模板 + CLI** | 自动化/CI/Agent | 5 步 |
| **C. 从零手写** | 自定义模块结构 | 6 步 |

---

## 方式 A：编辑器图形界面（最简单）

在 UE 5.x 中打开 **Unreal Editor**：

`
File → New Project → Blank (C++) → 命名 → 创建
`

编辑器自动完成全部工作：生成 `.uproject`、源码骨架、`.sln`、初始配置。

---

## 方式 B：克隆模板 + CLI（推荐用于自动化）

### 前置条件
- UE 引擎已安装（路径如 `<EngineRoot>/`）
- 已安装 Visual Studio（含 C++ 工具链）
- 本指南示例路径：`<EngineRoot>/`

### Step 1：选择模板

UE 预置模板在 `Engine/Templates/` 下：

| 模板目录 | 类型 | C++ | 描述 |
|----------|------|-----|------|
| `TP_Blank` | Blank | ✅ | 空白 C++ 项目 |
| `TP_BlankBP` | Blank | ❌ | 纯蓝图项目 |
| `TP_FirstPerson` | First Person | ✅ | 第一人称射击模板 |
| `TP_FirstPersonBP` | First Person | ❌ | 第一人称蓝图模板 |
| `TP_ThirdPerson` | Third Person | ✅ | 第三人称模板 |
| `TP_TopDown` | Top Down | ✅ | 俯视角模板 |

> 查看所有：`ls "<EngineRoot>/Templates/" | grep "^TP_"`

### Step 2：复制模板到目标目录

`bash
# 设定变量
ENGINE="<EngineRoot>"
TEMPLATE="$ENGINE/Templates/TP_Blank"
PROJECT_NAME="MyNewProject"
PROJECT_DIR="E:/Unreal Projects/$PROJECT_NAME"

# 复制模板
cp -r "$TEMPLATE" "$PROJECT_DIR"
`

### Step 3：重命名文件和目录

模板中所有 `TP_Blank` 替换为你的项目名：

`bash
cd "$PROJECT_DIR"

# 重命名 .uproject
mv "TP_Blank.uproject" "${PROJECT_NAME}.uproject"

# 重命名 Source 目录
mv "Source/TP_Blank" "Source/${PROJECT_NAME}"

# 重命名 Source 下的文件
cd "Source/$PROJECT_NAME"
mv "TP_Blank.Build.cs" "${PROJECT_NAME}.Build.cs"
mv "TP_Blank.cpp" "${PROJECT_NAME}.cpp"
mv "TP_Blank.h" "${PROJECT_NAME}.h"
cd ..

mv "TP_Blank.Target.cs" "${PROJECT_NAME}.Target.cs"
mv "TP_BlankEditor.Target.cs" "${PROJECT_NAME}Editor.Target.cs"
cd ..
`

### Step 4：更新文件内容

将模板文件内所有 `TP_Blank` 替换为项目名，并设置正确的引擎版本：

**`.uproject` 文件：**
`json
{
    "FileVersion": 3,
    "EngineAssociation": "5.7",   ← 改为你的 UE 版本
    "Category": "",
    "Description": "",
    "Modules": [
        {
            "Name": "MyNewProject",    ← 改为项目名
            "Type": "Runtime",
            "LoadingPhase": "Default"
        }
    ],
    "Plugins": [
        {
            "Name": "ModelingToolsEditorMode",
            "Enabled": true,
            "TargetAllowList": ["Editor"]
        }
    ]
}
`

**`Source/MyNewProject/MyNewProject.Build.cs`：**
`csharp
public class MyNewProject : ModuleRules
{
    public MyNewProject(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
    
        PublicDependencyModuleNames.AddRange(new string[] {
            "Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput"
        });
        PrivateDependencyModuleNames.AddRange(new string[] { });

        // 如果需要 Slate UI：
        // PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });
        
        // 如果需要网络功能：
        // PrivateDependencyModuleNames.Add("OnlineSubsystem");
    }
}
`

**`Source/MyNewProject.Target.cs`：**
`csharp
public class MyNewProjectTarget : TargetRules
{
    public MyNewProjectTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.V6;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_7;
        ExtraModuleNames.Add("MyNewProject");
    }
}
`

**`Source/MyNewProjectEditor.Target.cs`：**
`csharp
public class MyNewProjectEditorTarget : TargetRules
{
    public MyNewProjectEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.V6;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_7;
        ExtraModuleNames.Add("MyNewProject");
    }
}
`

**`Source/MyNewProject/MyNewProject.h`：**
`cpp
#pragma once
#include "EngineMinimal.h"
#include "Engine.h"
#include "Logging/LogMacros.h"

// 日志分类
DECLARE_LOG_CATEGORY_EXTERN(LogMyNewProject, Log, All);
`

**`Source/MyNewProject/MyNewProject.cpp`：**
`cpp
#include "MyNewProject.h"
#include "Modules/ModuleManager.h"

IMPLEMENT_PRIMARY_GAME_MODULE(FDefaultGameModuleImpl, MyNewProject, "MyNewProject");

DEFINE_LOG_CATEGORY(LogMyNewProject);
`

### Step 5：生成项目文件

使用 **UnrealBuildTool** 生成 Visual Studio `.sln`：

`bash
"${ENGINE}/Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.exe" ^
    -projectfiles ^
    -project="${PROJECT_DIR}/${PROJECT_NAME}.uproject" ^
    -game ^
    -engine
`

预期输出：
`
Result: Succeeded
Total execution time: XX.XX seconds
`

### Step 6：验证项目

`bash
# 检查关键文件存在
ls "$PROJECT_DIR/${PROJECT_NAME}.uproject"       # 项目文件
ls "$PROJECT_DIR/${PROJECT_NAME}.sln"             # VS 解决方案
ls "$PROJECT_DIR/Source/$PROJECT_NAME/"           # 源码目录
`

### Step 7：编译验证

`bash
cd "$PROJECT_DIR"

# 方式 1：通过编辑器（自动编译）
"${ENGINE}/Engine/Binaries/Win64/UnrealEditor.exe" "${PROJECT_NAME}.uproject"

# 方式 2：命令行编译
"${ENGINE}/Engine/Build/BatchFiles/Build.bat" ^
    "${PROJECT_NAME}Editor" ^
    Win64 ^
    Development ^
    -project="${PROJECT_DIR}/${PROJECT_NAME}.uproject" ^
    -waitmutex
`

---

## 常见配置

### 添加模块

在 `.uproject` 中添加更多模块：

`json
"Modules": [
    {
        "Name": "MyNewProject",
        "Type": "Runtime",
        "LoadingPhase": "Default"
    },
    {
        "Name": "MyNewProjectEditor",
        "Type": "Editor",
        "LoadingPhase": "Default"
    }
]
`

### 激活插件

`json
"Plugins": [
    {
        "Name": "GameplayAbilities",
        "Enabled": true
    },
    {
        "Name": "PCG",
        "Enabled": true
    },
    {
        "Name": "EnhancedInput",
        "Enabled": true
    }
]
`

### 引擎版本匹配

`EngineAssociation` 字段值可以是：
- 引擎版本号：`"5.7"`（Launcher 安装）
- UUID：`"{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}"`（源码编译）
- 留空：`""`（打开时手动选择）

---

## Pitfalls

**🔴 .uproject EngineAssociation 不对**
→ 打开时提示"找不到引擎"。确认版本号与已安装引擎匹配。UE 5.7 填 `"5.7"`。

**🔴 模板文件名未完全替换**
→ `.Target.cs`、`.Build.cs`、`.cpp`、`.h` 中的类名必须与项目名一致，否则编译报 `LNK2019`。

**🔴 用旧版引擎的模板创建 5.7 项目**
→ `BuildSettingsVersion` 和 `IncludeOrderVersion` 要用新版。UE 5.7 应使用 `V6` 和 `Unreal5_7`。

**🔴 UE 5.7 没有 GenerateProjectFiles.bat**
→ 该脚本在 UE5 中已被移除。用 `UnrealBuildTool -projectfiles` 代替。

**🔴 中文路径**
→ UE 不支持项目路径含中文字符。用英文路径。

**🔴 重复模板**
→ 不要直接在 `Templates/` 目录下修改，必须复制到 `Unreal Projects/` 下。

---

## 参考

- 已创建的示例项目：`E:/Unreal Projects/MyBlankProject/`
- 模板目录：`<EngineRoot>/Templates/`
- 相关技能：`ue-project-context`（项目配置）、`ue-module-build-system`（模块管理）
