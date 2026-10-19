#!/usr/bin/env python3
"""按需把 hub 里的技能装到本机（完整目录，带 scripts/references 等附属文件）。

pi-web-ui 市场的「全局安装」只写 SKILL.md 一个文件；需要完整技能时用这个脚本。

  python3 scripts/install.py --list                 # 列出全部（带中文介绍）
  python3 scripts/install.py --list k-dense         # 只看某个库
  python3 scripts/install.py k-dense-qiskit anthropic-pdf
  python3 scripts/install.py --remove k-dense-qiskit
  python3 scripts/install.py --project ~/proj k-dense-matplotlib   # 装到 <proj>/.pi/skills
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

HUB = Path(__file__).resolve().parent.parent
SKILLS = HUB / "skills"


def description(skill_dir: Path) -> str:
    md = skill_dir / "SKILL.md"
    if not md.exists():
        return ""
    m = re.search(r"^description:\s*(.+)$", md.read_text(encoding="utf-8"), re.M)
    return m.group(1).strip() if m else ""


def list_skills(prefix: str | None) -> None:
    ids = sorted(p.name for p in SKILLS.iterdir() if (p / "SKILL.md").exists())
    if prefix:
        ids = [i for i in ids if i.startswith(prefix)]
    for sid in ids:
        print(f"{sid:45s} {description(SKILLS / sid)}")
    print(f"\n共 {len(ids)} 个", file=sys.stderr)


def target_dir(project: str | None) -> Path:
    return Path(project).expanduser() / ".pi" / "skills" if project else Path.home() / ".pi" / "agent" / "skills"


def install(ids: list[str], project: str | None) -> int:
    dest_root = target_dir(project)
    dest_root.mkdir(parents=True, exist_ok=True)
    failed = 0
    for sid in ids:
        src = SKILLS / sid
        if not (src / "SKILL.md").exists():
            print(f"✗ 未知技能: {sid}", file=sys.stderr)
            failed += 1
            continue
        dest = dest_root / sid
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        print(f"✓ {sid} → {dest}")
    print(f"\n已安装 {len(ids) - failed} 个到 {dest_root}")
    return 1 if failed else 0


def remove(ids: list[str], project: str | None) -> int:
    dest_root = target_dir(project)
    for sid in ids:
        dest = dest_root / sid
        if dest.exists():
            shutil.rmtree(dest)
            print(f"✓ 已移除 {sid}")
        else:
            print(f"· 未安装: {sid}", file=sys.stderr)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*", help="技能 id，例如 k-dense-qiskit")
    ap.add_argument("--list", nargs="?", const="", metavar="PREFIX", help="列出技能（可按前缀过滤）")
    ap.add_argument("--remove", action="store_true", help="改为卸载")
    ap.add_argument("--project", metavar="DIR", help="装到 <DIR>/.pi/skills（默认全局 ~/.pi/agent/skills）")
    args = ap.parse_args()
    if args.list is not None:
        list_skills(args.list or None)
        return 0
    if not args.ids:
        ap.print_help()
        return 1
    return remove(args.ids, args.project) if args.remove else install(args.ids, args.project)


if __name__ == "__main__":
    raise SystemExit(main())
