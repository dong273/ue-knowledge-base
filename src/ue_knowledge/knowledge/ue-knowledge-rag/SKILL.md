---
title: ue-knowledge-rag
description: Semantic search over the UE knowledge base: 31 topics / 86 original docs bundled in the ue-knowledge-base package, indexed locally with BGE + BM25 hybrid retrieval (ChromaDB). Zero API cost, fully offline after the one-time model download. Do UE tasks → query the KB first for grounded context.
tags: [ue, knowledge, rag, search, semantic]
---

# UE Knowledge Base (RAG)

## 数据源

### Layer 1: 随包分发的技能文档
- `ue-knowledge-base` 包内置语料：31 个主题、86 篇原创文档（SKILL.md + references/*.md）
- 主题覆盖：GAS、动画、物理、AI、UMG、网络、PCG、Niagara、Mass、材质渲染等
- 语料随 wheel/sdist 打包（`src/ue_knowledge/knowledge/`），`pip install` 即得

### Layer 2: 引擎源码注释（本地构建，不随包分发）
- 用 `scripts/index_engine_source.py` 索引本地引擎的 C++ 头文件注释
- 产物在本地生成，尊重 Epic 版权，不重新分发

### Layer 3: Epic 官方文档（本地构建，不随包分发）
- 用 `scripts/crawl_epic_docs.py` 爬取官方文档页面
- 注意 Epic 文档站是 Angular SSR：内容在 `<p>` 标签与
  `block-dir-item-md` 的 `description` 属性中，需按脚本方式提取

## 存储与模型

- 索引位置（用户数据目录，可用 `--db` 或 `UE_KB_CHROMA_DIR` 覆盖）：
  - Windows: `%LOCALAPPDATA%\ue-knowledge-base\chroma_db`
  - macOS: `~/Library/Application Support/ue-knowledge-base/chroma_db`
  - Linux: `$XDG_DATA_HOME/ue-knowledge-base/chroma_db`
- 默认模型: `BAAI/bge-small-en-v1.5`（约 100MB，本地缓存，离线运行）
- 中文为主的场景：`ue-kb build --model BAAI/bge-small-zh-v1.5` 后重建索引

## 查询方法

### CLI（推荐，Agent 友好）

```bash
ue-kb query "GAS ability cooldown" --top-k 5 --json
```

每条命中包含 `source` / `heading` / `score` / `raw_score` / `rank` / `text`。
`raw_score` 可跨查询比较（置信度判断见 `docs/agent-integration.md`）。

### Python API

```python
from ue_knowledge.query import query

for hit in query("GAS cooldown", top_k=5):
    print(hit["source"], hit["heading"], hit["raw_score"])
```

### Agent 集成（Hermes / Claude Code / OpenCode）

见 `docs/agent-integration.md`：所有命令支持 `--json`，输出确定性强，
索引完全本地，无 API key、无网络依赖、无按次计费。

## 常见坑

**🔴 HuggingFace 被墙（中国大陆）**
→ 首次下载模型失败时自动回退 `hf-mirror.com`（`ue-kb download-model` 内置）；
也可手动设置 `HF_ENDPOINT=https://hf-mirror.com`。模型缓存后完全离线。

**🔴 ChromaDB 查询默认用 ONNX 模型**
→ `collection.query(query_texts=...)` 会触发 ChromaDB 内置
all-MiniLM-L6-v2 ONNX 模型下载（~79MB）。始终用 `query_embeddings=`
传入 BGE 模型计算的向量（`ue-kb` 内部已封装此流程）。

**🔴 模型加载尝试联网检查更新**
→ 即使模型已缓存，`SentenceTransformer(MODEL_NAME)` 默认会 HEAD 请求检查
更新。`ue-kb` 默认离线（`local_files_only=True` / `TRANSFORMERS_OFFLINE=1`）。

**🔴 PYTHONPATH 污染**
→ 当 `$PYTHONPATH` 包含其他 venv 路径时，sentence-transformers 可能报
`regex` 循环导入错误。解决办法：清空 `PYTHONPATH` 或设置
`TRANSFORMERS_OFFLINE=1`。

**🔴 Windows 非 ASCII 路径**
→ hnswlib 无法在含中文的路径下打开索引文件。索引目录必须用纯 ASCII 路径
（`ue-kb build --db C:/uekb/.chroma_db`）；语料目录不受限。

## 扩展知识库

- 自定义语料目录：`ue-kb build --source my-docs/`（任意本地 `.md` 目录）
- 增量同步：`ue-kb build --append`（新增/修改/删除都反映到新索引代数）
- 引擎源码 / Epic 文档索引脚本在 `scripts/` 下，需本地引擎/网络环境

## 索引维护

- `ue-kb info --json` 查看索引清单、语料指纹、staleness、模型匹配状态
- 索引是版本化代数 + 原子激活：构建失败不会破坏当前可用索引
- 发布流程与语料同步见 `docs/sync-guide.md` 与 `docs/releasing.md`

## 写回（Write-back）

任务中验证过的合适材料要主动沉淀回知识库。先按路由表判定去向：

| 材料类型 | 去向 | 发布性 |
|---|---|---|
| UE 通用可复用（已验证的引擎技术、C++ 模式、坑与解法） | `%LOCALAPPDATA%\hermes\skills\ue\<topic>\`（SKILL.md 或 references/*.md） | 走 publish 管线进公共语料，随 PyPI 发版 |
| 项目特定（设计决策、关卡、项目状态） | 项目自己的知识库（项目级 MCP） | 仅项目内 |
| 私有/内部管线 | publish 排除的私有主题（项目内部管线类技能） | 永不上线（publish 已排除） |

**判定标准（全部满足才写）**：
1. 实际验证过（编译或运行通过；禁止编造 API）；
2. 通用性：不含项目名、私有路径、内部管线信息（`check_privacy.py` 兜底）；
3. 新颖性：先查 KB，`raw_score` 低或无对应小节才写；
4. 风格合规：English-first 正文（可双语）、copy-paste C++ 模式带引擎版本标注、
   SKILL.md frontmatter（name/description/version/metadata.hermes.tags）。

**操作链（按序，任一门禁失败即停）**：
1. 写/更新 skills 树文件（新主题建目录）；
2. `python scripts/publish_from_hermes.py --topics <topic>`（在 repo 检出内运行，消毒再生成语料）；
3. 门禁：`python scripts/check_privacy.py`、`python scripts/check_zh_dict.py`、
   `pytest tests/` 全绿；
4. `ue-kb build --append`（editable 安装 → 本地立即可搜）；
5. PyPI 发版仅按用户指示执行（docs/releasing.md）；写回 ≠ 立即发版。
