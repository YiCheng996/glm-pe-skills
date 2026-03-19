#!/usr/bin/env python3
"""
GLM-4V 图像理解能力批量测试工具
独立脚本，无 Gradio 依赖，可被 agent 直接通过 Shell 调用。

用法示例：
    python image_tester.py --folder /path/to/images --prompt "描述图片内容"
    python image_tester.py --folder /path/to/images --prompt "识别图中物体" --model glm-4.5v --count 5

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


_REFERENCE_MODELS = {
    "vision": {
        "desc": "图像理解模型",
        "models": [
            ("glm-4.7v",               "旗舰视觉版"),
            ("glm-4.6v",               "旗舰视觉版"),
            ("glm-4.5v",               "旗舰视觉版"),
            ("glm-4.1v-thinking-flash", "推理视觉版"),
            ("glm-4v-plus",            "上一代增强"),
            ("glm-4v-flash",           "上一代免费版"),
            ("glm-4v",                 "上一代标准版"),
            ("glm-edge-v-nano",        "端侧轻量版"),
        ]
    }
}


def list_models(api_key: str, category: str = "vision") -> None:
    """实时查询账号可用模型，并展示本 skill 的参考模型列表"""
    import urllib.request as _req
    print("=" * 55)
    print("账号实时可用模型（来自 API）：")
    try:
        r = _req.Request("https://open.bigmodel.cn/api/paas/v4/models",
                         headers={"Authorization": f"Bearer {api_key}"})
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


def scan_image_files(folder_path: str) -> list:
    extensions = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
    results = []
    if not folder_path or not os.path.isdir(folder_path):
        return results
    for root, dirs, files in os.walk(folder_path):
        dirs.sort()
        for fname in sorted(files):
            if fname.lower().endswith(extensions):
                results.append(os.path.join(root, fname))
    return results


def call_image_api(
    image_path: str,
    prompt: str,
    model: str,
    api_key: str,
    system: str = "",
    temperature: float = 0.1,
    top_p: float = 0.8,
    max_tokens: int = 2048,
    thinking_mode: str = "disabled",
) -> dict:
    try:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        return {"success": False, "error": "读取图片失败: {}".format(str(e)),
                "content": "", "request_id": "", "elapsed_ms": 0,
                "prompt_tokens": 0, "completion_tokens": 0, "reasoning_content": ""}

    client = ZhipuAI(api_key=api_key)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": img_b64}},
            {"type": "text", "text": prompt},
        ],
    })

    thinking_param = None
    if any(model.startswith(p) for p in ["glm-4.5v", "glm-4.6v", "glm-4.7v"]):
        thinking_param = {"type": thinking_mode}

    kwargs = dict(
        model=model,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
    )
    if thinking_param:
        kwargs["thinking"] = thinking_param

    t0 = time.time()
    try:
        completion = client.chat.completions.create(**kwargs)
    except APIStatusError as e:
        elapsed = int((time.time() - t0) * 1000)
        err = e.response.json().get("error", {}).get("message", str(e))
        return {"success": False, "error": err, "content": "", "request_id": "",
                "elapsed_ms": elapsed, "prompt_tokens": 0, "completion_tokens": 0,
                "reasoning_content": ""}
    except Exception as e:
        elapsed = int((time.time() - t0) * 1000)
        return {"success": False, "error": str(e), "content": "", "request_id": "",
                "elapsed_ms": elapsed, "prompt_tokens": 0, "completion_tokens": 0,
                "reasoning_content": ""}

    elapsed = int((time.time() - t0) * 1000)
    choice = completion.choices[0]
    if choice.finish_reason in ("stop", "length"):
        content = choice.message.content or ""
    else:
        content = str(choice.message)
    reasoning_content = getattr(choice.message, "reasoning_content", "") or ""
    usage = getattr(completion, "usage", None)
    return {
        "success": True,
        "content": content,
        "request_id": getattr(completion, "request_id", ""),
        "elapsed_ms": elapsed,
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
        "reasoning_content": reasoning_content,
    }


def save_xlsx(rows: list, output_path: str):
    wb = Workbook()
    ws = wb.active
    ws.title = "图像理解测评结果"
    headers = [
        "序号", "文件名", "路径", "模型", "提示词",
        "成功", "模型输出", "request_id", "耗时ms",
        "prompt_tokens", "completion_tokens", "思考内容", "错误信息",
    ]
    ws.append(headers)
    for row in rows:
        ws.append(row)
    for col in ws.columns:
        max_len = max((len(str(cell.value or "")) for cell in col), default=0)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 60)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    wb.save(output_path)


def run_test(
    folder_path: str,
    prompt: str,
    model: str,
    api_key: str,
    system: str = "",
    count: int = -1,
    output_dir: str = "./output",
    temperature: float = 0.1,
    top_p: float = 0.8,
    max_tokens: int = 2048,
    thinking_mode: str = "disabled",
    verbose: bool = True,
    concurrency: int = 3,
) -> dict:
    images = scan_image_files(folder_path)
    if not images:
        return {"success": False, "error": "目录下未找到图片文件: {}".format(folder_path),
                "results": [], "xlsx_path": ""}

    if count > 0:
        images = images[:count]

    total = len(images)
    now = datetime.datetime.now().strftime("%m-%d_%H-%M-%S")
    day = datetime.datetime.now().strftime("%m-%d")
    xlsx_path = os.path.join(output_dir, day,
                             "图像理解测评_{}_{}张_{}.xlsx".format(
                                 model.replace("/", "-"), total, now))

    results = [None] * total
    rows = [None] * total
    lock = threading.Lock()
    completed_count = [0]

    def process_one(idx: int, ipath: str):
        fname = os.path.basename(ipath)
        if verbose:
            with lock:
                print("[开始 {}/{}] {}".format(idx, total, fname), flush=True)

        res = call_image_api(
            ipath, prompt, model, api_key,
            system=system,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            thinking_mode=thinking_mode,
        )

        result_item = {
            "index": idx,
            "filename": fname,
            "path": ipath,
            "success": res["success"],
            "content": res.get("content", ""),
            "elapsed_ms": res.get("elapsed_ms", 0),
            "error": res.get("error", ""),
        }
        row = [
            idx, fname, ipath, model, prompt,
            "✓" if res["success"] else "✗",
            res.get("content", ""),
            res.get("request_id", ""),
            res.get("elapsed_ms", 0),
            res.get("prompt_tokens", 0),
            res.get("completion_tokens", 0),
            res.get("reasoning_content", ""),
            res.get("error", ""),
        ]

        with lock:
            results[idx - 1] = result_item
            rows[idx - 1] = row
            completed_count[0] += 1
            save_xlsx([r for r in rows if r is not None], xlsx_path)
            if verbose:
                status = "✓" if res["success"] else "✗ " + res.get("error", "")
                print("[完成 {}/{}] {} {} 耗时: {}ms".format(
                    completed_count[0], total, status, fname,
                    res.get("elapsed_ms", 0)), flush=True)

        return result_item

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(process_one, idx, ipath): idx
            for idx, ipath in enumerate(images, start=1)
        }
        for future in as_completed(futures):
            future.result()

    final_results = [r for r in results if r is not None]
    success_count = sum(1 for r in final_results if r["success"])
    return {
        "success": True,
        "total": total,
        "success_count": success_count,
        "fail_count": total - success_count,
        "model": model,
        "prompt": prompt,
        "xlsx_path": xlsx_path,
        "results": final_results,
    }


def main():
    parser = argparse.ArgumentParser(
        description="GLM-4V 图像理解能力批量测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python image_tester.py --folder /path/to/images --prompt "描述图片内容"
  python image_tester.py --folder /path/to/images --prompt "识别物体" --model glm-4.5v --count 5 --concurrency 3
        """,
    )
    parser.add_argument("--folder", required=True, help="图片文件夹路径（递归扫描）")
    parser.add_argument("--prompt", required=True, help="发送给模型的提问")
    parser.add_argument("--model", default="glm-4.5v",
                        help="图像理解模型（默认: glm-4.5v）。运行 --list-models 查看当前可用模型列表")
    parser.add_argument("--system", default="", help="system prompt（可选）")
    parser.add_argument("--thinking-mode", default="disabled",
                        choices=["disabled", "enabled"],
                        help="思考模式（默认: disabled）")
    parser.add_argument("--temperature", type=float, default=0.1, help="温度（默认: 0.1）")
    parser.add_argument("--top-p", type=float, default=0.8, help="Top-P（默认: 0.8）")
    parser.add_argument("--max-tokens", type=int, default=2048, help="最大输出 Token（默认: 2048）")
    parser.add_argument("--count", type=int, default=-1, help="测试数量上限，-1 为全部")
    parser.add_argument("--concurrency", type=int, default=3, help="并发数（默认: 3）")
    parser.add_argument("--output", default="./output", help="输出目录（默认: ./output）")
    parser.add_argument("--api-key", default="", help="API Key（可用 ZHIPUAI_API_KEY）")
    parser.add_argument("--json-only", action="store_true", help="只输出 JSON")
    parser.add_argument("--list-models", action="store_true", help="列出账号当前可用模型，然后退出")

    args = parser.parse_args()

    api_key = resolve_api_key(args.api_key)
    if not api_key:
        error = {"success": False,
                 "error": "未找到 API Key，请通过 --api-key 或环境变量 ZHIPUAI_API_KEY 提供"}
        print(json.dumps(error, ensure_ascii=False))
        sys.exit(1)

    if args.list_models:
        list_models(api_key, category="vision")
        sys.exit(0)

    verbose = not args.json_only

    if verbose:
        print("=" * 60)
        print("GLM 图像理解测评")
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
        system=args.system,
        count=args.count,
        output_dir=args.output,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
        thinking_mode=args.thinking_mode,
        verbose=verbose,
        concurrency=args.concurrency,
    )

    if verbose and summary.get("success"):
        print("=" * 60)
        print("测评完成！成功: {}/{}, 结果文件: {}".format(
            summary["success_count"], summary["total"], summary["xlsx_path"]))

    for r in summary.get("results", []):
        if len(r.get("content", "")) > 200:
            r["content_preview"] = r["content"][:200] + "..."

    print("\n--- JSON_RESULT_START ---")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("--- JSON_RESULT_END ---")


if __name__ == "__main__":
    main()
