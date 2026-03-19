---
name: glm-video-understanding-test
description: >
  批量测试 GLM 视觉模型的视频理解能力。扫描本地目录下的视频文件，逐一调用智谱 AI 视频理解 API，将结果保存为 xlsx 并输出 JSON 摘要。
  触发词（中文）：测试视频理解、视频理解测评、批量测视频、GLM视频分析、glm-4.6v视频。
  Triggers (English): test video understanding, batch video analysis, GLM video understanding, glm-4.6v video test, video comprehension evaluation.
  Use when: user wants to evaluate/test video understanding quality, batch-analyze local video files, or benchmark GLM-4.6V / glm-4.6v-flashx on specific video scenarios.
allowed-tools: Bash
---

# GLM 视频理解批量测评

## 平台路径速查

| 平台 | 脚本路径 |
|------|---------|
| Cursor | `~/.cursor/skills/glm-video-understanding-test/scripts/video_tester.py` |
| Claude Code | `~/.claude/skills/glm-video-understanding-test/scripts/video_tester.py` |
| Codex | `~/.codex/skills/glm-video-understanding-test/scripts/video_tester.py` |
| OpenClaw | `~/.openclaw/skills/glm-video-understanding-test/scripts/video_tester.py` |

> Agent 调用时可用 Shell 自动定位：
> ```bash
> SCRIPT=$(find ~/.cursor ~/.claude ~/.codex ~/.openclaw -name "video_tester.py" 2>/dev/null | head -1)
> ```

## 前置条件

```bash
# 安装依赖（仅需一次）
pip install zhipuai openpyxl

# 配置 API Key（选一种）
export ZHIPUAI_API_KEY="your_api_key_here"
```

## 调用方式

**最简调用（测试全部视频）：**
```bash
SCRIPT=$(find ~/.cursor ~/.claude ~/.codex ~/.openclaw -name "video_tester.py" 2>/dev/null | head -1)
python "$SCRIPT" \
  --folder /path/to/videos \
  --prompt "请描述这段视频的内容和操作步骤"
```

**只测试前 N 个视频（5 并发）：**
```bash
python "$SCRIPT" \
  --folder /path/to/videos \
  --prompt "分析施工操作流程" \
  --count 10 \
  --model glm-4.6v \
  --concurrency 5
```

**查看可用模型：**
```bash
python "$SCRIPT" --list-models
```

## 参数说明

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--folder` | ✓ | — | 视频文件夹路径（递归扫描子目录） |
| `--prompt` | ✓ | — | 发送给模型的提示词 |
| `--model` | | `glm-4.6v-flashx` | 视频理解模型（--list-models 查看全部） |
| `--count` | | `-1`（全部） | 测试视频数量上限 |
| `--output` | | `./output` | xlsx 结果保存目录 |
| `--api-key` | | 读环境变量 | 智谱 AI API Key |
| `--concurrency` | | `1` | 并发请求数（建议 3-5） |
| `--json-only` | | false | 只输出 JSON，适合 agent 解析 |
| `--temperature` | | `0.1` | 温度参数 |
| `--max-tokens` | | `2048` | 最大输出 Token 数 |
| `--list-models` | | — | 查询账号可用模型后退出 |

## JSON 输出格式

脚本在 stdout 最后输出 `--- JSON_RESULT_START ---` / `--- JSON_RESULT_END ---` 之间的 JSON：

```json
{
  "success": true,
  "total": 5,
  "success_count": 5,
  "fail_count": 0,
  "model": "glm-4.6v-flashx",
  "xlsx_path": "./output/视频理解测评_glm-4.6v-flashx_5个_....xlsx",
  "results": [
    {
      "index": 1,
      "filename": "切片1.mp4",
      "success": true,
      "content": "视频展示了...",
      "elapsed_ms": 3200
    }
  ]
}
```

## 注意事项

- 视频以 base64 编码传输，单个文件建议不超过 **50MB**
- 支持格式：`mp4 / mov / avi / mkv / webm`
- 每个视频独立调用 API，中途中断不丢已完成数据
