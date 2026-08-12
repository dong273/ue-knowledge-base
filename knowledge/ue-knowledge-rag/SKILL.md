---
title: ue-knowledge-rag
description: Semantic search over the UE knowledge base (29 skills + 11 engine modules' API + Epic official docs = 9,471 chunks). Locally indexed with BAAI/bge-small-zh-v1.5 + ChromaDB. Zero API cost, fully offline. Do UE tasks → query KB first for context.
tags: [ue, knowledge, rag, search, semantic]
---

# UE Knowledge Base (RAG)

## 数据源
### Layer 1: UE 技能文档（Hermes Skills）
- 29 个 UE 技能文档（SKILL.md + references/*.md）
- 84 个 .md 文件，1,425 个知识片段
- 范围：GAS、动画、物理、AI、UMG、网络、PCG、Niagara 等

### Layer 2: UE 引擎源码注释（Engine Source）

覆盖 **11 个引擎模块**，共 7,862 个 API 文档块：

| 模块 | 路径 | .h 数 | 提取数 |
|------|------|-------|--------|
| **Core** | Runtime/Core/Public | 1,192 | ~2,200 |
| **Engine** | Runtime/Engine/Public | 1,253 | ~2,400 |
| **GAS** | Plugins/GameplayAbilities | 136 | 776 |
| **Slate** | Runtime/Slate/Public | 233 | ~500 |
| **MovieScene** | Runtime/MovieScene/Public | 278 | ~500 |
| **UMG** | Runtime/UMG/Public | 163 | ~450 |
| **RenderCore** | Runtime/RenderCore/Public | 97 | ~300 |
| **Engine/Anim** | Runtime/Engine/Public/Animation | 74 | ~250 |
| **AIModule** | Runtime/AIModule/Public | 21 | ~150 |
| **AnimationCore** | Runtime/AnimationCore/Public | 17 | ~100 |
| **LevelSequence** | Runtime/LevelSequence/Public | 18 | ~100 |
| **总计** | | **3,482** | **~7,862** |

提取内容包括：UCLASS/USTRUCT/UENUM 类注释、UFUNCTION 方法注释、系统架构概述注释。

### Layer 3: UE 官方文档（Epic Games Docs）

| 页面 | 内容量 | 状态 |
|------|--------|------|
| Unreal Engine Architecture | 13 子主题概要 | ✅ |
| Unreal Engine Modules | 70 段落正文 | ✅ |
| **Unreal Engine 5.7 Release Notes** | **336 知识块 (377K chars)** | ✅ **新** |
| **Data Assets in Unreal Engine** | 4 块概要 | ✅ **新** |
| **Project Settings** | 18 文本块 | ✅ **新** |

> `Programming with C++` 和 `Materials` 页面为 Angular SPA，无 SSR 内容，但已通过引擎源码注释深度覆盖。

### 全量统计
| 层级 | 来源 | 文档数 |
|------|------|--------|
| Layer 1 | 29 UE 技能文档 | 1,425 |
| Layer 2 | 引擎 C++ API 源码注释（11 模块） | ~7,862 |
| Layer 3 | Epic 官方文档 | ~360 |
| **总计** | | **~9,471 文档片段** |

### 存储与模型
- Vector DB: `~/AppData/Local/hermes/ue-knowledge/chroma_db/`
- Embedding: `BAAI/bge-small-zh-v1.5` (本地缓存, 512维, 离线运行)
- 搜索技巧：`references/query-optimization.md`

### 自动更新
- cron: 每周日凌晨 0:00 自动重建全量索引（技能 + 引擎源码）

## 查询方法

### 从 Hermes execute_code 中调用

```python
from hermes_tools import terminal
import json

result = terminal(
    'PYTHONPATH="" TRANSFORMERS_OFFLINE=1 '
    '"$HOME/ue-rag-env/Scripts/python" '
    '"$HOME/ue-rag-env/query_ue_knowledge.py" '
    '"你的查询内容" --top-k 5 --json',
    timeout=60
)
data = json.loads(result["output"])
for item in data:
    print(f"[{item['score']:.0%}] {item['source']}: {item['heading']}")
```

### 从 CLI 调用
```bash
PYTHONPATH="" TRANSFORMERS_OFFLINE=1 \
~/ue-rag-env/Scripts/python \
~/ue-rag-env/query_ue_knowledge.py \
"GAS Ability 冷却" --top-k 5
```

### 快速格式化查询
```python
from hermes_tools import terminal
result = terminal(
    'PYTHONPATH="" TRANSFORMERS_OFFLINE=1 '
    '"$HOME/ue-rag-env/Scripts/python" '
    '"$HOME/ue-rag-env/ue_knowledge.py" '
    '"GAS Ability 冷却" --top-k 5',
    timeout=60
)
print(result["output"])
```

## Pitfalls

**🔴 HuggingFace 被墙（中国大陆）**
→ 首次下载模型时设置 `HF_ENDPOINT=https://hf-mirror.com`。模型缓存后（`~/.cache/huggingface/hub/models--BAAI--bge-small-zh-v1.5`），后续离线运行设置 `TRANSFORMERS_OFFLINE=1`。

**🔴 Hermes venv 的 PYTHONPATH 污染**
→ 当 `$PYTHONPATH` 包含 Hermes venv 路径时，sentence-transformers 会报 `regex` 循环导入错误。解决办法：始终设置 `PYTHONPATH=""` 或使用 `TRANSFORMERS_OFFLINE=1`。

**🔴 查询时 model.load() 尝试连接 HF**
→ 即使模型已缓存，`SentenceTransformer(MODEL_NAME)` 默认会 HEAD 请求检查更新。始终传 `local_files_only=True` 或设置 `TRANSFORMERS_OFFLINE=1`。

**🔴 Epic 文档是 Angular SSR**
→ 页面内容在 `<p>` 标签内，不在静态 HTML 中直接可见。用 `curl + re.finditer('<p[^>]*>(.*?)</p>')` 提取。`block-dir-item-md` 的 `description` 属性也包含有价值的摘要。

**🔴 ChromaDB 查询默认用 ONNX 模型**
→ `collection.query(query_texts=...)` 会触发 ChromaDB 内置的 all-MiniLM-L6-v2 ONNX 模型下载（~79MB），网络慢或受限时不可用。始终用 `query_embeddings=` 传入 BGE 模型计算的向量。

## 重新构建知识库

### 全量重建（技能 + 引擎源码）
当 UE 技能文档更新时执行：
```bash
PYTHONPATH="" TRANSFORMERS_OFFLINE=1 \
~/ue-rag-env/Scripts/python \
~/ue-rag-env/build_ue_knowledge.py

PYTHONPATH="" TRANSFORMERS_OFFLINE=1 \
~/ue-rag-env/Scripts/python \
~/ue-rag-env/index_engine_source.py
```

### 索引 Epic 官方文档
爬取 Epic 官方文档页面的 Angular SSR 内容（`<p>` 标签 + `<block-dir-item-md description>` 属性）：
```bash
# 1. 用 curl 下载目标页面
curl -s -L -A "Mozilla/5.0" "https://dev.epicgames.com/documentation/unreal-engine/PAGE-NAME?application_version=5.7" -o page.html

# 2. 提取 <p> 标签正文和 description 属性中的内容
PYTHONPATH="" python -c "
import re
html = open('page.html', encoding='utf-8').read()
# 提取段落
for m in re.finditer('<p[^>]*>(.*?)</p>', html, re.DOTALL):
    t = re.sub('<[^>]+>', '', m.group(1)).strip()
    if len(t) > 30: print(t)
# 提取描述
for m in re.finditer('description=\"([^\"]+)\"', html):
    t = m.group(1).replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    if len(t) > 30: print(t)
"

# 3. 编写索引脚本，按段落分块（1500 chars/块）→ 调用 model.encode + collection.add
#    参考: ~/ue-rag-env/crawl_epic_docs.py (skill 内 scripts/ 下)
```

### 自动重建
cron: 每周日凌晨 0:00 自动执行 `build_ue_knowledge.py` + `index_engine_source.py`。
注意：Epic 文档爬取需手动触发（页面内容变动不频繁）。

## 扩展知识库

### 引擎源码
要索引更多 UE 模块（GameFramework、AI、Animation 等），编辑 `~/ue-rag-env/index_engine_source.py` 中的 `EXTRA_MODULES` 列表，添加目标路径即可。

### Epic 文档
- Epic 文档站是 Angular SSR —— 内容不直接在 HTML 中，需提取 `<p>` 标签正文和自定义 Web Component 的 `description` 属性
- 子页面中的 `block-dir-item-md` 元素包含页面摘要，可批量提取归档

## 环境
- Python 3.12 venv: `~/ue-rag-env/`
- 依赖: sentence-transformers, chromadb, torch
- 模型缓存: `~/.cache/huggingface/hub/models--BAAI--bge-small-zh-v1.5`
