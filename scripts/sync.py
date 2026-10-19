#!/usr/bin/env python3
"""把 sources.json 里配置的多个技能库聚合成一个扁平 skills/ 目录。

为什么需要它：pi-web-ui 的技能市场一次只能填一个 GitHub 仓库，
且只扫描该仓库「skills/ 下一层子目录」当作技能（描述取 SKILL.md 的
description:）。所以要把多个库放进同一个可检索仓库，必须平铺。

用法:
  python3 scripts/sync.py                  # 重新下载并重建 skills/
  python3 scripts/sync.py --install-local  # 额外同步到 ~/.pi/agent/skills
  python3 scripts/sync.py --offline        # 用 /tmp/skillsrc 已有解压副本（调试用）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

HUB = Path(__file__).resolve().parent.parent
SKILLS = HUB / "skills"
MAX_FILE_BYTES = 8 * 1024 * 1024  # 单文件上限，超出跳过（大多为数据集/大 PDF）


def load_sources() -> dict:
    return json.loads((HUB / "sources.json").read_text(encoding="utf-8"))


def fetch_repo(repo: str, dest: Path) -> Path:
    """下载仓库 main 分支 tarball 并解压到 dest，返回解压根目录。"""
    url = f"https://codeload.github.com/{repo}/tar.gz/refs/heads/main"
    tgz = dest / (repo.replace("/", "_") + ".tar.gz")
    print(f"  下载 {url}")
    subprocess.run(
        ["curl", "-fsSL", "--max-time", "900", "-o", str(tgz), url],
        check=True,
    )
    root = dest / repo.replace("/", "_")
    root.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tgz) as tf:
        tf.extractall(root, filter="data")  # 去掉顶层 <repo>-main/
    children = list(root.iterdir())
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return root


def normalize_name(skill_md: Path, skill_id: str) -> None:
    """把 frontmatter 的 name 改成技能 id（= 目录名）。

    pi-web-ui 的市场用「目录 id」判断是否已安装，而已安装列表用的是
    frontmatter 的 name；两者不一致时，装完卡片也不会变成「已安装」。
    """
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return
    end = text.find("\n---", 3)
    if end == -1:
        return
    head, body = text[3:end], text[end:]
    if re.search(r"^name:\s*" + re.escape(skill_id) + r"\s*$", head, re.M):
        return
    if re.search(r"^name:.*$", head, re.M):
        head = re.sub(r"^name:.*$", f"name: {skill_id}", head, count=1, flags=re.M)
    else:
        head = f"\nname: {skill_id}" + head
    skill_md.write_text("---" + head + body, encoding="utf-8")


def copy_skill(src: Path, dst: Path, skipped: list[str]) -> None:
    """复制技能目录，跳过超大文件。"""
    for path in sorted(src.rglob("*")):
        rel = path.relative_to(src)
        target = dst / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        if not path.is_file():
            continue
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            skipped.append(f"{src.name}/{rel} ({size / 1e6:.1f}MB)")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def rebuild(offline: bool, install_local: bool) -> int:
    cfg = load_sources()
    staging = Path(tempfile.mkdtemp(prefix="skills-sync-"))
    new_skills = staging / "skills"
    new_skills.mkdir()
    manifest: dict[str, list[str]] = {}
    skipped: list[str] = []

    for lib in cfg["libraries"]:
        repo, prefix, subdir = lib["repo"], lib["prefix"], lib.get("subdir", "skills")
        print(f"[{prefix}] {repo}")
        if offline:
            root = Path("/tmp/skillsrc") / repo.replace("/", "_")
            if not root.exists():
                sys.exit(f"离线模式缺少 {root}，先不带 --offline 跑一次")
        else:
            root = fetch_repo(repo, staging)
        skills_dir = root / subdir
        if not skills_dir.is_dir():
            sys.exit(f"{repo} 下没有 {subdir}/ 目录，检查 sources.json")
        excluded = set(lib.get("exclude") or [])
        names = sorted(
            d for d in os.listdir(skills_dir)
            if (skills_dir / d).is_dir() and d not in excluded
        )
        if excluded:
            print(f"  按 sources.json 排除 {len(excluded)} 个")
        ids: list[str] = []
        for name in names:
            if not (skills_dir / name / "SKILL.md").exists():
                print(f"  ! 跳过无 SKILL.md 的目录: {name}")
                continue
            skill_id = f"{prefix}-{name}"
            if (new_skills / skill_id).exists():
                sys.exit(f"技能 id 冲突: {skill_id}")
            copy_skill(skills_dir / name, new_skills / skill_id, skipped)
            normalize_name(new_skills / skill_id / "SKILL.md", skill_id)
            ids.append(skill_id)
        manifest[prefix] = ids
        print(f"  → {len(ids)} 个技能")

    # 中文 description（检索与介绍用中文，正文保持英文）
    from i18n import apply as apply_i18n

    zh_done, zh_missing = apply_i18n(new_skills, HUB)
    print(f"  description 中文化：{zh_done} 个" + (f"（缺翻译 {len(zh_missing)}）" if zh_missing else ""))

    # 用 staging 替换正式目录（先保留旧目录以便回滚）
    backup = HUB / "skills.previous"
    if SKILLS.exists():
        if backup.exists():
            shutil.rmtree(backup)
        SKILLS.rename(backup)
    new_skills.rename(SKILLS)
    shutil.rmtree(staging, ignore_errors=True)

    total = sum(len(v) for v in manifest.values())
    (HUB / "MANIFEST.json").write_text(
        json.dumps({"total": total, "libraries": manifest, "skipped_big_files": skipped},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\n完成：{total} 个技能 → {SKILLS}")
    if skipped:
        print(f"跳过 {len(skipped)} 个超大文件（清单见 MANIFEST.json）")

    if install_local:
        target = Path.home() / ".pi" / "agent" / "skills"
        target.mkdir(parents=True, exist_ok=True)
        managed = {i for ids in manifest.values() for i in ids}
        for skill_id in sorted(managed):
            dst = target / skill_id
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(SKILLS / skill_id, dst)
        print(f"已同步到 {target}（{len(managed)} 个技能）")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="使用 /tmp/skillsrc 已解压副本")
    ap.add_argument("--install-local", action="store_true", help="同时同步到 ~/.pi/agent/skills")
    args = ap.parse_args()
    raise SystemExit(rebuild(args.offline, args.install_local))
