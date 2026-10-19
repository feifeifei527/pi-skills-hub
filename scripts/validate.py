#!/usr/bin/env python3
"""聚合仓库自检：结构、命名、中文描述、体积、MANIFEST 一致性。

CI 里跑 `python3 scripts/validate.py --strict-zh`；本地可加 --quiet。
退出码 1 = 有错误；缺中文描述只算警告，除非 --strict-zh。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HUB = Path(__file__).resolve().parent.parent
SKILLS = HUB / "skills"
ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
MAX_FILE_BYTES = 8 * 1024 * 1024


def frontmatter(md: Path) -> dict[str, str] | None:
    text = md.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fields: dict[str, str] = {}
    lines = text[3:end].split("\n")
    i = 0
    while i < len(lines):
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", lines[i])
        if not m:
            i += 1
            continue
        key, value = m.group(1), m.group(2).strip()
        if value in (">", ">-", "|", "|-", "|+", ">+", ""):
            buf = []
            for nxt in lines[i + 1:]:
                if nxt.strip() == "" or nxt[:1] in (" ", "\t"):
                    buf.append(nxt.strip())
                else:
                    break
            value = " ".join(x for x in buf if x)
            i = i + 1 + len(buf)
        else:
            i += 1
        fields[key] = value.strip('"\'')
    return fields


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict-zh", action="store_true", help="缺中文描述也算失败")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    sources = json.loads((HUB / "sources.json").read_text(encoding="utf-8"))
    prefixes = {lib["prefix"] for lib in sources.get("libraries", [])}
    if not prefixes:
        errors.append("sources.json 里没有 libraries")
    if not sources.get("market_repo"):
        errors.append("sources.json 缺少 market_repo")

    if not SKILLS.is_dir():
        errors.append("skills/ 不存在，先跑 scripts/sync.py")
        print("\n".join(errors))
        return 1

    skill_dirs = sorted(p for p in SKILLS.iterdir() if p.is_dir())
    ids: list[str] = []
    zh = {}
    for f in sorted((HUB / "scripts" / "zh").glob("*.json")):
        zh.update(json.loads(f.read_text(encoding="utf-8")))

    for d in skill_dirs:
        sid = d.name
        ids.append(sid)
        if not ID_RE.match(sid):
            errors.append(f"{sid}: id 只能包含字母数字下划线中划线")
        if not any(sid.startswith(p + "-") for p in prefixes):
            errors.append(f"{sid}: 前缀不在 sources.json 里（{'/'.join(sorted(prefixes))}）")
        md = d / "SKILL.md"
        if not md.exists():
            errors.append(f"{sid}: 缺 SKILL.md")
            continue
        fm = frontmatter(md)
        if fm is None:
            errors.append(f"{sid}: SKILL.md 没有合法 frontmatter")
            continue
        if not fm.get("name"):
            errors.append(f"{sid}: frontmatter 缺 name")
        desc = fm.get("description", "")
        if not desc:
            errors.append(f"{sid}: frontmatter 缺 description")
        elif "\n" in desc:
            errors.append(f"{sid}: description 必须单行（市场解析只取首行）")
        elif not CJK_RE.search(desc):
            msg = f"{sid}: description 不是中文"
            (errors if args.strict_zh else warnings).append(msg)
        if sid not in zh:
            msg = f"{sid}: scripts/zh/*.json 缺中文映射"
            (errors if args.strict_zh else warnings).append(msg)
        for f in d.rglob("*"):
            if f.is_file() and f.stat().st_size > MAX_FILE_BYTES:
                errors.append(f"{sid}: {f.relative_to(d)} 超过 8MB")

    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        errors.append(f"重复 id: {sorted(dupes)}")

    manifest_file = HUB / "MANIFEST.json"
    if manifest_file.exists():
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        if manifest.get("total") != len(ids):
            errors.append(f"MANIFEST total={manifest.get('total')} 与实际 {len(ids)} 不一致（重跑 sync.py）")
        missing = {i for lst in manifest.get("libraries", {}).values() for i in lst} - set(ids)
        if missing:
            errors.append(f"MANIFEST 里有不存在的技能: {sorted(missing)[:5]}")
    else:
        errors.append("缺 MANIFEST.json")

    if not args.quiet:
        print(f"技能 {len(ids)} 个 · 前缀 {len(prefixes)} 个 · 中文映射 {len(zh)} 条")
        for w in warnings:
            print(f"WARN  {w}")
        for e in errors[:50]:
            print(f"ERROR {e}")
        if len(errors) > 50:
            print(f"... 还有 {len(errors) - 50} 条错误")
    if errors:
        print(f"\n✗ 校验失败：{len(errors)} 个错误，{len(warnings)} 个警告")
        return 1
    print(f"✓ 校验通过（{len(warnings)} 个警告）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
