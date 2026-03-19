---
name: glm-embedding-test
description: >
  批量评测智谱 GLM Embedding 模型的文本向量化能力，计算余弦相似度矩阵。
  触发词（中文）：Embedding评测、向量化、余弦相似度、文本相似度、embedding-3测试、语义相似度。
  Triggers (English): embedding test, text vectorization, cosine similarity, semantic similarity evaluation, embedding-3 batch test, text embedding benchmark.
  Use when: user wants to batch-generate text embeddings, compute similarity scores between texts, or evaluate ZhipuAI embedding model quality.
allowed-tools: Bash
---

# GLM Embedding 评测

## 平台路径速查

| 平台 | 脚本路径 |
|------|---------|
| Cursor | `~/.cursor/skills/glm-embedding-test/scripts/embedding_tester.py` |
| Claude Code | `~/.claude/skills/glm-embedding-test/scripts/embedding_tester.py` |
| Codex | `~/.codex/skills/glm-embedding-test/scripts/embedding_tester.py` |
| OpenClaw | `~/.openclaw/skills/glm-embedding-test/scripts/embedding_tester.py` |

> Agent 调用时可用 Shell 自动定位：
> ```bash
> SCRIPT=$(find ~/.cursor ~/.claude ~/.codex ~/.openclaw -name "embedding_tester.py" 2>/dev/null | head -1)
> ```

## 前置条件

```bash
pip install zhipuai openpyxl numpy pandas
export ZHIPUAI_API_KEY="your_api_key"
```

## 参数说明

| 参数 | 默认 | 说明 |
|------|------|------|
| `--mode` | `file` | `texts`（多行文本）或 `file`（Excel/CSV） |
| `--texts` | — | 多行文本，每行一条或 `***` 分隔 |
| `--file` | — | Excel(.xlsx) 或 CSV 路径 |
| `--col` | 第一列 | 指定列名 |
| `--col2` | — | 第二列，用于逐行相似度（query vs answer） |
| `--sheet` | — | Excel sheet 名 |
| `--model` | `embedding-3` | `embedding-3`（推荐，2048维）/ `embedding-2` |
| `--count` | `-1` | 测试行数上限，-1 为全部 |
| `--output` | `./output` | 输出目录 |
| `--api-key` | 环境变量 | 智谱 API Key |
| `--json-only` | false | 只输出 JSON |
| `--list-models` | — | 查询账号可用模型后退出 |

## 输出

- xlsx 两个 sheet：**向量结果**（序号、原文、维度、范数、prompt_tokens）、**相似度矩阵**
- JSON 输出在 `--- JSON_RESULT_START ---` / `--- JSON_RESULT_END ---` 之间

## 示例

**模式一：文本列表**
```bash
SCRIPT=$(find ~/.cursor ~/.claude ~/.codex ~/.openclaw -name "embedding_tester.py" 2>/dev/null | head -1)
python "$SCRIPT" --mode texts --texts "今天天气很好
明天会下雨
周末去爬山"
```

**模式二：文件批量（两列逐行相似度）**
```bash
python "$SCRIPT" --file ./data.xlsx --col query --col2 answer --count 50 --model embedding-3
```

**查看可用模型：**
```bash
python "$SCRIPT" --list-models
```
