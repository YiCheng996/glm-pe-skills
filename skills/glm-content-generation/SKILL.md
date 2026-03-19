---
name: glm-content-generation
description: 使用智谱 CogView/CogVideoX 进行文生图、图生视频、文生视频。支持单条与批量（Excel/CSV）模式，CLI 驱动无 Gradio。触发词：文生图、图生视频、文生视频、CogView、CogVideoX、cogview-3-plus。
---

# GLM 内容生成

## 前置条件

```bash
pip install zhipuai openpyxl pandas
export ZHIPUAI_API_KEY="your_api_key"
```

脚本路径：`~/.cursor/skills/glm-content-generation/scripts/content_generator.py`

## 子命令

### t2i（文生图 - CogView）

```bash
# 单张
python ~/.cursor/skills/glm-content-generation/scripts/content_generator.py t2i \
  --prompt "一只橘猫在阳光下打盹" \
  --model cogview-3-plus

# 批量（Excel/CSV）
python ~/.cursor/skills/glm-content-generation/scripts/content_generator.py t2i \
  --file prompts.xlsx --col prompt \
  --output-dir ./output/images --concurrency 3
```

### i2v（图生视频 - CogVideoX）

```bash
python ~/.cursor/skills/glm-content-generation/scripts/content_generator.py i2v \
  --image ./input.png \
  --prompt "镜头缓慢推进" \
  --model cogvideox-flash
```

### t2v（文生视频）

```bash
python ~/.cursor/skills/glm-content-generation/scripts/content_generator.py t2v \
  --prompt "海浪拍打礁石，夕阳西下" \
  --output-dir ./output/videos
```

## 参数速查

| 子命令 | 必填 | 常用可选 |
|--------|------|----------|
| t2i | `--prompt` 或 `--file` | `--model`(cogview-3-plus/cogview-3/cogview-3-flash)、`--count`、`--col`、`--output-dir`、`--concurrency`(3) |
| i2v | `--image` | `--prompt`、`--model`(cogvideox-flash)、`--output-dir` |
| t2v | `--prompt` | `--model`(cogvideox-flash)、`--output-dir` |

通用：`--api-key`、`--json-only`（仅输出 JSON，便于 agent 解析）

## JSON 输出

所有模式在 stdout 末尾输出 `--- JSON_RESULT_START ---` / `--- JSON_RESULT_END ---` 标记，agent 可截取解析。t2i 批量结果另写入 xlsx（序号、prompt、图片URL、本地路径、耗时ms、成功/失败）。
