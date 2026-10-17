#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通过 GitHub REST API 提交（Git Data API）

用途：当 github.com:443 不可达、但 api.github.com 可用时，
     用它替代 `git push` 完成提交。

原理：blob -> tree -> commit -> 更新 ref，等价于一次普通提交。
不改变文件内容，只搬运。

用法（PowerShell / Bash）：
    GH_TOKEN=ghp_xxx python tools/push_via_api.py "提交说明"
"""

import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OWNER = "qingfeng-crypto"
REPO = "test-site"
BRANCH = "main"
API = "https://api.github.com"

TOKEN = os.environ.get("GH_TOKEN", "").strip()
if not TOKEN:
    print("缺少环境变量 GH_TOKEN")
    sys.exit(1)

MESSAGE = sys.argv[1] if len(sys.argv) > 1 else "Update via API"


def call(method, path, body=None):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        method=method,
        headers={
            "Authorization": "Bearer " + TOKEN,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "workbuddy",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            raw = r.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        print(f"[HTTP {e.code}] {method} {path}\n{detail}")
        raise


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(repo_root)

    print("[1/5] 读取远程分支指针")
    ref = call("GET", f"/repos/{OWNER}/{REPO}/git/ref/heads/{BRANCH}")
    head_sha = ref["object"]["sha"]
    print("      HEAD =", head_sha[:10])

    print("[2/5] 读取基线 tree")
    commit = call("GET", f"/repos/{OWNER}/{REPO}/git/commits/{head_sha}")
    base_tree = commit["tree"]["sha"]
    print("      base tree =", base_tree[:10])

    files = subprocess.check_output(
        ["git", "ls-tree", "-r", "HEAD", "--name-only"], text=True
    ).split()
    # .gitignore 里的文件本来就不在 git 索引里，无需处理
    print(f"[3/5] 上传 {len(files)} 个 blob")

    tree_items = []
    for f in files:
        with open(f, "rb") as fh:
            raw = fh.read()
        blob = call("POST", f"/repos/{OWNER}/{REPO}/git/blobs", {
            "content": base64.b64encode(raw).decode("ascii"),
            "encoding": "base64",
        })
        tree_items.append({
            "path": f.replace("\\", "/"),
            "mode": "100644",
            "type": "blob",
            "sha": blob["sha"],
        })
        print(f"      {f:<34} {len(raw)/1024:8.1f} KB")

    print("[4/5] 创建 tree")
    new_tree = call("POST", f"/repos/{OWNER}/{REPO}/git/trees", {
        "base_tree": base_tree,
        "tree": tree_items,
    })
    print("      new tree =", new_tree["sha"][:10])

    print("[5/5] 创建 commit 并更新 ref")
    new_commit = call("POST", f"/repos/{OWNER}/{REPO}/git/commits", {
        "message": MESSAGE,
        "tree": new_tree["sha"],
        "parents": [head_sha],
    })
    call("PATCH", f"/repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}",
         {"sha": new_commit["sha"], "force": False})
    print("      提交成功：", new_commit["sha"][:10])
    print("      " + new_commit["html_url"])


if __name__ == "__main__":
    main()
