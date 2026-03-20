---
name: glm-agent-test
description: >
  批量测试智谱 AI 平台（bigmodel.cn）上发布的智能体（应用）。支持文本输入、图片/文件/音频/视频上传，
  从目录、Excel 或 CSV 批量读取测试用例，多线程并发调用 Agent API，结果实时写入 xlsx 并输出 JSON 摘要。
  触发词（中文）：测试智能体、智能体测评、批量测智能体、GLM 智能体测试、bigmodel 应用测试、agent测试。
  Triggers (English): test bigmodel agent, batch agent evaluation, GLM agent test, test application on bigmodel, agent benchmark.
  Use when: user wants to evaluate a bigmodel.cn agent/application, batch-test prompts against an agent, or benchmark
  an agent's output quality across multiple inputs (text, images, files, video, audio).
allowed-tools: Bash
---

# GLM 智能体（Agent）批量测评

智谱 AI 智能体（应用）使用三步 API 流程：**上传文件 → 等待解析 → 调用推理**。
本 skill 封装了完整流程，支持纯文本与多模态输入的批量测试。

## 平台路径速查

| 平台 | 脚本路径 |
|------|---------|
| Cursor | `~/.cursor/skills/glm-agent-test/scripts/agent_tester.py` |
| Claude Code | `~/.claude/skills/glm-agent-test/scripts/agent_tester.py` |
| Codex | `~/.codex/skills/glm-agent-test/scripts/agent_tester.py` |
| OpenClaw | `~/.openclaw/skills/glm-agent-test/scripts/agent_tester.py` |

```bash
# Agent 可自动定位脚本
SCRIPT=$(find ~/.cursor ~/.claude ~/.codex ~/.openclaw \
         -name "agent_tester.py" 2>/dev/null | head -1)
```

## 前置条件

```bash
pip install requests openpyxl
export ZHIPUAI_API_KEY="your_api_key_here"
```

`APP_ID`（应用 ID）在智谱 AI 控制台 → 我的智能体列表页面获取。

## 调用方式

### 纯文本批量测试（从 Excel/CSV 读 prompt）

```bash
python "$SCRIPT" \
  --app-id 1848309397651148800 \
  --input-file prompts.xlsx \
  --input-col "用户输入" \
  --input-key "用户输入"
```

### 图片批量测试（目录下所有图片，每3张一组）

```bash
python "$SCRIPT" \
  --app-id 1958047571750592512 \
  --image-dir /path/to/images \
  --group-size 3 \
  --upload-unit-id 1755678409607958158
```

### 文件批量测试（目录下所有 PDF/docx）

```bash
python "$SCRIPT" \
  --app-id 1848309397651148800 \
  --file-dir /path/to/docs \
  --upload-unit-id 1737528754381717495 \
  --file-type 2
```

### 视频/音频批量测试

```bash
python "$SCRIPT" \
  --app-id 1848309397651148800 \
  --file-dir /path/to/videos \
  --upload-unit-id 1737528778264408584 \
  --file-type 5
```

### 查询智能体输入参数（获取 upload-unit-id）

```bash
python "$SCRIPT" --app-id 1848309397651148800 --list-vars
```

## 参数说明

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--app-id` | ✓ | — | 智能体（应用）ID |
| `--api-key` | | 读环境变量 | 智谱 AI API Key |
| `--input-file` | | — | Excel/CSV 文件路径（文本测试模式） |
| `--input-col` | | `input` | input-file 中 prompt 所在列名 |
| `--input-key` | | `用户输入` | 对应智能体变量名（3.1接口返回的 name） |
| `--image-dir` | | — | 图片目录（图片测试模式） |
| `--group-size` | | `1` | 每次调用传入的图片数量 |
| `--file-dir` | | — | 文件目录（文件/视频/音频测试模式） |
| `--upload-unit-id` | | — | 上传组件 ID（文件/图片模式必填）|
| `--file-type` | | `4` | 1=excel 2=文档 3=音频 4=图片 5=视频 |
| `--concurrency` | | `2` | 并发线程数（建议 2-4，避免限流）|
| `--count` | | `-1`（全部）| 测试数量上限 |
| `--output` | | `./output` | xlsx 结果保存目录 |
| `--list-vars` | | — | 查询智能体输入变量后退出 |
| `--json-only` | | false | 只输出 JSON 摘要 |

## JSON 输出格式

脚本在 stdout 末尾输出 `--- JSON_RESULT_START ---` / `--- JSON_RESULT_END ---` 之间的 JSON：

```json
{
  "success": true,
  "app_id": "1958047571750592512",
  "total": 113,
  "success_count": 112,
  "fail_count": 1,
  "xlsx_path": "./output/agent_test_....xlsx",
  "results": [
    {
      "index": 1,
      "input_files": ["frame_000001.jpg", "frame_000002.jpg", "frame_000003.jpg"],
      "success": true,
      "output": "{\"判断是否异常\": \"是\", \"异常类型\": \"手部离开写作区\"}",
      "elapsed_ms": 18400
    }
  ]
}
```

## API 关键说明

> 详见 [api-reference.md](api-reference.md)

- **服务地址**：`https://open.bigmodel.cn/api/llm-application/open`
- **上传响应 key**：`data.successInfo[].fileId`（camelCase，非 snake_case）
- **推理响应路径**：`choices[0].messages.content.msg`
- **文本类智能体**：`messages.content` 中 `key` 字段必须与智能体变量 `name` 完全一致
- **图片/文件上传**：需传 `upload_unit_id`（通过 `--list-vars` 获取）

## 注意事项

- 并发建议 2-4；超过 5 容易触发服务端限流（`invoke_failed`）
- 图片每组最多传 9 张，单张不超过 5MB，支持 jpg/png/jpeg
- 文件上传后需等待解析（脚本自动轮询，最长 60s）
- 失败的组会标记 `invoke_failed`，不会中断整体测试

## 附：快速获取 upload-unit-id

```bash
python "$SCRIPT" --app-id <YOUR_APP_ID> --list-vars
# 输出示例：
# id=1755678409607958158  type=upload_image  name=图片
# id=1737528754381717495  type=upload_file   name=文件
```
