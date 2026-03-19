#!/usr/bin/env python3
"""
GLM 文本批量测试工具
支持文本批量与文件批量两种模式，无 Gradio 依赖。

用法示例：
    python text_tester.py --mode file --file prompts.xlsx --input-col 问题
    python text_tester.py --mode text --input prompts.txt --prompt-template "请分析：{input}"
"""

import argparse
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

try:
    import pandas as pd
except ImportError:
    print(json.dumps({"error": "缺少依赖: pip install pandas"}), flush=True)
    sys.exit(1)


_REFERENCE_MODELS = {
    "text": {
        "desc": "文本对话模型",
        "models": [
            ("glm-4.7",         "旗舰版"),
            ("glm-4.6",         "旗舰版"),
            ("glm-4.5",         "旗舰版"),
            ("glm-4.5-air",     "轻量版"),
            ("glm-4.5-airx",    "高速轻量版"),
            ("glm-4.5-flash",   "免费版"),
            ("glm-4.5-x",       "增强版"),
            ("glm-4-plus",      "上一代旗舰"),
            ("glm-4-flash",     "上一代免费版"),
            ("glm-4-long",      "超长上下文"),
            ("glm-zero-preview","推理模型预览版"),
        ]
    }
}


def list_models(api_key: str, category: str = "text") -> None:
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


def call_chat_api(
    prompt: str,
    model: str,
    api_key: str,
    system: str = "",
    temperature: float = 0.1,
    top_p: float = 0.8,
    max_tokens: int = 4096,
    thinking_mode: str = "disabled",
    messages_override: list = None,
) -> dict:
    client = ZhipuAI(api_key=api_key)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    if messages_override:
        messages.extend(messages_override)
    else:
        messages.append({"role": "user", "content": prompt})

    thinking_param = None
    if any(model.startswith(p) for p in ["glm-4.5", "glm-4.6", "glm-4.7"]):
        if not any(model.startswith(p) for p in ["glm-4.5v", "glm-4.6v", "glm-4.7v"]):
            thinking_param = {"type": thinking_mode}

    kwargs = dict(
        model=model,
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        stream=False,
    )
    if thinking_param:
        kwargs["thinking"] = thinking_param

    t0 = time.time()
    try:
        completion = client.chat.completions.create(**kwargs)
    except APIStatusError as e:
        elapsed = int((time.time() - t0) * 1000)
        err = e.response.json().get("error", {}).get("message", str(e))
        return {
            "success": False,
            "content": "",
            "request_id": "",
            "elapsed_ms": elapsed,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "reasoning": "",
            "error": err,
        }
    except Exception as e:
        elapsed = int((time.time() - t0) * 1000)
        return {
            "success": False,
            "content": "",
            "request_id": "",
            "elapsed_ms": elapsed,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "reasoning": "",
            "error": str(e),
        }

    elapsed = int((time.time() - t0) * 1000)
    choice = completion.choices[0]
    content = choice.message.content or ""
    reasoning = getattr(choice.message, "reasoning_content", "") or ""
    usage = getattr(completion, "usage", None)
    return {
        "success": True,
        "content": content,
        "request_id": getattr(completion, "request_id", ""),
        "elapsed_ms": elapsed,
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
        "reasoning": reasoning,
        "error": "",
    }


def load_text_prompts(input_path: str, prompt_template: str) -> list:
    if input_path == "-":
        content = sys.stdin.read()
    else:
        with open(input_path, "r", encoding="utf-8") as f:
            content = f.read()
    blocks = [b.strip() for b in content.split("***") if b.strip()]
    return [prompt_template.format(input=b) for b in blocks]


def load_file_prompts(
    file_path: str,
    sheet: str,
    prompt_template: str,
    input_col: str = None,
) -> list:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".xlsx" or ext == ".xls":
        if sheet:
            df = pd.read_excel(file_path, sheet_name=sheet)
        else:
            df = pd.read_excel(file_path, sheet_name=0)
    else:
        df = pd.read_csv(file_path, encoding="utf-8-sig")
    df = df.fillna("")
    prompts = []
    for _, row in df.iterrows():
        ctx = dict(row)
        if input_col:
            ctx["input"] = str(ctx.get(input_col, ""))
        try:
            p = prompt_template.format(**ctx)
        except KeyError as e:
            raise ValueError("模板变量 {} 在数据列中不存在，可用列: {}".format(e, list(df.columns)))
        prompts.append(p)
    return prompts


