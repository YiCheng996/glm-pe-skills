---
name: glm-content-generation
description: >
  使用智谱多模态模型生成图像或视频。支持文生图（CogView-4 / GLM-Image）、图生视频、文生视频（CogVideoX / Vidu）三种模式，支持批量（Excel/CSV），CLI 驱动无 Gradio。
  触发词（中文）：文生图、图生视频、文生视频、CogView、CogVideoX、Vidu、cogview-4、图像生成、视频生成。
  Triggers (English): text-to-image, image-to-video, text-to-video, generate image, generate video, CogView, CogVideoX, Vidu, GLM image generation, AI image creation, AI video generation.
  Use when: user wants to generate images from text prompts, convert images to videos, or generate videos from text descriptions using ZhipuAI multimodal models.
allowed-tools: Bash
---

# GLM 内容生成

## 平台路径速查

| 平台 | 脚本路径 |
|------|---------|
| Cursor | `~/.cursor/skills/glm-content-generation/scripts/content_generator.py` |
| Claude Code | `~/.claude/skills/glm-content-generation/scripts/content_generator.py` |
| Codex | `~/.codex/skills/glm-content-generation/scripts/content_generator.py` |
| OpenClaw | `~/.openclaw/skills/glm-content-generation/scripts/content_generator.py` |

> Agent 调用时可用 Shell 自动定位：
> ```bash
> SCRIPT=$(find ~/.cursor ~/.claude ~/.codex ~/.openclaw -name "content_generator.py" 2>/dev/null | head -1)
> ```

## 前置条件

```bash
pip install zhipuai openpyxl pandas
export ZHIPUAI_API_KEY="your_api_key"
```

## 子命令

### t2i — 文生图（CogView-4 / GLM-Image）

```bash
SCRIPT=$(find ~/.cursor ~/.claude ~/.codex ~/.openclaw -name "content_generator.py" 2>/dev/null | head -1)

# 单张（默认模型 cogview-4）
python "$SCRIPT" t2i --prompt "一只橘猫在阳光下打盹"

# 指定模型
python "$SCRIPT" t2i --prompt "星空下的山脉" --model glm-image

# 批量（Excel/CSV）
python "$SCRIPT" t2i --file prompts.xlsx --col prompt --output-dir ./output/images --concurrency 3
```

### i2v — 图生视频（CogVideoX / Vidu）

```bash
python "$SCRIPT" i2v \
  --image ./input.png \
  --prompt "镜头缓慢推进" \
  --model cogvideox-flash
```

### t2v — 文生视频（CogVideoX / Vidu）

```bash
python "$SCRIPT" t2v \
  --prompt "海浪拍打礁石，夕阳西下" \
  --model cogvideox-flash \
  --output-dir ./output/videos
```

### 查看可用模型

```bash
python "$SCRIPT" --list-models
```

## 参数速查

| 子命令 | 必填 | 常用可选 |
|--------|------|----------|
| t2i | `--prompt` 或 `--file` | `--model`（cogview-4/glm-image/cogview-3-flash）、`--count`、`--col`、`--output-dir`、`--concurrency`(3) |
| i2v | `--image` | `--prompt`、`--model`(cogvideox-flash)、`--output-dir` |
| t2v | `--prompt` | `--model`(cogvideox-flash)、`--output-dir` |

通用：`--api-key`、`--json-only`（仅输出 JSON，便于 agent 解析）、`--list-models`

## JSON 输出

所有模式在 stdout 末尾输出 `--- JSON_RESULT_START ---` / `--- JSON_RESULT_END ---` 标记，agent 可截取解析。t2i 批量结果另写入 xlsx。
