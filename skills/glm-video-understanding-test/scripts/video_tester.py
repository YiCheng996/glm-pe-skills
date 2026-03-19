#!/usr/bin/env python3
"""
GLM-4.6V 视频理解能力批量测试工具
独立脚本，无 Gradio 依赖，可被 agent 直接通过 Shell 调用。

用法示例：
    python video_tester.py --folder /path/to/videos --prompt "描述视频内容"
    python video_tester.py --folder /path/to/videos --prompt "描述操作步骤" --model glm-4.6v --count 5
    python video_tester.py --folder /path/to/videos --prompt "分析施工流程" --output ./results

依赖安装：
    pip install zhipuai openpyxl

API Key 配置（优先级由高到低）：
    1. 命令行参数 --api-key
    2. 环境变量 ZHIPUAI_API_KEY
    3. 环境变量 ZHIPUAI_API_KEY_PATH（指向含 key 的文本文件路径）
"""

import argparse
import base64
import datetime
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── 依赖检查 ──────────────────────────────────────────────────────────────────
try:
    from zhipuai import ZhipuAI, APIStatusError
except ImportError:
    print(json.dumps({"error": "缺少依赖: pip install zhipuai"}), flush=True)
    sys.exit(1)

try:
    from openpyxl import Workbook
except ImportError:
    print(json.dumps({"error": "缺少依赖: pip install openpyxl"}), flush=True)
    sys.exit(1)


# ── 工具函数 ──────────────────────────────────────────────────────────────────

# 参考模型列表（内嵌，随 skill 版本更新；运行时通过 API 实时补充）
_REFERENCE_MODELS = {
    "video_understanding": {
        "desc": "视频理解模型（均属视觉模型，支持图片+视频输入）",
        "models": [
            ("glm-4.6v",                 "旗舰版，128K，精度最高"),
            ("glm-4.6v-flashx",          "轻量高速版，128K，日常首选"),
            ("glm-4.6v-flash",           "免费版"),
            ("glm-4.5v",                 "上一代旗舰，64K"),
            ("glm-4.1v-thinking-flash",  "视觉推理版，64K，免费"),
        ]
    }
}


def list_models(api_key: str, category: str = "video_understanding") -> None:
    """实时查询账号可用模型，并展示本 skill 的参考模型列表"""
    import urllib.request as _req

    print("=" * 55)
    print("账号实时可用模型（来自 API）：")
    try:
        r = _req.Request(
            "https://open.bigmodel.cn/api/paas/v4/models",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        with _req.urlopen(r, timeout=8) as resp:
            data = json.loads(resp.read())
        ids = [m["id"] for m in data.get("data", [])]
        for mid in ids:
            print(f"  {mid}")
        if not ids:
            print("  （无数据，请检查 API Key）")
    except Exception as e:
        print(f"  ⚠ API 查询失败：{e}")

    cat = _REFERENCE_MODELS.get(category, {})
    if cat:
        print(f"\n本 skill 参考模型（{cat['desc']}，以官网为准）：")
        for mid, note in cat["models"]:
            print(f"  {mid:<30} {note}")
    print(f"\n  完整模型列表：https://open.bigmodel.cn/dev/api")
    print("=" * 55)


def resolve_api_key(cli_key: str) -> str:
    """
    按优先级获取 API Key：
    CLI 参数 > 环境变量 ZHIPUAI_API_KEY > 文件路径环境变量 ZHIPUAI_API_KEY_PATH
    """
    if cli_key:
        return cli_key
    key = os.environ.get("ZHIPUAI_API_KEY", "")
    if key:
        return key
    key_path = os.environ.get("ZHIPUAI_API_KEY_PATH", "")
    if key_path and os.path.isfile(key_path):
        with open(key_path, "r") as f:
            return f.read().strip()
    return ""


def scan_video_files(folder_path: str) -> list:
    """
    递归扫描目录，返回按路径排序的视频文件列表。
    支持格式：mp4 / mov / avi / mkv / webm
    """
    extensions = (".mp4", ".mov", ".avi", ".mkv", ".webm")
    results = []
    if not folder_path or not os.path.isdir(folder_path):
        return results
    for root, dirs, files in os.walk(folder_path):
        dirs.sort()
        for fname in sorted(files):
            if fname.lower().endswith(extensions):
                results.append(os.path.join(root, fname))
    return results


def call_video_api(
    video_path: str,
    prompt: str,
    model: str,
    api_key: str,
    temperature: float = 0.1,
    top_p: float = 0.8,
    max_tokens: int = 2048,
) -> dict:
    """
    调用 GLM-4.6V 视频理解 API，返回结构化结果 dict。

    返回字段：
        success      - bool
        content      - 模型输出文本
        request_id   - 请求 ID
        elapsed_ms   - 总耗时（毫秒）
        prompt_tokens
        completion_tokens
        reasoning    - 思考链内容（如模型支持）
        error        - 错误信息（仅失败时存在）
    """
    try:
        with open(video_path, "rb") as f:
            video_b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        return {"success": False, "error": "读取视频文件失败: {}".format(str(e)),
                "content": "", "request_id": "", "elapsed_ms": 0,
                "prompt_tokens": 0, "completion_tokens": 0, "reasoning": ""}

    client = ZhipuAI(api_key=api_key)
    t0 = time.time()

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "video_url", "video_url": {"url": video_b64}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            thinking={"type": "disabled"},  # 默认关闭思考链，加快速度
        )
    except APIStatusError as e:
        elapsed = int((time.time() - t0) * 1000)
        err = e.response.json().get("error", {}).get("message", str(e))
        return {"success": False, "error": err, "content": "", "request_id": "",
                "elapsed_ms": elapsed, "prompt_tokens": 0, "completion_tokens": 0,
                "reasoning": ""}
    except Exception as e:
        elapsed = int((time.time() - t0) * 1000)
        return {"success": False, "error": str(e), "content": "", "request_id": "",
                "elapsed_ms": elapsed, "prompt_tokens": 0, "completion_tokens": 0,
                "reasoning": ""}

    elapsed = int((time.time() - t0) * 1000)
    choice = completion.choices[0]

    if choice.finish_reason in ("stop", "length"):
        content = choice.message.content or ""
    else:
        content = str(choice.message)

    reasoning = ""
    if hasattr(choice.message, "reasoning_content"):
        reasoning = choice.message.reasoning_content or ""

    usage = getattr(completion, "usage", None)
    return {
        "success": True,
        "content": content,
        "request_id": getattr(completion, "request_id", ""),
        "elapsed_ms": elapsed,
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
        "reasoning": reasoning,
    }


