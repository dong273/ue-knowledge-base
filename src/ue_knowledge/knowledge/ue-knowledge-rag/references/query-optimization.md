# UE Knowledge Base — Query Optimization Guide

## Search Language

知识库语料以英文为主（86 篇文档中 79 篇为英文、7 篇中英混合），默认模型
`bge-small-en-v1.5` 也是英文优先。查询策略：

| 查询语言 | 效果 | 示例 |
|----------|------|------|
| **英文术语（API 名 + 关键词）** | ⭐⭐⭐ 最佳 | `"GameplayEffect replication mode"` |
| **中文描述** | ⭐⭐ 可用；混合检索 + 术语表展开可弥补 | `"游戏效果复制模式"` |
| **混合** | ⭐⭐⭐ 推荐 | `"GameplayEffect 冷却 duration policy"` |

**经验法则**：文档是英文的 → 用英文 API 名 + 关键词查询最准。
中文查询会先经 `glossary.json` 术语表做最长匹配别名展开（如
"角色移动 速度衰减" → 追加 `character movement braking deceleration speed`
与相关标识符），命中已知术语时效果接近英文；术语表未覆盖的口语化表达
依赖向量检索本身，效果取决于措辞与文档的重合度。

## Query Specificity

| 查询类型 | 说明 |
|----------|------|
| 精确 API 名 | 直接命中对应章节，效果最好 |
| 主题关键词 | 命中技能文档，效果良好 |
| 模糊概念 | 分散匹配多个来源；先宽泛查找到可能来源，再用精确名重查 |

## 混合检索与分数

- 默认 `hybrid`：向量（BGE）+ 词法（加权字段 BM25）做 RRF 融合，
  中文与专有名词（`DOREPLIFETIME`、`CreateDefaultSubobject`）都可靠。
- `--profile vector` 可回退纯向量（0.4 行为）。
- 每条命中带 `raw_score`（RRF 融合值，**跨查询可比**）与 `rank`。
  置信度/覆盖率判断一律用 `raw_score`，不要用 `score`
  （`score` 是展示用归一化值，每次查询第一名恒为 1.0）。
- 阈值参考（RRF k=60，30+30 候选）：`raw_score ≥ 0.025` 双榜高位；
  `0.015–0.025` 单榜强命中；`< 0.012` 弱命中；全部 `< 0.012` 视为无覆盖。

## Avoiding ChromaDB ONNX Model Download

`collection.query(query_texts=...)` 会触发 ChromaDB 内置 ONNX 模型下载
（all-MiniLM-L6-v2，~79MB），在国内网络环境下会卡死。

**始终使用 BGE 模型计算 embedding 后传入 `query_embeddings=`**
（`ue-kb` CLI 与 `ue_knowledge.query` 已封装此流程）：

```python
from ue_knowledge.query import query

for hit in query("GAS cooldown", top_k=5):
    print(hit["source"], hit["heading"], hit["raw_score"])
```

## Top-K 参数建议

| 场景 | top-k | 说明 |
|------|-------|------|
| 快速参考 | 3 | 只需最相关的 1-2 条 |
| 深入研究 | 5 | Agent 取证的甜点区 |
| 知识扩展 | 8-10 | 发现相关但不同的主题 |

## 查询重写与术语扩展

- `glossary.json` 是别名 → 规范术语/标识符的映射（随包分发）。
  新增主题或发现常用口语词未被覆盖时，补充 `aliases` 后重建索引即可生效
  （`ue-kb build --force`）。
- 混合检索下查询会先做术语扩展再分别走向量与 BM25，两路结果 RRF 融合。

## Performance Notes

- 首次查询（冷进程）包含 ~100MB 模型加载，CPU 上约 1-5s（视机器而定）；
  常驻进程内后续查询 <1s（评测门禁 `cold_cli_query_under_8s` 覆盖冷启动）。
- `model.encode()` 对 64 个文档批量编码约 0.5-1s（构建期）。
- ChromaDB SQLite + HNSW 在万级文档规模下查询 <50ms。
- 需要高频查询的 Agent 场景，建议用常驻进程/`ue-kb serve`（若已提供）
  避免每次查询都重新加载模型。
