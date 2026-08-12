# UE Knowledge Base — Query Optimization Guide

## Search Language

UE 知识库的数据源以英文为主（引擎源码注释、技能文档、Epic 官方文档）。查询策略：

| 查询语言 | 效果 | 示例 |
|----------|------|------|
| **英文术语** | ⭐⭐⭐ 最佳匹配 (40-62%) | `"GameplayEffect replication mode"` |
| **中文描述** | ⭐⭐ 可用，但匹配度低10-20% | `"游戏效果复制模式"` |
| **混合** | ⭐⭐⭐ 推荐 | `"GameplayEffect 冷却 duration policy"` |

**经验法则**：文档是英文的 → 用英文 API 名 + 关键词查询最准。中文适合补充上下文。

## Query Specificity

| 查询类型 | 匹配度范围 | 说明 |
|----------|-----------|------|
| 精确 API 名 | 50-62% | `"FString Format"` 直接命中 Core 头文件注释 |
| 主题关键词 | 35-50% | `"UE module structure"` 命中技能文档 |
| 模糊概念 | 25-35% | `"how to implement jump"` 分散匹配多个来源 |

**技巧**：不确定 API 名时，先用宽泛查询找到可能来源，再用精确名重查。

## Source Filtering

查询结果中不同 layer 的内容会混合返回。可通过 JSON 模式取回来源过滤：

```python
from hermes_tools import terminal
import json

result = terminal(
    'PYTHONPATH="" TRANSFORMERS_OFFLINE=1 '
    '"$HOME/ue-rag-env/Scripts/python" '
    '"$HOME/ue-rag-env/query_ue_knowledge.py" '
    '"GAS prediction key" --top-k 10 --json',
    timeout=60
)

data = json.loads(result["output"])

# 只看引擎源码注释
engine_docs = [d for d in data if d["source"].startswith("engine-source")]
# 只看 Epic 官方文档
epic_docs = [d for d in data if d["source"].startswith("epic-docs")]
# 只看技能文档
skill_docs = [d for d in data if not d["source"].startswith(("engine-source", "epic-docs"))]
```

## Avoiding ChromaDB ONNX Model Download

`collection.query(query_texts=...)` 会触发 ChromaDB 内置的 ONNX 模型下载（all-MiniLM-L6-v2，~79MB），在国内网络环境下会卡死。

**始终使用 BGE 模型计算 embedding 后传入 `query_embeddings=`**：

```python
model = SentenceTransformer("BAAI/bge-small-zh-v1.5", local_files_only=True)
query_emb = model.encode([query], normalize_embeddings=True)[0]
results = collection.query(
    query_embeddings=[query_emb.tolist()],
    n_results=5,
    include=["documents", "metadatas", "distances"]
)
```

`query_ue_knowledge.py` 和 `ue_knowledge.py` 已封装好此流程，直接调用即可。

## Top-K 参数建议

| 场景 | top-k | 说明 |
|------|-------|------|
| 快速参考 | 3 | 只需最相关的 1-2 条 |
| 深入研究 | 5-8 | 获取多来源的交叉参考 |
| 知识扩展 | 10-15 | 发现相关但不同的主题 |

## Performance Notes

- 首次查询加载模型约 2-5s（CPU），后续查询 <1s
- `model.encode()` 对 64 个文档批量编码约 0.5-1s
- ChromaDB SQLite 在 10K 文档规模下查询 <50ms
- 整体延迟：首次 ~8s，后续 ~3s (网络 + 模型 + 查询)