def save_xlsx(rows: list, output_path: str):
    """将结果列表保存为 xlsx 文件"""
    wb = Workbook()
    ws = wb.active
    ws.title = "视频理解测评结果"
    headers = [
        "序号", "视频文件名", "视频路径", "模型", "提示词",
        "成功", "模型输出", "request_id", "耗时ms",
        "prompt_tokens", "completion_tokens", "思考内容", "错误信息",
    ]
    ws.append(headers)
    for row in rows:
        ws.append(row)
    # 自动调整列宽（最大 60 字符）
    for col in ws.columns:
        max_len = max((len(str(cell.value or "")) for cell in col), default=0)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 60)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    wb.save(output_path)


# ── 主测试流程 ─────────────────────────────────────────────────────────────────

def run_test(
    folder_path: str,
    prompt: str,
    model: str,
    api_key: str,
    count: int = -1,
    output_dir: str = "./output",
    temperature: float = 0.1,
    top_p: float = 0.8,
    max_tokens: int = 2048,
    verbose: bool = True,
    concurrency: int = 1,
) -> dict:
    """
    核心测试流程，支持并发调用。
    返回 summary dict，包含 results 列表和 xlsx_path。

    每条 result 包含：
        index, filename, path, success, content, elapsed_ms, error
    """
    videos = scan_video_files(folder_path)
    if not videos:
        return {"success": False, "error": "目录下未找到视频文件: {}".format(folder_path),
                "results": [], "xlsx_path": ""}

    # 按 count 截取
    if count > 0:
        videos = videos[:count]

    total = len(videos)
    now = datetime.datetime.now().strftime("%m-%d_%H-%M-%S")
    day = datetime.datetime.now().strftime("%m-%d")
    xlsx_path = os.path.join(output_dir, day,
                             "视频理解测评_{}_{}个_{}.xlsx".format(
                                 model.replace("/", "-"), total, now))

    # 预分配按原始顺序存储结果，并发时保证 xlsx 顺序一致
    results = [None] * total
    rows = [None] * total

    lock = threading.Lock()           # 保护共享计数器、打印、xlsx 写入
    completed_count = [0]             # 用列表包装方便闭包修改

    def process_one(idx: int, vpath: str):
        """单个视频的完整处理流程（在线程池中执行）"""
        fname = os.path.basename(vpath)
        if verbose:
            with lock:
                print("[开始 {}/{}] {}".format(idx, total, fname), flush=True)

        res = call_video_api(vpath, prompt, model, api_key,
                             temperature=temperature, top_p=top_p,
                             max_tokens=max_tokens)

        result_item = {
            "index": idx,
            "filename": fname,
            "path": vpath,
            "success": res["success"],
            "content": res.get("content", ""),
            "elapsed_ms": res.get("elapsed_ms", 0),
            "error": res.get("error", ""),
        }
        row = [
            idx, fname, vpath, model, prompt,
            "✓" if res["success"] else "✗",
            res.get("content", ""),
            res.get("request_id", ""),
            res.get("elapsed_ms", 0),
            res.get("prompt_tokens", 0),
            res.get("completion_tokens", 0),
            res.get("reasoning", ""),
            res.get("error", ""),
        ]

        with lock:
            results[idx - 1] = result_item
            rows[idx - 1] = row
            completed_count[0] += 1

            # 每完成一个立即保存，仅写入已完成的行（跳过 None）
            save_xlsx([r for r in rows if r is not None], xlsx_path)

            if verbose:
                status = "✓" if res["success"] else "✗ " + res.get("error", "")
                print("[完成 {}/{}] {} {} 耗时: {}ms".format(
                    completed_count[0], total, status, fname,
                    res.get("elapsed_ms", 0)), flush=True)

        return result_item

    # 并发执行：concurrency=1 时退化为顺序执行
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(process_one, idx, vpath): idx
            for idx, vpath in enumerate(videos, start=1)
        }
        for future in as_completed(futures):
            # 传播线程内异常到主线程
            future.result()

    # 过滤掉极少数情况下未完成的槽位
    final_results = [r for r in results if r is not None]
    success_count = sum(1 for r in final_results if r["success"])
    summary = {
        "success": True,
        "total": total,
        "success_count": success_count,
        "fail_count": total - success_count,
        "model": model,
        "prompt": prompt,
        "xlsx_path": xlsx_path,
        "results": final_results,
    }
    return summary


