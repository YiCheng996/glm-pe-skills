# GLM PE Skills

> 智谱 AI GLM 系列模型的 **Agent Skills** 合集，兼容 **Cursor · Claude Code · Codex · OpenClaw** 

[![GitHub stars](https://img.shields.io/github/stars/YiCheng996/glm-pe-skills?style=flat-square)](https://github.com/YiCheng996/glm-pe-skills/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

---

## 一键安装

脚本会**自动检测**当前机器已安装的平台，并将 Skills 同时安装到所有检测到的平台目录：

```bash
curl -fsSL https://raw.githubusercontent.com/YiCheng996/glm-pe-skills/main/install.sh | bash
```

安装完成后**重启对应平台**，即可在 Agent 对话中直接触发。

### 指定平台安装

```bash
# 只安装到 Claude Code
PLATFORM=claudecode curl -fsSL .../install.sh | bash

# 只安装到 Codex
PLATFORM=codex curl -fsSL .../install.sh | bash

# 只安装到 OpenClaw
PLATFORM=openclaw curl -fsSL .../install.sh | bash

# 强制安装到全部四个平台
PLATFORM=all curl -fsSL .../install.sh | bash
```

可选平台值：`cursor` · `claudecode` · `codex` · `openclaw` · `all`

### 只安装指定 Skill

```bash
SKILLS="glm-video-understanding-test glm-text-batch-test" \
  curl -fsSL https://raw.githubusercontent.com/YiCheng996/glm-pe-skills/main/install.sh | bash
```

### 各平台安装目录

| 平台 | Skills 目录 |
|------|------------|
| Cursor | `~/.cursor/skills/` |
| Claude Code | `~/.claude/skills/` |
| Codex | `~/.codex/skills/` |
| OpenClaw | `~/.openclaw/skills/` |

---

## 包含的 Skills

| Skill | 状态 | 触发词 / 使用场景 |
|-------|:----:|-----------------|
| [glm-agent-test](skills/glm-agent-test/) | ✅ 已发布 | 测试智能体、智能体测评、批量测智能体、bigmodel 应用测试 / test bigmodel agent, batch agent evaluation |
| [glm-video-understanding-test](skills/glm-video-understanding-test/) | ✅ 已发布 | 视频理解测评、批量分析视频、glm-4.6v 视频 / batch video analysis |
| [glm-text-batch-test](skills/glm-text-batch-test/) | ✅ 已发布 | 文本批量测试、Excel 批量调用、多列变量替换 / batch text test |
| [glm-image-understanding-test](skills/glm-image-understanding-test/) | ✅ 已发布 | 图生文、批量图片理解、GLM-4V 评测 / batch image analysis |
| [glm-embedding-test](skills/glm-embedding-test/) | ✅ 已发布 | Embedding 评测、余弦相似度矩阵 / embedding benchmark |
| [glm-content-generation](skills/glm-content-generation/) | ✅ 已发布 | 文生图(CogView-4)、图/文生视频(CogVideoX/Vidu) / text-to-image, video generation |

---

## 前置条件

```bash
# 安装 Python 依赖
pip install zhipuai openpyxl pandas numpy

# 配置 API Key（任选其一）
export ZHIPUAI_API_KEY="your_api_key_here"
# 或在调用 skill 时传入 --api-key 参数
```

---

## 使用示例

安装完成后，在任意平台的 Agent 对话框中直接说：

```
测试视频理解：
  对 /path/to/videos 里的视频批量跑 glm-4.6v，
  提示词"描述钻探操作步骤"，并发 5，测前 20 个
```

```
batch image analysis:
  analyze all images in /path/to/images with glm-4.6v-flashx
  prompt: "describe the objects and scene in this image"
```

```
文本批量测试：
  用 glm-4.5 批量跑 data.xlsx 的 A 列，
  提示词模板 "请分析以下内容：{input}"
```

Agent 会自动选择匹配的 Skill 并执行。

```
测试智能体：
  批量测 bigmodel 上的图片巡课智能体，
  app-id=1958...，图片目录 /path/to/frames，每3张一组
```

---

## 手动安装

```bash
git clone https://github.com/YiCheng996/glm-pe-skills.git

# Cursor
cp -r glm-pe-skills/skills/glm-video-understanding-test ~/.cursor/skills/

# Claude Code
cp -r glm-pe-skills/skills/glm-video-understanding-test ~/.claude/skills/

# Codex
cp -r glm-pe-skills/skills/glm-video-understanding-test ~/.codex/skills/

# OpenClaw
cp -r glm-pe-skills/skills/glm-video-understanding-test ~/.openclaw/skills/
```

---

## 更新 Skill

```bash
# 删除旧版本后重新安装（以 Cursor 为例）
rm -rf ~/.cursor/skills/glm-video-understanding-test
curl -fsSL https://raw.githubusercontent.com/YiCheng996/glm-pe-skills/main/install.sh | bash
```

---

## 贡献 / 反馈

欢迎提 [Issue](https://github.com/YiCheng996/glm-pe-skills/issues) 或 PR，告诉我你希望支持的场景。

---

## License

MIT © [YiCheng996](https://github.com/YiCheng996)
