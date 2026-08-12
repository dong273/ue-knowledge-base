# UE Knowledge Base — 中文 UE 开发者的本地语义知识库

[![PyPI version](https://img.shields.io/pypi/v/ue-knowledge-base.svg)](https://pypi.org/project/ue-knowledge-base/)
[![CI](https://github.com/dong273/ue-knowledge-base/actions/workflows/ci.yml/badge.svg)](https://github.com/dong273/ue-knowledge-base/actions)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> 面向中文 UE 开发者的本地语义知识库：86 篇原创中文文档，
> 配合本地向量检索（BGE + ChromaDB）。模型一次下载（约 100MB）后
> 完全离线，笔记本 CPU 即可运行，无 API 费用。

## 为什么你需要它

| 痛点 | 常见现状 | 这个项目 |
|---|---|---|
| **中文 UE 资料碎片化** | 答案散落在论坛、博客、视频和英文官方文档里，一个"GAS 冷却"要拼十几个来源 | 31 个主题、86 篇**结构化原创中文文档**，一次检索直达答案 |
| **LLM 会幻觉 UE API** | 通用模型分不清 UE 5.4 和 5.7 的 API 差异，给你"看起来对"的代码 | 文档来自真实项目实践，包含**可直接使用的 C++ 模式**，并针对特定引擎版本校验 |
| **云 RAG 花钱 + 泄代码** | 每次查询都把你的代码片段发给云端 API，还要按 token 计费 | **完全本地运行，零 API 成本**——游戏代码一行都不会离开你的机器 |
| **英文文档阅读成本高** | 官方文档全是英文，翻译丢上下文，专有名词对不上 | **原生中文语料 + 中文优先的 embedding**，中文提问命中率最高 |

覆盖：Gameplay Ability System、角色移动、动画、AI 导航、网络/复制、UMG/Slate、
Niagara、Mass Entity、State Trees、PCG 程序化生成、材质/渲染、模块构建系统、
编辑器工具……（完整 31 主题见 `knowledge/`）

## 特点

- 86 篇原创中文文档，共 **1455 个检索块**，内容来自实际项目实践
- 中文查询实测 top-1 命中 **60.5% 相似度**（见下方真实输出）
- 无 API key、无 token 计费，`pip install` 后即可使用
- embedding 与检索全部在本地完成，代码不会离开你的机器
- 所有命令支持 `--json` 输出，可接入 Hermes / Claude Code / OpenCode 等 Agent
- 面向国内网络：GitHub 镜像克隆 + 清华 PyPI + hf-mirror 自动回退，无需代理
- 模型约 100MB，笔记本 CPU 即可运行，无 GPU 要求；索引构建约 1 分钟

## 一分钟上手

```bash
pip install ue-knowledge-base   # 安装

ue-kb download-model            # 下载模型（约 100MB，仅一次；官方源失败自动切 hf-mirror）
ue-kb build                     # 构建索引（约 1 分钟，之后完全离线）
ue-kb query "GAS 技能冷却"       # 语义检索
ue-kb query "角色移动 速度衰减" --json   # JSON 输出，给 Agent 用
```

## 真实查询示例（实测输出）

```text
$ ue-kb query "GAS 技能冷却"
🔍 UE 知识库检索：GAS 技能冷却

[1] ue-gameplay-abilities/references/gas-input-integration.md › 问题 (匹配度: 60.5%)
    ## 问题  UE 项目同时使用 GAS (GameplayAbilitySystem) 和 Enhanced Input 时，
    容易陷入两个极端：- **全 GAS** → 所有输入走 GAS，但 WASD 轴输入不适合 GAS 的
    事件模型，且 `CommitAbility` 的 GC 延迟影响跳跃手感 - **全直调** → 绕过 GAS，
    失去标签阻断、冷却、属性驱动的 BUFF/DEBUFF...
[2] ue-gameplay-abilities/references/gas-input-integration.md › Jump — GAS 即时技能 (匹配度: 57.1%)
    ### Jump — GAS 即时技能
    `cpp void AMyCharacter::OnJumpStarted() {
        if (AbilitySystem)
            AbilitySystem->TryActivateAbilityByClass(UGA_Jump::StaticClass());
    } // GA_Jump.cpp ...
```

检索结果直接包含可用的 C++ 写法，不只是相关文字。

## 国内安装（零代理）

```bash
# 1. 获取代码（GitHub 镜像，任选其一）
git clone --depth 1 https://gh-proxy.com/https://github.com/dong273/ue-knowledge-base.git
#   git clone --depth 1 https://ghfast.top/https://github.com/dong273/ue-knowledge-base.git

# 2. 安装依赖（清华镜像）
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 下载模型（自动镜像回退，无需手动配置）
ue-kb download-model

# 4. 构建索引（全本地，此后完全离线）
ue-kb build

# 5. 检索
ue-kb query "GAS ability cooldown"
```

## CLI 参考

| 命令 | 说明 | 示例 |
| --- | --- | --- |
| `ue-kb build` | 切块 + embedding 建立索引 | `ue-kb build --force` |
| `ue-kb build --append` | 增量索引：只处理新增文档，已有内容保持不变；日常扩充语料无需全量重建 | `ue-kb build --append` |
| `ue-kb query "..."` | 语义检索，返回带来源和标题的 top-k 结果 | `ue-kb query "角色移动 速度衰减" --top-k 5` |
| `ue-kb info` | 查看索引统计（文档数、目录） | `ue-kb info` |
| `ue-kb download-model` | 一次性下载 embedding 模型 | `ue-kb download-model` |
| `--json` | 机器可读输出（Agent 集成） | `ue-kb query "..." --json` |
| `--db <dir>` | 自定义索引目录（Windows 中文路径请用纯英文目录，见 FAQ） | `ue-kb build --db C:/uekb/.chroma_db` |
| `--source <dir>` | 自定义语料目录 | `ue-kb build --source my-docs/` |
| `--model <name>` | 自定义 embedding 模型 | `ue-kb query "..." --model BAAI/bge-large-zh-v1.5` |
| `--force` | 已存在索引时强制重建 | `ue-kb build --force` |
| `--online` | 允许模型缺失时联网下载（默认离线） | `ue-kb build --online` |

## Python API

```python
from ue_knowledge.query import query

for hit in query("GAS 冷却", top_k=5):
    print(hit["source"], hit["heading"], hit["score"])   # 来源、章节、相似度
```

## Agent 集成

`ue-kb` 专为 AI Agent 设计：完全离线、每次查询零成本、所有命令支持 `--json`。
接入方式见 [docs/agent-integration.md](docs/agent-integration.md)，包含：

- **Hermes Agent** skill 封装（把检索变成 agent 工具）
- **Claude Code** 斜杠命令
- **OpenCode** 命令
- 任意管线的**纯 Python 片段**

## 扩展语料

语料可以自行扩充：

1. 在 `knowledge/<topic>/` 下新增 Markdown 文档（用 `##`/`###` 标题，索引器按标题边界切块）；
2. `ue-kb build --append` 把新增文档加入索引，无需全量重建；
3. 也可以直接索引任意本地 `.md` 目录：`ue-kb build --source my-docs/`。

如需索引 **UE 引擎 C++ 头文件注释** 或 **Epic 官方文档**，参见
`scripts/index_engine_source.py` 与 `scripts/crawl_epic_docs.py`（需要本地引擎
路径；提取的索引数据仅本地生成、不随仓库分发，尊重 Epic 版权）。

## FAQ

- **Windows 下报 `Cannot open header file`？** — hnswlib 无法在含非 ASCII 字符
  的路径（中文用户名/文件夹）下打开索引文件。CLI 会提前拒绝并给出提示：请使用
  纯英文索引目录，如 `ue-kb build --db C:/uekb/.chroma_db`。语料目录本身无限制。
- **国内下载模型慢？** — `ue-kb download-model` 官方源失败时自动经
  `hf-mirror.com` 镜像重试，无需代理或手动 `HF_ENDPOINT`。
- **构建成功但查询说索引不存在？** — 索引目录被移动/删除，或 `chromadb` 升级
  改了存储格式。`ue-kb build --force` 重建即可（`chromadb>=0.5,<1.0` 已自动
  规避 1.x Rust 后端无法重载自身 HNSW 索引的问题）。
- **stderr 有 telemetry 报错？** — chromadb 0.6.x 的 telemetry 已在代码层
  显式关闭（`anonymized_telemetry=False`），与安装的 posthog 版本无关，
  不会再输出噪音。

## License

MIT。知识文档均为原创撰写，不包含引擎源码或 Epic 文档的逐字内容。
