#!/usr/bin/env python3
"""
EC3D-Bridge CLI: 拡張機能を使わずにバックエンドを操作する。

使い方:
    ec3d submit <product.json>           # JSON ファイルから 1 件投入
    ec3d submit --bulk <urls.txt>        # 行区切り URL ファイルから一括投入
                                           ※ 各 URL に対する商品情報は事前に手動で
                                           収集する前提。拡張機能経由の方が楽。
    ec3d status <job_id>                 # 状態を 1 回確認
    ec3d watch <job_id>                  # 終端まで毎秒ポーリング
    ec3d jobs [--limit 20]               # 直近ジョブ一覧
    ec3d cancel <job_id>                 # 実行中ジョブをキャンセル
    ec3d upload-homestyler <job_id>      # 成功済みジョブを Homestyler に流す

環境変数:
    EC3D_API_URL    バックエンド URL (default: http://localhost:3000)
    EC3D_API_KEY    認証ヘッダの値 (バックエンドで設定済みなら必須)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

API_BASE = os.environ.get("EC3D_API_URL", "http://localhost:3000")
API_KEY = os.environ.get("EC3D_API_KEY", "")


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    if API_KEY:
        h["X-API-Key"] = API_KEY
    return h


def cmd_submit(args) -> int:
    data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    r = httpx.post(f"{API_BASE}/api/process", headers=_headers(), json=data, timeout=10)
    if r.status_code != 202:
        print(f"ERROR: {r.status_code} {r.text}", file=sys.stderr)
        return 1
    body = r.json()
    print(body["job_id"])
    if args.wait:
        return _watch(body["job_id"])
    return 0


def cmd_status(args) -> int:
    r = httpx.get(f"{API_BASE}/api/status/{args.job_id}", headers=_headers(), timeout=10)
    if r.status_code != 200:
        print(f"ERROR: {r.status_code} {r.text}", file=sys.stderr)
        return 1
    print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    return 0


def _watch(job_id: str, interval: float = 1.0) -> int:
    last_msg = ""
    while True:
        r = httpx.get(f"{API_BASE}/api/status/{job_id}", headers=_headers(), timeout=10)
        if r.status_code != 200:
            print(f"ERROR: {r.status_code} {r.text}", file=sys.stderr)
            return 1
        body = r.json()
        msg = body["message"]
        if msg != last_msg:
            sys.stderr.write(f"[{body['step_index']}/{body['total_steps']}] {msg}\n")
            sys.stderr.flush()
            last_msg = msg
        if body["status"] in ("success", "error", "cancelled"):
            print(json.dumps(body, ensure_ascii=False, indent=2))
            return 0 if body["status"] == "success" else 1
        time.sleep(interval)


def cmd_watch(args) -> int:
    return _watch(args.job_id)


def cmd_jobs(args) -> int:
    r = httpx.get(f"{API_BASE}/api/jobs?limit={args.limit}", headers=_headers(), timeout=10)
    if r.status_code != 200:
        print(f"ERROR: {r.status_code} {r.text}", file=sys.stderr)
        return 1
    body = r.json()
    if args.json:
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return 0
    # 表形式
    print(f"{'JOB ID':<14}{'STATUS':<11}{'STEP':<22}{'PRODUCT'}")
    print("-" * 80)
    for j in body["jobs"]:
        sid = j["id"][:12]
        print(f"{sid:<14}{j['status']:<11}{j['step']:<22}{j['product_name'][:40]}")
    print(f"\n({body['count']} jobs)")
    return 0


def cmd_cancel(args) -> int:
    r = httpx.post(f"{API_BASE}/api/jobs/{args.job_id}/cancel", headers=_headers(), timeout=10)
    if r.status_code not in (202, 409):
        print(f"ERROR: {r.status_code} {r.text}", file=sys.stderr)
        return 1
    print(r.json())
    return 0 if r.status_code == 202 else 1


def cmd_upload_homestyler(args) -> int:
    r = httpx.post(
        f"{API_BASE}/api/jobs/{args.job_id}/upload-to-homestyler",
        headers=_headers(),
        timeout=10,
    )
    if r.status_code != 202:
        print(f"ERROR: {r.status_code} {r.text}", file=sys.stderr)
        return 1
    print(json.dumps(r.json(), ensure_ascii=False))
    if args.wait:
        return _watch(args.job_id)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="ec3d",
        description="EC3D-Bridge CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command", required=True)

    s_submit = sub.add_parser("submit", help="JSON 1 件を投入")
    s_submit.add_argument("file", help="ProductData JSON ファイル")
    s_submit.add_argument("--wait", action="store_true", help="終端までポーリング")
    s_submit.set_defaults(func=cmd_submit)

    s_status = sub.add_parser("status", help="1 回ステータス取得")
    s_status.add_argument("job_id")
    s_status.set_defaults(func=cmd_status)

    s_watch = sub.add_parser("watch", help="終端までポーリング")
    s_watch.add_argument("job_id")
    s_watch.set_defaults(func=cmd_watch)

    s_jobs = sub.add_parser("jobs", help="直近ジョブ一覧")
    s_jobs.add_argument("--limit", type=int, default=20)
    s_jobs.add_argument("--json", action="store_true", help="JSON で出力")
    s_jobs.set_defaults(func=cmd_jobs)

    s_cancel = sub.add_parser("cancel", help="ジョブをキャンセル")
    s_cancel.add_argument("job_id")
    s_cancel.set_defaults(func=cmd_cancel)

    s_up = sub.add_parser("upload-homestyler", help="成功ジョブを Homestyler に流す")
    s_up.add_argument("job_id")
    s_up.add_argument("--wait", action="store_true")
    s_up.set_defaults(func=cmd_upload_homestyler)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
