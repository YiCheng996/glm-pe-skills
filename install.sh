#!/usr/bin/env bash
# install.sh — GLM PE Skills 一键安装脚本
# 用法：curl -fsSL https://raw.githubusercontent.com/YiCheng996/glm-pe-skills/main/install.sh | bash
# 支持选项：
#   SKILLS="skill1 skill2"  安装指定 skill（空格分隔），默认安装全部
#   SKILLS_DIR="/自定义路径" 安装到指定目录，默认 ~/.cursor/skills

set -e

REPO="YiCheng996/glm-pe-skills"
BRANCH="main"
RAW_BASE="https://raw.githubusercontent.com/${REPO}/${BRANCH}"
API_BASE="https://api.github.com/repos/${REPO}/contents"

# 安装目标目录：优先读环境变量，其次默认 ~/.cursor/skills
SKILLS_DIR="${SKILLS_DIR:-${HOME}/.cursor/skills}"

# 所有可用 skill 列表（新增 skill 后在此追加）
ALL_SKILLS=(
  "glm-video-understanding-test"
  "glm-text-batch-test"
  "glm-image-understanding-test"
  "glm-embedding-test"
  "glm-content-generation"
)

# 若用户通过环境变量指定了要安装的 skill，则只安装那些；否则安装全部
if [ -n "${SKILLS}" ]; then
  # 把空格分隔的字符串转成数组
  IFS=' ' read -r -a TARGET_SKILLS <<< "${SKILLS}"
else
  TARGET_SKILLS=("${ALL_SKILLS[@]}")
fi

# ── 工具函数 ────────────────────────────────────────────────────────────────

# 检查命令是否存在
need_cmd() {
  if ! command -v "$1" &>/dev/null; then
    echo "❌ 需要 '$1' 命令但未找到，请先安装后重试。"
    exit 1
  fi
}

# 通过 GitHub API 列出目录下所有文件，递归下载
# 参数：$1=仓库路径（如 skills/foo/scripts），$2=本地目标目录
download_dir() {
  local remote_path="$1"
  local local_dir="$2"
  mkdir -p "$local_dir"

  # 调用 GitHub Contents API，获取目录内容列表
  local api_url="${API_BASE}/${remote_path}?ref=${BRANCH}"
  local items
  items=$(curl -fsSL "$api_url" 2>/dev/null) || {
    echo "  ⚠ 无法获取目录列表：${remote_path}，尝试直接跳过"
    return 0
  }

  # 解析 JSON（不依赖 jq，用 Python 处理）
  python3 - <<PYEOF
import json, sys, os, urllib.request

items = json.loads('''${items}''')
for item in items:
    name = item['name']
    typ  = item['type']
    path = item['path']
    if typ == 'file':
        url = item['download_url']
        dest = os.path.join('${local_dir}', name)
        print(f'    ↓  {name}')
        urllib.request.urlretrieve(url, dest)
    elif typ == 'dir':
        # 递归：通知 shell 继续处理子目录
        # （Python 无法直接调用 shell 函数，改用 subprocess）
        import subprocess
        subprocess.run(
            ['bash', '-c', f'source {os.path.abspath("${0:-install.sh}")} 2>/dev/null; download_dir "{path}" "${local_dir}/{name}"'],
            check=False
        )
PYEOF
}

# 下载单个 skill（SKILL.md + scripts/ 目录）
install_skill() {
  local skill_name="$1"
  local dest="${SKILLS_DIR}/${skill_name}"

  if [ -d "$dest" ]; then
    echo "⏭  ${skill_name} 已安装，跳过（如需更新：rm -rf ${dest} 后重新运行）"
    return 0
  fi

  echo "⬇  安装 ${skill_name} ..."
  mkdir -p "${dest}/scripts"

  # 下载 SKILL.md
  local skill_md_url="${RAW_BASE}/skills/${skill_name}/SKILL.md"
  if curl -fsSL "$skill_md_url" -o "${dest}/SKILL.md" 2>/dev/null; then
    echo "   ✓ SKILL.md"
  else
    echo "   ⚠ ${skill_name} 暂未发布，跳过"
    rm -rf "$dest"
    return 0
  fi

  # 下载 scripts/ 目录下所有 .py 文件（通过 GitHub API 列出）
  local scripts_api="${API_BASE}/skills/${skill_name}/scripts?ref=${BRANCH}"
  local scripts_json
  if scripts_json=$(curl -fsSL "$scripts_api" 2>/dev/null); then
    python3 - <<PYEOF
import json, urllib.request, os

items = json.loads('''${scripts_json}''')
scripts_dir = '${dest}/scripts'
os.makedirs(scripts_dir, exist_ok=True)
for item in items:
    if item['type'] == 'file':
        url  = item['download_url']
        name = item['name']
        dest = os.path.join(scripts_dir, name)
        print(f'   ✓ scripts/{name}')
        urllib.request.urlretrieve(url, dest)
PYEOF
  fi

  echo "✅  ${skill_name} 安装完成 → ${dest}"
}

# ── 主流程 ───────────────────────────────────────────────────────────────────

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║       GLM PE Skills 安装程序              ║"
echo "║  github.com/${REPO}  ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# 依赖检查
need_cmd curl
need_cmd python3

mkdir -p "${SKILLS_DIR}"

echo "安装目录：${SKILLS_DIR}"
echo "即将安装：${TARGET_SKILLS[*]}"
echo ""

for skill in "${TARGET_SKILLS[@]}"; do
  install_skill "$skill"
done

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  🎉 安装完成！                            ║"
echo "║  请重启 Cursor，Skills 即自动生效。        ║"
echo "║                                          ║"
echo "║  配置 API Key（任选其一）：               ║"
echo "║  export ZHIPUAI_API_KEY=\"your_key\"        ║"
echo "╚══════════════════════════════════════════╝"
echo ""
