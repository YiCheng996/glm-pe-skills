#!/usr/bin/env python3
import argparse
import base64
import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import pandas as pd
from openpyxl import Workbook
from zhipuai import ZhipuAI


_REFERENCE_MODELS = {
    "image_generation": [
        ("glm-image",       "最新文生图，0.1元/次"),
        ("cogview-4",       "CogView 新旗舰，0.06元/次"),
        ("cogview-3-flash", "免费版"),
        ("cogview-3-plus",  "上一代旗舰（历史版本）"),
        ("cogview-3",       "上一代标准版（历史版本）"),
    ],
    "video_generation": [
        ("cogvideox-3",      "最新视频生成，1元/次"),
        ("cogvideox-2",      "标准版，0.5元/次"),
        ("cogvideox-flash",  "免费版"),
        ("viduq1-text",      "Vidu Q1 文生视频，1080p，2.5元/次"),
        ("viduq1-image",     "Vidu Q1 图生视频，1080p，2.5元/次"),
        ("viduq1-start-end", "Vidu Q1 首尾帧，1080p，2.5元/次"),
        ("vidu2-image",      "Vidu 2 图生视频，720p，1.25元/次"),
        ("vidu2-start-end",  "Vidu 2 首尾帧，720p，1.25元/次"),
        ("vidu2-reference",  "Vidu 2 参考生视频，720p，2.5元/次"),
    ]
}


def list_models(api_key: str, category: str = "image_generation") -> None:
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
    for cat_key, models in _REFERENCE_MODELS.items():
        label = "文生图参考模型" if cat_key == "image_generation" else "视频生成参考模型"
        print(f"\n{label}（以官网为准）：")
        for mid, note in models:
            print(f"  {mid:<30} {note}")
    print(f"\n  完整模型列表：https://open.bigmodel.cn/dev/api")
    print("=" * 55)


def get_api_key(cli_key: str) -> str:
    """按优先级解析 API Key：CLI 参数 > ZHIPUAI_API_KEY > ZHIPUAI_API_KEY_PATH"""
    if cli_key:
        return cli_key
    key = os.environ.get("ZHIPUAI_API_KEY", "")
    if key:
        return key
    key_path = os.environ.get("ZHIPUAI_API_KEY_PATH", "")
    if key_path and os.path.isfile(key_path):
        with open(key_path) as f:
            return f.read().strip()
    return ""


def download_file(url, save_path):
    urllib.request.urlretrieve(url, save_path)


def call_t2i_api(prompt, model, api_key):
    client = ZhipuAI(api_key=api_key)
    response = client.images.generations(model=model, prompt=prompt)
    return response.data[0].url


def call_i2v_api(image_path, prompt, model, api_key):
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
    client = ZhipuAI(api_key=api_key)
    response = client.videos.generations(
        model=model,
        image_url=img_b64,
        prompt=prompt if prompt else None,
    )
    return _poll_video_task(client, response.id, response.task_status)


def call_t2v_api(prompt, model, api_key):
    client = ZhipuAI(api_key=api_key)
    response = client.videos.generations(model=model, prompt=prompt)
    return _poll_video_task(client, response.id, response.task_status)


def _poll_video_task(client, task_id, task_status, max_wait=60, interval=10):
    cnt = 0
    while task_status == "PROCESSING" and cnt < max_wait:
        time.sleep(interval)
        result = client.videos.retrieve_videos_result(id=task_id)
        task_status = result.task_status
        cnt += 1
    if task_status == "SUCCESS":
        return result.video_result[0].url
    raise RuntimeError(f"视频生成失败，状态：{task_status}")


def _process_t2i_single(prompt, model, output_dir, api_key, index):
    start = time.perf_counter()
    try:
        url = call_t2i_api(prompt, model, api_key)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = ".png" if "png" in url.lower() else ".jpg"
        fname = f"{index}_{ts}{ext}"
        save_path = os.path.join(output_dir, fname)
        download_file(url, save_path)
        elapsed = int((time.perf_counter() - start) * 1000)
        return {"index": index, "prompt": prompt, "url": url, "path": save_path, "elapsed_ms": elapsed, "success": True}
    except Exception as e:
        elapsed = int((time.perf_counter() - start) * 1000)
        return {"index": index, "prompt": prompt, "url": None, "path": None, "elapsed_ms": elapsed, "success": False, "error": str(e)}


