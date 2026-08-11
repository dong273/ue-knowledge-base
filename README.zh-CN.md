# UE Knowledge Base（UE 知识库）

[![PyPI version](https://img.shields.io/pypi/v/ue-knowledge-base.svg)](https://pypi.org/project/ue-knowledge-base/)
[![CI](https://github.com/dong273/ue-knowledge-base/actions/workflows/ci.yml/badge.svg)](https://github.com/dong273/ue-knowledge-base/actions)

面向 Unreal Engine 开发者的**本地语义检索工具链**：29 个主题的中文 UE 开发知识文档
（GAS、动画、AI、网络、UMG、Niagara、PCG 等），配合 `BAAI/bge-small-zh-v1.5`
嵌入模型 + ChromaDB 建立本地向量索引。

**零 API 成本，模型下载一次后完全离线**。适合中文 UE 开发者，也方便接入任何
AI Agent、IDE 或命令行工作流。

```
knowledge/  (29 个主题, ~84 篇 Markdown 文档)
    │  ue-kb build          分块 + 嵌入（本地 BGE small）
    ▼
.chroma_db/  (向量索引)
    │  ue-kb query "GAS 冷却"
    ▼
top-k 语义命中结果（含来源与标题）
```

## 特性

- 📚 **精选语料**：中文 UE 开发文档，覆盖 Gameplay Ability System、角色移动、
  动画、物理碰撞、AI 导航、网络复制、UMG/Slate、Niagara、Mass Entity、
  State Trees、PCG 程序化生成、材质渲染、模块构建系统、编辑器工具等。
- 🧠 **本地语义检索**：`BAAI/bge-small-zh-v1.5`（多语言，约 100MB）+ ChromaDB，
  无云 API、零费用，笔记本 CPU 可跑。
- 🖥️ **简洁 CLI**（`ue-kb`）：`build` / `query` / `info` / `download-model`，
  支持 `--json` 输出方便 Agent 集成。
- 🔌 **可扩展**：用 `--source` 索引任意额外 UE 文档；`scripts/` 提供引擎源码
  注释与 Epic 官方文档的索引脚本。

## 快速开始

```bash
# 1. 安装
pip install -e .            # 或: pip install ue-knowledge-base

# 2. 下载嵌入模型（仅一次，约 100MB）
ue-kb download-model
#    国内网络无需手动设置——官方源失败时自动切换到 hf-mirror 镜像重试

# 3. 建立索引
ue-kb build

# 4. 检索
ue-kb query "GAS 技能冷却" --top-k 5
ue-kb query "角色移动 速度衰减" --json      # 机器可读，供 Agent 使用
```

### 中国大陆：零代理安装

GitHub / PyPI / HuggingFace 直连在国内经常超时或失败，以下路径**全程无需代理**：

```bash
# 1. 获取代码（GitHub 镜像，任选其一）
git clone --depth 1 https://gh-proxy.com/https://github.com/dong273/ue-knowledge-base.git
#   git clone --depth 1 https://ghfast.top/https://github.com/dong273/ue-knowledge-base.git

# 2. 安装依赖（PyPI 清华镜像）
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 下载模型（自动切换镜像，无需手动 export）
ue-kb download-model
#    官方源失败时自动改用 hf-mirror.com 重试；仍失败再手动指定：
#    export HF_ENDPOINT=https://hf-mirror.com && ue-kb download-model

# 4. 建立索引（纯本地，之后完全离线）
ue-kb build

# 5. 检索
ue-kb query "GAS 技能冷却"
```

> 提示：`download-model` 在官方 HuggingFace 源失败时会**自动切换国内镜像重试**，
> 中国大陆用户无需手动设置 `HF_ENDPOINT`。

### 示例

```text
$ ue-kb query "GAS 技能冷却"
🔍 UE 知识库检索：GAS 技能冷却

[1] ue-gameplay-abilities/references/gas-input-integration.md › 问题 (匹配度: 21.1%)
    UE 项目同时使用 GAS (GameplayAbilitySystem) 和 Enhanced Input 时，容易陷入
    两个极端：- **全 GAS** → 所有输入走 GAS，但 WASD 轴输入不适合 GAS 的事件
    模型，且 CommitAbility 的 GC 延迟影响跳跃手感 ...
[2] ue-gameplay-abilities/references/gas-input-integration.md › Jump — GAS 即时技能 (匹配度: 14.2%)
    ...
```

## Python API

```python
from ue_knowledge.query import query

for hit in query("GAS 冷却", top_k=5):
    print(hit["source"], hit["heading"], hit["score"])
```

## 扩展语料

1. 在 `knowledge/<topic>/` 下新增 Markdown 文档（使用 `##`/`###` 标题，索引器
   按标题边界分块）。
2. `ue-kb build --force` 重建索引。

如需索引 **UE 引擎 C++ 头文件注释** 或 **Epic 官方文档**，参见
`scripts/index_engine_source.py` 与 `scripts/crawl_epic_docs.py`（需要本地引擎
路径；提取出的索引数据仅本地生成、不随仓库分发，尊重 Epic 版权）。

## FAQ

- **Windows 下查询报 `Cannot open header file`** — hnswlib 无法在含非 ASCII
  字符的路径（中文用户名/中文文件夹）下打开索引文件。CLI 会提前拒绝此类
  路径：请使用纯英文索引目录，例如 `ue-kb build --db C:/uekb/.chroma_db`。
  语料目录本身无此限制。
- **国内下载模型慢** — `ue-kb download-model` 在官方源失败时会自动通过
  `hf-mirror.com` 镜像重试，无需代理或手动设置 `HF_ENDPOINT`。
- **构建成功但查询提示索引不存在** — 索引目录被移动/删除，或 `chromadb`
  升级改变了存储格式。用 `ue-kb build --force` 重建（注意 `chromadb` 必须
  低于 1.0：1.x 的 Rust 后端无法重新加载自己构建的 HNSW 索引；
  `chromadb>=0.5,<1.0` 已自动处理）。
- **stderr 出现两行无害 telemetry 报错** — `posthog` 版本与 chromadb 0.6.x
  的兼容性问题；已通过 pin `posthog<4` 消除。

## License

MIT。知识文档均为原创撰写，不包含引擎源码或 Epic 文档的逐字内容。
