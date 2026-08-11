# UE Knowledge Base（UE 知识库）

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
#    国内网络: export HF_ENDPOINT=https://hf-mirror.com 后重试

# 3. 建立索引
ue-kb build

# 4. 检索
ue-kb query "GAS 技能冷却" --top-k 5
ue-kb query "角色移动 速度衰减" --json      # 机器可读，供 Agent 使用
```

### 示例

```text
$ ue-kb query "GAS 冷却"
🔍 UE 知识库检索：GAS 冷却

[1] ue-gameplay-abilities/SKILL.md › GameplayEffect 冷却配置 (匹配度: 86.3%)
    Cooldown tags 通过 GameplayTag 管理冷却状态：在 GameplayEffect 中设置
    CooldownGameplayEffectClass ... 
[2] ue-gameplay-abilities/references/gas-input-integration.md › 冷却与输入 (匹配度: 82.1%)
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

## License

MIT。知识文档均为原创撰写，不包含引擎源码或 Epic 文档的逐字内容。
