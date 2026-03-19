#!/usr/bin/env python3
import argparse
import json
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd
from openpyxl import Workbook
from zhipuai import ZhipuAI

BATCH_SIZE = 25

_REFERENCE_MODELS = {
    "embedding": {
        "desc": "向量化模型",
        "models": [
            ("embedding-3", "最新版，2048维，推荐"),
            ("embedding-2", "上一代，1024维"),
        ]
    }
}


def list_models(api_key: str, category: str = "embedding") -> None:
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


def call_embedding_api(texts, model, api_key):
    client = ZhipuAI(api_key=api_key)
    all_embeddings = []
    total_tokens = 0
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        response = client.embeddings.create(model=model, input=batch)
        all_embeddings.extend([item.embedding for item in response.data])
        if hasattr(response, "usage") and response.usage:
            total_tokens += getattr(response.usage, "total_tokens", 0) or 0
    return all_embeddings, total_tokens


def cosine_similarity_matrix(embeddings):
    arr = np.array(embeddings)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    normed = arr / (norms + 1e-10)
    return (normed @ normed.T).tolist()


def cosine_similarity_pair(emb1, emb2):
    a, b = np.array(emb1), np.array(emb2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))


def truncate(s, max_len=100):
    s = str(s).strip()
    return s[:max_len] + "…" if len(s) > max_len else s


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["texts", "file"], default="file")
    parser.add_argument("--texts", type=str, help="Multi-line text, each line or *** separated")
    parser.add_argument("--file", type=str, help="Excel(.xlsx) or CSV path")
    parser.add_argument("--col", type=str, default=None, help="Column name (default: first col)")
    parser.add_argument("--col2", type=str, default=None, help="Second column for row-wise similarity")
    parser.add_argument("--sheet", type=str, default=None, help="Excel sheet name")
    parser.add_argument("--model", type=str, default="embedding-3")
    parser.add_argument("--count", type=int, default=-1)
    parser.add_argument("--output", type=str, default="./output")
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument("--json-only", action="store_true")
    parser.add_argument("--list-models", action="store_true", help="列出账号当前可用模型，然后退出")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("ZHIPUAI_API_KEY")
    if not api_key:
        print("Error: API key required (--api-key or ZHIPUAI_API_KEY)", file=sys.stderr)
        sys.exit(1)

    if args.list_models:
        list_models(api_key, category="embedding")
        sys.exit(0)

    texts2 = None
    if args.mode == "texts":
        raw = args.texts or ""
        texts = [t.strip() for t in raw.replace("***", "\n").split("\n") if t.strip()]
    else:
        if not args.file or not os.path.isfile(args.file):
            print("Error: --file required and must exist", file=sys.stderr)
            sys.exit(1)
        ext = os.path.splitext(args.file)[1].lower()
        if ext == ".csv":
            df = pd.read_csv(args.file)
        else:
            df = pd.read_excel(args.file, sheet_name=args.sheet or 0)
        col = args.col or df.columns[0]
        texts = df[col].astype(str).tolist()
        texts2 = df[args.col2].astype(str).tolist() if args.col2 and args.col2 in df.columns else None

    if args.count > 0:
        texts = texts[: args.count]
        if texts2 is not None:
            texts2 = texts2[: args.count]

    if not texts:
        print("Error: no texts to process", file=sys.stderr)
        sys.exit(1)

    embeddings, total_tokens = call_embedding_api(texts, args.model, api_key)
    dims = [len(e) for e in embeddings]
    norms = [float(np.linalg.norm(np.array(e))) for e in embeddings]
    avg_dim = sum(dims) / len(dims)
    avg_norm = sum(norms) / len(norms)

    if texts2 is not None:
        emb2, tok2 = call_embedding_api(texts2, args.model, api_key)
        total_tokens += tok2
        sim_matrix = [[cosine_similarity_pair(embeddings[i], emb2[i])] for i in range(len(texts))]
    else:
        sim_matrix = cosine_similarity_matrix(embeddings)

    os.makedirs(args.output, exist_ok=True)
    ts = datetime.now().strftime("%m-%d_%H-%M-%S")
    xlsx_name = f"Embedding评测_{args.model}_{len(texts)}条_{ts}.xlsx"
    xlsx_path = os.path.join(args.output, xlsx_name)

    wb = Workbook()
    ws1 = wb.active
    ws1.title = "向量结果"
    ws1.append(["序号", "原文", "向量维度", "向量范数", "prompt_tokens"])
    for i, (t, d, n) in enumerate(zip(texts, dims, norms), 1):
        ws1.append([i, truncate(t), d, round(n, 4), total_tokens if i == 1 else ""])
    ws2 = wb.create_sheet("相似度矩阵")
    if texts2 is not None:
        ws2.append(["序号", "相似度"])
        for i, row in enumerate(sim_matrix, 1):
            ws2.append([i, round(row[0], 6)])
    else:
        for i, row in enumerate(sim_matrix):
            ws2.append([round(x, 6) for x in row])
    wb.save(xlsx_path)

    sim_trunc = sim_matrix
    if isinstance(sim_matrix, list) and len(sim_matrix) > 20:
        sim_trunc = [row[:20] for row in sim_matrix[:20]]

    result = {
        "model": args.model,
        "total": len(texts),
        "avg_dim": round(avg_dim, 2),
        "avg_norm": round(avg_norm, 4),
        "similarity_matrix": sim_trunc,
        "xlsx_path": xlsx_path,
    }
    if not args.json_only:
        print(f"Done: {xlsx_path}")
    print("--- JSON_RESULT_START ---")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("--- JSON_RESULT_END ---")


if __name__ == "__main__":
    main()
