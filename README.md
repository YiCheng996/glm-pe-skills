# GLM PE Skills

> 智谱 AI GLM 系列模型的 **Cursor Agent Skills** 合集，专为探水、测评、批量分析场景设计。

[![GitHub stars](https://img.shields.io/github/stars/YiCheng996/glm-pe-skills?style=flat-square)](https://github.com/YiCheng996/glm-pe-skills/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

---

## 一键安装（Cursor）

```bash
curl -fsSL https://raw.githubusercontent.com/YiCheng996/glm-pe-skills/main/install.sh | bash
```

安装完成后**重启 Cursor**，在 Agent 对话中直接触发即可使用。

> **只安装指定 skill：**
> ```bash
> SKILLS="glm-video-understanding-test glm-text-batch-test" \
>   curl -fsSL https://raw.githubusercontent.com/YiCheng996/glm-pe-skills/main/install.sh | bash
> ```

---

## 包含的 Skills

| Skill | 状态 | 触发词 / 使用场景 |
|-------|:----:|-----------------|
| [glm-video-understanding-test](skills/glm-video-understanding-test/) | ✅ 已发布 | 视频理解测评、批量分析视频、glm-4.6v 视频 |
| [glm-text-batch-test](skills/glm-text-batch-test/) | ✅ 已发布 | 文本批量测试、Excel 批量调用、{列名}变量替换、多线程 |
| [glm-image-understanding-test](skills/glm-image-understanding-test/) | ✅ 已发布 | 图生文、批量图片理解、GLM-4V 系列评测 |
| [glm-embedding-test](skills/glm-embedding-test/) | ✅ 已发布 | Embedding 评测、余弦相似度矩阵、向量化 |
| [glm-content-generation](skills/glm-content-generation/) | ✅ 已发布 | 文生图(CogView)、图生视频、文生视频(CogVideoX) |

---

## 前置条件

```bash
# 安装 Python 依赖
pip install zhipuai openpyxl pandas pillow

# 配置 API Key（任选其一）
export ZHIPUAI_API_KEY="your_api_key_here"
# 或在调用 skill 时传入 --api-key 参数
```

---

## 使用示例

安装完成后，在 Cursor Agent 对话框中直接说：

```
测试视频理解：
  对 /path/to/videos 里的视频批量跑 glm-4.6v，
  提示词"描述钻探操作步骤"，并发 5，测前 20 个
```

```
文本批量测试：
  用 glm-4.5 批量跑 data.xlsx 的 A 列，
  提示词模板 "请分析以下内容：{input}"
```

Agent 会自动选择匹配的 skill 并执行。

---

## 手动安装（不用 curl）

```bash
git clone https://github.com/YiCheng996/glm-pe-skills.git
cp -r glm-pe-skills/skills/glm-video-understanding-test ~/.cursor/skills/
# 按需复制其他 skill
```

---

## 更新 Skill

```bash
# 删除旧版本后重新安装
rm -rf ~/.cursor/skills/glm-video-understanding-test
curl -fsSL https://raw.githubusercontent.com/YiCheng996/glm-pe-skills/main/install.sh | bash
```

---

## 贡献 / 反馈

欢迎提 [Issue](https://github.com/YiCheng996/glm-pe-skills/issues) 或 PR，告诉我你希望支持的场景。

---

## License

MIT © [YiCheng996](https://github.com/YiCheng996)
