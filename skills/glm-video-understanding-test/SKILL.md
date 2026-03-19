---
name: glm-video-understanding-test
description: 批量测试 GLM-4.6V 系列模型的视频理解能力。扫描本地目录下的视频文件，逐一调用智谱 AI 视频理解 API，将结果保存为 xlsx 并输出 JSON 摘要。当用户需要测试/评估视频理解模型效果、对一批视频做自动化分析、或验证 GLM-4.6V/glm-4.6v-flashx 对特定场景视频的理解质量时使用。触发词：测试视频理解、视频理解测评、批量测视频、GLM视频分析、glm-4.6v视频。
---

# GLM 视频理解批量测评

## 前置条件

```bash
# 安装依赖（仅需一次）
pip install zhipuai openpyxl

# 配置 API Key（选一种）
export ZHIPUAI_API_KEY="your_api_key_here"
# 或在调用时传入 --api-key 参数
```

脚本路径：`~/.cursor/skills/glm-video-understanding-test/scripts/video_tester.py`

## 调用方式

**最简调用（测试全部视频）：**
```bash
python ~/.cursor/skills/glm-video-understanding-test/scripts/video_tester.py \
  --folder /path/to/videos \
  --prompt "请描述这段视频的内容和操作步骤"
```

**只测试前 N 个视频（5 并发）：**
```bash
python ~/.cursor/skills/glm-video-understanding-test/scripts/video_tester.py \
  --folder /path/to/videos \
  --prompt "分析施工操作流程" \
  --count 10 \
  --model glm-4.6v \
  --concurrency 5
```

**agent 解析模式（只输出 JSON，无进度打印）：**
```bash
python ~/.cursor/skills/glm-video-understanding-test/scripts/video_tester.py \
  --folder /path/to/videos \
  --prompt "描述视频中的操作" \
  --json-only
```

## 参数说明

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--folder` | ✓ | — | 视频文件夹路径（递归扫描子目录） |
| `--prompt` | ✓ | — | 发送给模型的提示词 |
| `--model` | | `glm-4.6v-flashx` | 模型选择（见下方） |
| `--count` | | `-1`（全部） | 测试视频数量上限 |
| `--output` | | `./output` | xlsx 结果保存目录 |
| `--api-key` | | 读环境变量 | 智谱 AI API Key |
| `--concurrency` | | `1` | 并发请求数（建议 3-5，不超过 10） |
| `--json-only` | | false | 只输出 JSON，适合 agent 解析 |
| `--temperature` | | `0.1` | 温度参数 |
| `--max-tokens` | | `2048` | 最大输出 Token 数 |

**模型选择：**
- `glm-4.6v-flashx`：轻量高速（9B），日常测试首选
- `glm-4.6v`：旗舰版（106B），精度最高
- `glm-4.6v-flash`：完全免费版

## 读取 JSON 结果

脚本在 stdout 最后输出标记行，agent 可以截取 `--- JSON_RESULT_START ---` 和 `--- JSON_RESULT_END ---` 之间的内容解析：

```json
{
  "success": true,
  "total": 5,
  "success_count": 5,
  "fail_count": 0,
  "model": "glm-4.6v-flashx",
  "prompt": "描述视频操作步骤",
  "xlsx_path": "./output/03-17/视频理解测评_glm-4.6v-flashx_5个_03-17_14-30-00.xlsx",
  "results": [
    {
      "index": 1,
      "filename": "切片1.mp4",
      "path": "/path/to/切片1.mp4",
      "success": true,
      "content": "视频展示了...",
      "elapsed_ms": 3200,
      "error": ""
    }
  ]
}
```

## 典型用法示例

**场景：测试打钻视频前10个切片的理解效果**
```bash
python ~/.cursor/skills/glm-video-understanding-test/scripts/video_tester.py \
  --folder "/Users/xxx/Downloads/智谱-探水视频37/60s/打钻-后上杆-侧视" \
  --prompt "请描述视频中的钻探操作步骤，包括使用的工具和关键动作" \
  --count 10 \
  --model glm-4.6v-flashx
```

**场景：对比两个模型的输出质量**
```bash
# 先用 flashx 测
python ... --model glm-4.6v-flashx --count 3 --output ./output/flashx
# 再用旗舰版测同一批
python ... --model glm-4.6v --count 3 --output ./output/flagship
```

## 注意事项

- 视频以 base64 编码传输，单个视频文件建议不超过 **50MB**（对应约 60s 的 1080p 切片）
- 每个视频独立调用 API，结果实时写入 xlsx，中途中断不丢已完成数据
- `--concurrency` 并发时 xlsx 仍按原始顺序写入，进度日志会显示"[开始 x/n]"和"[完成 x/n]"
- 支持格式：`mp4 / mov / avi / mkv / webm`
