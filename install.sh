#!/usr/bin/env bash
# install.sh — GLM PE Skills 多平台一键安装脚本
#
# 用法：
#   curl -fsSL https://raw.githubusercontent.com/YiCheng996/glm-pe-skills/main/install.sh | bash
#
# 环境变量（均可选）：
#   PLATFORM="cursor"           只装到指定平台（cursor/claudecode/codex/openclaw/all），默认自动检测
#   SKILLS="skill1 skill2"      只安装指定 skill（空格分隔），默认全部
#   SKILLS_DIR="/自定义路径"     覆盖所有平台安装到此目录（调试用）

set -e

REPO="YiCheng996/glm-pe-skills"
BRANCH="main"
RAW_BASE="https://raw.githubusercontent.com/${REPO}/${BRANCH}"
API_BASE="https://api.github.com/repos/${REPO}/contents"

# ── 平台目录定义 ─────────────────────────────────────────────────────────────
declare -A PLATFORM_DIRS=(
  ["cursor"]="${HOME}/.cursor/skills"
  ["claudecode"]="${HOME}/.claude/skills"
  ["codex"]="${HOME}/.codex/skills"
  ["openclaw"]="${HOME}/.openclaw/skills"
)

# ── 检测当前机器安装了哪些平台 ─────────────────────────────────────────────
detect_platforms() {
  local detected=()
  # Cursor：检测 ~/.cursor 目录
  [[ -d "${HOME}/.cursor" ]] && detected+=("cursor")
  # Claude Code：检测 ~/.claude 目录
  [[ -d "${HOME}/.claude" ]] && detected+=("claudecode")
  # Codex：检测 ~/.codex 目录
  [[ -d "${HOME}/.codex" ]] && detected+=("codex")
  # OpenClaw：检测 ~/.openclaw 目录
  [[ -d "${HOME}/.openclaw" ]] && detected+=("openclaw")
  echo "${detected[@]}"
}

# ── 确定要安装的平台列表 ────────────────────────────────────────────────────
if [ -n "${SKILLS_DIR}" ]; then
  # 用户指定了自定义目录，直接用
  TARGET_PLATFORM_DIRS=("${SKILLS_DIR}")
  TARGET_PLATFORM_LABELS=("custom:${SKILLS_DIR}")
elif [ -n "${PLATFORM}" ]; then
  if [ "${PLATFORM}" = "all" ]; then
    # 强制安装到所有四个平台
    TARGET_PLATFORM_DIRS=(
      "${PLATFORM_DIRS[cursor]}"
      "${PLATFORM_DIRS[claudecode]}"
      "${PLATFORM_DIRS[codex]}"
      "${PLATFORM_DIRS[openclaw]}"
    )
    TARGET_PLATFORM_LABELS=("cursor" "claudecode" "codex" "openclaw")
  else
    # 用户指定了单一平台
    dir="${PLATFORM_DIRS[$PLATFORM]}"
    if [ -z "$dir" ]; then
      echo "❌ 未知平台：${PLATFORM}（可选：cursor / claudecode / codex / openclaw / all）"
      exit 1
    fi
    TARGET_PLATFORM_DIRS=("$dir")
    TARGET_PLATFORM_LABELS=("$PLATFORM")
  fi
else
  # 自动检测：安装到所有已检测到的平台，至少保底安装 cursor
  read -ra detected_list <<< "$(detect_platforms)"
  if [ ${#detected_list[@]} -eq 0 ]; then
    detected_list=("cursor")
  fi
  TARGET_PLATFORM_DIRS=()
  TARGET_PLATFORM_LABELS=()
  for p in "${detected_list[@]}"; do
    TARGET_PLATFORM_DIRS+=("${PLATFORM_DIRS[$p]}")
    TARGET_PLATFORM_LABELS+=("$p")
  done
fi

# ── Skill 列表 ───────────────────────────────────────────────────────────────
ALL_SKILLS=(
  "glm-video-understanding-test"
  "glm-text-batch-test"
  "glm-image-understanding-test"
  "glm-embedding-test"
  "glm-content-generation"
)

if [ -n "${SKILLS}" ]; then
  IFS=' ' read -r -a TARGET_SKILLS <<< "${SKILLS}"
else
  TARGET_SKILLS=("${ALL_SKILLS[@]}")
fi

# ── 工具函数 ─────────────────────────────────────────────────────────────────

need_cmd() {
  if ! command -v "$1" &>/dev/null; then
    echo "❌ 需要 '$1' 命令但未找到，请先安装后重试。"
    exit 1
  fi
}

# 下载单个 skill（SKILL.md + scripts/ 目录）到指定目录
install_skill_to_dir() {
  local skill_name="$1"
  local skills_dir="$2"
  local dest="${skills_dir}/${skill_name}"

  if [ -d "$dest" ]; then
    echo "   ⏭  已存在，跳过（rm -rf ${dest} 后可重装）"
    return 0
  fi

  mkdir -p "${dest}/scripts"

  # 下载 SKILL.md
  local skill_md_url="${RAW_BASE}/skills/${skill_name}/SKILL.md"
  if curl -fsSL "$skill_md_url" -o "${dest}/SKILL.md" 2>/dev/null; then
    echo "   ✓ SKILL.md"
  else
    echo "   ⚠ 暂未发布，跳过"
    rm -rf "$dest"
    return 0
  fi

  # 通过 GitHub API 下载 scripts/ 下所有文件
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
        dst  = os.path.join(scripts_dir, name)
        print(f'   \u2713 scripts/{name}')
        urllib.request.urlretrieve(url, dst)
PYEOF
  fi

  echo "   ✅ ${dest}"
}

# ── 主流程 ───────────────────────────────────────────────────────────────────

echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║       GLM PE Skills  多平台安装程序             ║"
echo "║   github.com/${REPO}   ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

need_cmd curl
need_cmd python3

echo "检测到的目标平台："
for i in "${!TARGET_PLATFORM_LABELS[@]}"; do
  echo "  • ${TARGET_PLATFORM_LABELS[$i]}  →  ${TARGET_PLATFORM_DIRS[$i]}"
done
echo ""
echo "即将安装 Skills：${TARGET_SKILLS[*]}"
echo ""

# 遍历每个平台 × 每个 skill
for i in "${!TARGET_PLATFORM_DIRS[@]}"; do
  platform_label="${TARGET_PLATFORM_LABELS[$i]}"
  skills_dir="${TARGET_PLATFORM_DIRS[$i]}"
  mkdir -p "$skills_dir"

  echo "▶ 平台：${platform_label}  (${skills_dir})"
  for skill in "${TARGET_SKILLS[@]}"; do
    echo "  ⬇  ${skill}"
    install_skill_to_dir "$skill" "$skills_dir"
  done
  echo ""
done

echo "╔════════════════════════════════════════════════╗"
echo "║  🎉 安装完成！                                  ║"
echo "║                                                ║"
echo "║  各平台激活方式：                               ║"
echo "║  Cursor      — 重启 Cursor 即自动生效           ║"
echo "║  Claude Code — 重启 claude 命令行即生效          ║"
echo "║  Codex       — 重启 codex 命令行即生效           ║"
echo "║  OpenClaw    — 重启 OpenClaw 即自动生效          ║"
echo "║                                                ║"
echo "║  配置 API Key（任选其一）：                     ║"
echo "║  export ZHIPUAI_API_KEY=\"your_key\"             ║"
echo "╚════════════════════════════════════════════════╝"
echo ""
