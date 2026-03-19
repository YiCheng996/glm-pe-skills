---
name: glm-embedding-test
description: 批量评测智谱 GLM Embedding 模型（embedding-3/embedding-2）的文本向量化能力，计算余弦相似度矩阵。当用户需要 Embedding评测、向量化、余弦相似度、文本相似度、embedding-3 相关测试时使用。
---

# GLM Embedding 评测

## 前置条件

```bash
pip install zhipuai openpyxl numpy pandas
export ZHIPUAI_API_KEY="your_api_key"
```

脚本路径：`~/.cursor/skills/glm-embedding-test/scripts/embedding_tester.py`

## 参数说明

| 参数 | 默认 | 说明 |
|------|------|------|
| `--mode` | `file` | `texts` 或 `file` |
| `--texts` | — | 多行文本（每行一条或 `***` 分隔） |
| `--file` | — | Excel(.xlsx) 或 CSV 路径 |
| `--col` | 第一列 | 指定列名 |
| `--col2` | — | 第二列，用于逐行相似度（query vs answer） |
| `--sheet` | — | Excel sheet 名 |
| `--model` | `embedding-3` | `embedding-3` 或 `embedding-2` |
| `--count` | `-1` | 测试行数上限，-1 为全部 |
| `--output` | `./output` | 输出目录 |
| `--api-key` | 环境变量 | 智谱 API Key |
| `--json-only` | false | 只输出 JSON |

## 输出

- xlsx 两个 sheet：**向量结果**（序号、原文、维度、范数、prompt_tokens）、**相似度矩阵**
- JSON 输出在 `--- JSON_RESULT_START ---` / `--- JSON_RESULT_END ---` 之间

## 示例

**模式一：文本列表**
```bash
python ~/.cursor/skills/glm-embedding-test/scripts/embedding_tester.py \
  --mode texts \
  --texts "今天天气很好
明天会下雨
***
周末去爬山"
```

**模式二：文件批量（两列逐行相似度）**
```bash
python ~/.cursor/skills/glm-embedding-test/scripts/embedding_tester.py \
  --file ./data.xlsx \
  --col query \
  --col2 answer \
  --count 50 \
  --model embedding-3
```