def save_xlsx(rows: list, output_path: str):
    wb = Workbook()
    ws = wb.active
    ws.title = "文本批量测评结果"
    headers = [
        "序号", "输入", "模型输出", "耗时ms", "request_id",
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
    prompts: list,
    model: str,
    api_key: str,
    system: str = "",
    temperature: float = 0.1,
    top_p: float = 0.8,
    max_tokens: int = 4096,
    thinking_mode: str = "disabled",
    count: int = -1,
    output_dir: str = "./output",
    verbose: bool = True,
    concurrency: int = 3,
) -> dict:
    if count > 0:
        prompts = prompts[:count]
    total = len(prompts)
    if total == 0:
        return {"success": False, "error": "无有效输入", "results": [], "xlsx_path": ""}

    now = datetime.datetime.now().strftime("%m-%d_%H-%M-%S")
    day = datetime.datetime.now().strftime("%m-%d")
    xlsx_path = os.path.join(
        output_dir, day,
        "文本批量测评_{}_{}条_{}.xlsx".format(model.replace("/", "-"), total, now),
    )

    results = [None] * total
    rows = [None] * total
    lock = threading.Lock()
    completed_count = [0]

    def process_one(idx: int, prompt: str):
        if verbose:
            with lock:
                print("[开始 {}/{}]".format(idx, total), flush=True)

        res = call_chat_api(
            prompt=prompt,
            model=model,
            api_key=api_key,
            system=system,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            thinking_mode=thinking_mode,
        )

        row = [
            idx,
            prompt,
            res.get("content", ""),
            res.get("elapsed_ms", 0),
            res.get("request_id", ""),
            res.get("prompt_tokens", 0),
            res.get("completion_tokens", 0),
            res.get("reasoning", ""),
            res.get("error", ""),
        ]

        with lock:
            results[idx - 1] = {
                "index": idx,
                "input": prompt,
                "success": res["success"],
                "content": res.get("content", ""),
                "elapsed_ms": res.get("elapsed_ms", 0),
                "error": res.get("error", ""),
            }
            rows[idx - 1] = row
            completed_count[0] += 1
            save_xlsx([r for r in rows if r is not None], xlsx_path)

            if verbose:
                status = "✓" if res["success"] else "✗ " + res.get("error", "")
                print("[完成 {}/{}] {} 耗时: {}ms".format(
                    completed_count[0], total, status, res.get("elapsed_ms", 0)), flush=True)

        return results[idx - 1]

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(process_one, idx, p): idx
            for idx, p in enumerate(prompts, start=1)
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
        "xlsx_path": xlsx_path,
        "results": final_results,
    }


def main():
    parser = argparse.ArgumentParser(
        description="GLM 文本批量测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--mode", default="file", choices=["text", "file"],
                        help="模式：text=文本批量，file=文件批量（默认）")
    parser.add_argument("--input", default="",
                        help="[text模式] 输入文件路径，每行为一 prompt，*** 分隔多轮；- 表示 stdin")
    parser.add_argument("--file", default="",
                        help="[file模式] Excel(.xlsx) 或 CSV 文件路径")
    parser.add_argument("--sheet", default="",
                        help="[file模式] Excel sheet 名，默认第一个")
    parser.add_argument("--prompt-template", default="{input}",
                        help="模板，支持 {input} 或 {列名} 变量替换")
    parser.add_argument("--input-col", default="",
                        help="[file模式] 单列快捷指定，等价于 --prompt-template \"{input_col}\"")
    parser.add_argument("--model", default="glm-4.5", help="模型名（默认 glm-4.5）")
    parser.add_argument("--system", default="", help="system prompt")
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--top-p", type=float, default=0.8)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--thinking-mode", default="disabled",
                        choices=["enabled", "disabled"])
    parser.add_argument("--count", type=int, default=-1, help="测试行数上限，-1 为全部")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--output", default="./output", help="输出目录")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--json-only", action="store_true", help="只输出 JSON，不打印进度")
    parser.add_argument("--list-models", action="store_true", help="列出账号当前可用模型，然后退出")

    args = parser.parse_args()

    api_key = resolve_api_key(args.api_key)
    if not api_key:
        err = {"success": False, "error": "未找到 API Key，请通过 --api-key 或环境变量 ZHIPUAI_API_KEY 提供"}
        print(json.dumps(err, ensure_ascii=False))
        sys.exit(1)

    if args.list_models:
        list_models(api_key, category="text")
        sys.exit(0)

    prompt_template = args.prompt_template
    if args.mode == "file" and args.input_col:
        prompt_template = "{" + args.input_col + "}"

    try:
        if args.mode == "text":
            if not args.input:
                raise ValueError("text 模式需指定 --input 文件路径或 -")
            prompts = load_text_prompts(args.input, prompt_template)
        else:
            if not args.file:
                raise ValueError("file 模式需指定 --file 路径")
            prompts = load_file_prompts(
                args.file,
                args.sheet if args.sheet else None,
                prompt_template,
                args.input_col if args.input_col else None,
            )
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
        sys.exit(1)

    verbose = not args.json_only
    if verbose:
        print("=" * 60)
        print("GLM 文本批量测评")
        print("  模式  : {}".format(args.mode))
        print("  模型  : {}".format(args.model))
        print("  数量  : {}".format("全部" if args.count == -1 else args.count))
        print("  并发数: {}".format(args.concurrency))
        print("=" * 60)

    summary = run_test(
        prompts=prompts,
        model=args.model,
        api_key=api_key,
        system=args.system,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
        thinking_mode=args.thinking_mode,
        count=args.count,
        output_dir=args.output,
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
