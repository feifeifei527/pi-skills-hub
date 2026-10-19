#!/usr/bin/env python3
"""把 Chinese summaries（scripts/zh/*.json）写进各技能 SKILL.md 的 frontmatter。

只改 `description:` 一行，技能正文保持英文原样。
pi-web-ui 的技能市场、pi 的 available_skills 提示词都读 description，
所以这一层就是「检索与介绍用中文，内容用英文」的落点。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

FM_END = "\n---"


def load_zh(hub: Path) -> dict[str, str]:
    merged: dict[str, str] = {}
    zh_dir = hub / "scripts" / "zh"
    if not zh_dir.is_dir():
        return merged
    for f in sorted(zh_dir.glob("*.json")):
        merged.update(json.loads(f.read_text(encoding="utf-8")))
    return merged


def _safe_scalar(text: str) -> str:
    """避免 YAML 歧义：去掉会破坏 plain scalar 的 `: ` 与行首 #。"""
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace(": ", "：").replace(" #", " ＃")
    return text


def rewrite_description(skill_md: Path, zh: str) -> bool:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return False
    end = text.find(FM_END, 3)
    if end == -1:
        return False
    head_lines = text[3:end].split("\n")
    body = text[end:]

    start = next((i for i, l in enumerate(head_lines) if re.match(r"^description:", l)), None)
    if start is None:
        return False
    # description 块：本行 + 后续缩进行（折叠/多行标量）
    stop = start + 1
    while stop < len(head_lines) and (
        head_lines[stop].strip() == "" or head_lines[stop][:1] in (" ", "\t")
    ):
        stop += 1
    head_lines[start:stop] = [f"description: {_safe_scalar(zh)}"]
    skill_md.write_text("---" + "\n".join(head_lines) + body, encoding="utf-8")
    return True


def apply(skills_root: Path, hub: Path) -> tuple[int, list[str]]:
    zh = load_zh(hub)
    done, missing = 0, []
    for skill_md in sorted(skills_root.glob("*/SKILL.md")):
        sid = skill_md.parent.name
        summary = (zh.get(sid) or "").strip()
        if not summary:
            missing.append(sid)
            continue
        if rewrite_description(skill_md, summary):
            done += 1
        else:
            missing.append(sid)
    return done, missing


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    n, miss = apply(root / "skills", root)
    print(f"已中文化 description：{n} 个" + (f"，缺翻译：{len(miss)} {miss[:5]}" if miss else ""))