def cmd_t2i(args):
    api_key = get_api_key(args.api_key)
    if not api_key:
        raise SystemExit("需要 --api-key 或环境变量 ZHIPUAI_API_KEY")
    os.makedirs(args.output_dir, exist_ok=True)

    if args.file:
        df = pd.read_excel(args.file) if args.file.endswith((".xlsx", ".xls")) else pd.read_csv(args.file)
        col = args.col if args.col in df.columns else df.columns[0]
        prompts = df[col].astype(str).tolist()
    else:
        if not args.prompt:
            raise SystemExit("需要 --prompt 或 --file")
        prompts = [args.prompt] * (args.count or 1)

    model = args.model or "cogview-3-plus"
    concurrency = getattr(args, "concurrency", 3) or 3
    results = []

    if len(prompts) > 1:
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            futures = {ex.submit(_process_t2i_single, p, model, args.output_dir, api_key, i + 1): i for i, p in enumerate(prompts)}
            for f in as_completed(futures):
                results.append(f.result())
        results.sort(key=lambda x: x["index"])
        wb = Workbook()
        ws = wb.active
        ws.append(["序号", "prompt", "图片URL", "本地保存路径", "耗时ms", "成功/失败"])
        for r in results:
            ws.append([r["index"], r["prompt"], r.get("url", ""), r.get("path", ""), r["elapsed_ms"], "成功" if r["success"] else "失败"])
        out_xlsx = os.path.join(args.output_dir, f"t2i_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        wb.save(out_xlsx)
        if not args.json_only:
            print(f"批量结果已保存: {out_xlsx}")
    else:
        r = _process_t2i_single(prompts[0], model, args.output_dir, api_key, 1)
        results = [r]
        if not args.json_only:
            print(f"URL: {r.get('url')}\n保存: {r.get('path')}")

    _emit_json({"mode": "t2i", "results": results})


def cmd_i2v(args):
    if not args.image or not os.path.isfile(args.image):
        raise SystemExit("需要有效的 --image 路径")
    api_key = get_api_key(args.api_key)
    if not api_key:
        raise SystemExit("需要 --api-key 或环境变量 ZHIPUAI_API_KEY")
    os.makedirs(args.output_dir, exist_ok=True)

    model = args.model or "cogvideox-flash"
    url = call_i2v_api(args.image, args.prompt, model, api_key)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = os.path.join(args.output_dir, f"i2v_{ts}.mp4")
    download_file(url, save_path)

    if not args.json_only:
        print(f"URL: {url}\n保存: {save_path}")
    _emit_json({"mode": "i2v", "url": url, "path": save_path})


def cmd_t2v(args):
    if not args.prompt:
        raise SystemExit("需要 --prompt")
    api_key = get_api_key(args.api_key)
    if not api_key:
        raise SystemExit("需要 --api-key 或环境变量 ZHIPUAI_API_KEY")
    os.makedirs(args.output_dir, exist_ok=True)

    model = args.model or "cogvideox-flash"
    url = call_t2v_api(args.prompt, model, api_key)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = os.path.join(args.output_dir, f"t2v_{ts}.mp4")
    download_file(url, save_path)

    if not args.json_only:
        print(f"URL: {url}\n保存: {save_path}")
    _emit_json({"mode": "t2v", "url": url, "path": save_path})


def _emit_json(obj):
    print("--- JSON_RESULT_START ---")
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    print("--- JSON_RESULT_END ---")


def main():
    import sys as _sys

    # 提前检测 --list-models，绕过子命令 required 限制
    _pre = argparse.ArgumentParser(add_help=False)
    _pre.add_argument("--api-key", default="")
    _pre.add_argument("--list-models", action="store_true")
    _known, _ = _pre.parse_known_args()
    if _known.list_models:
        api_key = get_api_key(_known.api_key)
        if not api_key:
            raise SystemExit("需要 --api-key 或环境变量 ZHIPUAI_API_KEY")
        list_models(api_key)
        _sys.exit(0)

    # 公共参数放 parent parser，所有子命令自动继承
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--api-key", default="", help="智谱 API Key（可用 ZHIPUAI_API_KEY 环境变量）")
    common.add_argument("--json-only", action="store_true", help="仅输出 JSON，不打印进度")
    common.add_argument("--list-models", action="store_true", help="列出账号当前可用模型，然后退出")

    parser = argparse.ArgumentParser(description="GLM 内容生成 CLI", parents=[common])
    sub = parser.add_subparsers(dest="cmd", required=True)

    t2i = sub.add_parser("t2i", help="文生图（CogView / GLM-Image）", parents=[common])
    t2i.add_argument("--prompt", help="图片描述提示词")
    t2i.add_argument("--model", default="cogview-4", help="文生图模型（默认: cogview-4）。运行 --list-models 查看当前可用模型")
    t2i.add_argument("--count", type=int, default=1)
    t2i.add_argument("--file", help="Excel/CSV 批量文件")
    t2i.add_argument("--col", default=None, help="批量时列名，默认第一列")
    t2i.add_argument("--output-dir", default="./output/images")
    t2i.add_argument("--concurrency", type=int, default=3)
    t2i.set_defaults(func=cmd_t2i)

    i2v = sub.add_parser("i2v", help="图生视频（CogVideoX / Vidu）", parents=[common])
    i2v.add_argument("--image", required=True, help="本地图片路径")
    i2v.add_argument("--prompt", default="", help="视频描述（可选）")
    i2v.add_argument("--model", default="cogvideox-flash")
    i2v.add_argument("--output-dir", default="./output/videos")
    i2v.set_defaults(func=cmd_i2v)

    t2v = sub.add_parser("t2v", help="文生视频（CogVideoX / Vidu）", parents=[common])
    t2v.add_argument("--prompt", required=True, help="视频描述提示词")
    t2v.add_argument("--model", default="cogvideox-flash")
    t2v.add_argument("--output-dir", default="./output/videos")
    t2v.set_defaults(func=cmd_t2v)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
