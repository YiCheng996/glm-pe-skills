---
name: glm-text-batch-test
description: 批量测试 GLM 文本模型的调用效果。支持从多行文本或 Excel/CSV 文件读取 prompt，使用模板变量替换，多线程并发调用智谱 Chat API，结果写入 xlsx 并输出 JSON 摘要。触发词：文本批量测试、Excel批量调用、GLM批量、多列变量测试。
---

# GLM 文本批量测试

## 前置条件

```bash
pip install zhipuai openpyxl pandas
export ZHIPUAI_API_KEY="your_api_key_here"
```

脚本路径：`~/.cursor/skills/glm-text-batch-test/scripts/text_tester.py`

## 参数一览

| 参数 | 默认 | 说明 |
|------|------|------|
| `--mode` | file | text / file |
| `--input` | — | [text] 输入文件，每行一 prompt 或 *** 分隔块 |
| `--file` | — | [file] Excel/CSV 路径 |
| `--sheet` | 首 sheet | [file] Excel sheet 名 |
| `--prompt-template` | {input} | 支持 {input} 或 {列名} |
| `--input-col` | — | [file] 单列快捷，等价于 `{列名}` |
| `--model` | glm-4.5 | 任意智谱模型 |
| `--system` | — | system prompt |
| `--temperature` | 0.1 | 温度 |
| `--top-p` | 0.8 | Top-P |
| `--max-tokens` | 4096 | 最大输出 token |
| `--thinking-mode` | disabled | enabled/disabled |
| `--count` | -1 | 行数上限，-1 全部 |
| `--concurrency` | 3 | 并发数 |
| `--output` | ./output | 输出目录 |
| `--api-key` | 环境变量 | API Key |
| `--json-only` | false | 仅输出 JSON |

## 示例

**文件批量（Excel 单列）：**
```bash
python ~/.cursor/skills/glm-text-batch-test/scripts/text_tester.py \
  --file prompts.xlsx --input-col 问题 --model glm-4.5 --count 10
```

**多列变量模板：**
```bash
python ~/.cursor/skills/glm-text-batch-test/scripts/text_tester.py \
  --file data.csv --prompt-template "分析：{A列} 与 {B列} 的关系" --concurrency 5
```

**文本批量：**
```bash
python ~/.cursor/skills/glm-text-batch-test/scripts/text_tester.py \
  --mode text --input prompts.txt --prompt-template "请分析：{input}"
```

## JSON 输出

stdout 末尾输出 `--- JSON_RESULT_START ---` / `--- JSON_RESULT_END ---` 之间的 JSON，含 `total`、`success_count`、`xlsx_path`、`results`。
