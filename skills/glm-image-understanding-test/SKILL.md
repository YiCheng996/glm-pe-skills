---
name: glm-image-understanding-test
description: >
  批量测试 GLM 视觉模型的图像理解能力。递归扫描本地目录下的图片文件，将图片 base64 编码后调用智谱 AI 图像理解 API，结果实时写入 xlsx 并输出 JSON 摘要。
  触发词（中文）：图生文、图像理解测评、批量图片分析、GLM-4V、glm-4.5v图像、图像识别批量。
  Triggers (English): image understanding test, batch image analysis, image-to-text evaluation, GLM vision model test, glm-4.6v image, batch OCR, image comprehension.
  Use when: user wants to batch-test GLM vision models with local images, evaluate image understanding quality, or run batch image captioning/analysis.
allowed-tools: Bash
---

# GLM 图像理解批量测评

## 平台路径速查

| 平台 | 脚本路径 |
|------|---------|
| Cursor | `~/.cursor/skills/glm-image-understanding-test/scripts/image_tester.py` |
| Claude Code | `~/.claude/skills/glm-image-understanding-test/scripts/image_tester.py` |
| Codex | `~/.codex/skills/glm-image-understanding-test/scripts/image_tester.py` |
| OpenClaw | `~/.openclaw/skills/glm-image-understanding-test/scripts/image_tester.py` |

> Agent 调用时可用 Shell 自动定位：
> ```bash
> SCRIPT=$(find ~/.cursor ~/.claude ~/.codex ~/.openclaw -name "image_tester.py" 2>/dev/null | head -1)
> ```

## 前置条件

```bash
pip install zhipuai openpyxl
export ZHIPUAI_API_KEY="your_api_key_here"
```

## 参数说明

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--folder` | ✓ | — | 图片文件夹路径（递归扫描） |
| `--prompt` | ✓ | — | 发给模型的提问 |
| `--model` | | `glm-4.6v-flashx` | 视觉模型（--list-models 查看全部） |
| `--system` | | — | system prompt（可选） |
| `--thinking-mode` | | `disabled` | disabled/enabled |
| `--temperature` | | `0.1` | 温度 |
| `--top-p` | | `0.8` | Top-P |
| `--max-tokens` | | `2048` | 最大输出 Token |
| `--count` | | `-1`（全部） | 测试数量上限 |
| `--concurrency` | | `3` | 并发数 |
| `--output` | | `./output` | 输出目录 |
| `--api-key` | | 环境变量 | API Key |
| `--json-only` | | false | 只输出 JSON |
| `--list-models` | | — | 查询账号可用模型后退出 |

支持格式：jpg/jpeg/png/gif/webp/bmp

## 典型用法

**最简调用：**
```bash
SCRIPT=$(find ~/.cursor ~/.claude ~/.codex ~/.openclaw -name "image_tester.py" 2>/dev/null | head -1)
python "$SCRIPT" --folder /path/to/images --prompt "请描述这张图片的内容"
```

**指定模型与并发：**
```bash
python "$SCRIPT" --folder /path/to/images --prompt "识别图中的物体和场景" \
  --model glm-4.6v --count 20 --concurrency 5
```

**查看可用模型：**
```bash
python "$SCRIPT" --list-models
```

## JSON 输出

脚本在 stdout 末尾输出 `--- JSON_RESULT_START ---` 与 `--- JSON_RESULT_END ---` 之间的 JSON，agent 可解析。xlsx 文件名格式：`图像理解测评_{model}_{n}张_{日期时间}.xlsx`。