# ── CLI 入口 ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="GLM-4.6V 视频理解能力批量测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 测试目录下全部视频
  python video_tester.py --folder /path/to/videos --prompt "描述视频内容"

  # 只测试前 5 个，使用旗舰模型
  python video_tester.py --folder /path/to/videos --prompt "描述操作步骤" --model glm-4.6v --count 5

  # 指定输出目录和 API Key
  python video_tester.py --folder /path/to/videos --prompt "分析施工流程" \\
      --output ./my_results --api-key YOUR_KEY
        """,
    )
    parser.add_argument("--folder",   required=True,  help="视频文件夹路径（支持递归子目录）")
    parser.add_argument("--prompt",   required=True,  help="发送给模型的提示词")
    parser.add_argument("--model",    default="glm-4.6v-flashx",
                        help="视频理解模型（默认: glm-4.6v-flashx）。运行 --list-models 查看当前可用模型列表")
    parser.add_argument("--count",    type=int, default=-1,
                        help="测试视频数量，-1 表示全部（默认: -1）")
    parser.add_argument("--output",   default="./output", help="结果输出目录（默认: ./output）")
    parser.add_argument("--api-key",  default="",     help="智谱 AI API Key（可用环境变量代替）")
    parser.add_argument("--temperature", type=float, default=0.1, help="温度参数（默认: 0.1）")
    parser.add_argument("--top-p",    type=float, default=0.8,  help="Top-P 参数（默认: 0.8）")
    parser.add_argument("--max-tokens", type=int, default=2048, help="最大输出 Token 数（默认: 2048）")
    parser.add_argument("--concurrency", type=int, default=1,
                        help="并发请求数（默认: 1，即顺序执行；建议不超过 10）")
    parser.add_argument("--json-only", action="store_true",
                        help="只输出 JSON 结果，不打印进度（适合 agent 解析）")
    parser.add_argument("--list-models", action="store_true",
                        help="列出账号当前可用模型，然后退出")

    args = parser.parse_args()

    api_key = resolve_api_key(args.api_key)
    if not api_key:
        error = {"success": False,
                 "error": "未找到 API Key，请通过 --api-key 参数或环境变量 ZHIPUAI_API_KEY 提供"}
        print(json.dumps(error, ensure_ascii=False))
        sys.exit(1)

    if args.list_models:
        list_models(api_key, category="video_understanding")
        sys.exit(0)

    verbose = not args.json_only

    if verbose:
        print("=" * 60)
        print("GLM 视频理解测评")
        print("  文件夹: {}".format(args.folder))
        print("  模型  : {}".format(args.model))
        print("  提示词: {}".format(args.prompt[:80]))
        print("  数量  : {}".format("全部" if args.count == -1 else args.count))
        print("  并发数: {}".format(args.concurrency))
        print("=" * 60)

    summary = run_test(
        folder_path=args.folder,
        prompt=args.prompt,
        model=args.model,
        api_key=api_key,
        count=args.count,
        output_dir=args.output,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
        verbose=verbose,
        concurrency=args.concurrency,
    )

    if verbose and summary.get("success"):
        print("=" * 60)
        print("测评完成！成功: {}/{}, 结果文件: {}".format(
            summary["success_count"], summary["total"], summary["xlsx_path"]))

    # 最终输出 JSON（agent 可解析此行）
    # 为减少输出体积，results 中的 content 截断到 200 字符
    for r in summary.get("results", []):
        if len(r.get("content", "")) > 200:
            r["content_preview"] = r["content"][:200] + "..."
            r["content"] = r["content"]  # 完整内容保留在 xlsx，此处保持原样

    print("\n--- JSON_RESULT_START ---")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("--- JSON_RESULT_END ---")


if __name__ == "__main__":
    main()
