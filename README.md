# pi-skills-hub

把多个上游 Agent Skill 库**聚合成一个可检索的仓库**，专门给 [pi-web-ui](https://github.com/xing-shuyin/pi-web-ui)
的技能市场（设置 → 技能 → 技能市场 → GitHub 仓库源）用。

pi-web-ui 的市场一次只能填 **一个** 仓库，且只把仓库 `skills/` 下**一层子目录**当成技能
（标题取目录名，介绍取 `SKILL.md` 的 `description`）。所以这里把四个库的技能平铺到同一层，
目录名加来源前缀，`description` 换成中文摘要，**技能正文保持上游英文原文**。

## 包含的库

| 前缀 | 上游仓库 | 个数 | 用途 |
| --- | --- | --- | --- |
| `superpowers-` | [obra/superpowers](https://github.com/obra/superpowers) | 15 | 系统排错、完成前验证、代码审查、TDD、规划 |
| `anthropic-` | [anthropics/skills](https://github.com/anthropics/skills) | 19 | PDF / PPTX / DOCX / XLSX、skill-creator、前端设计 |
| `vercel-` | [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) | 9 | React 性能、界面规范、部署 |
| `k-dense-` | [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) | 177 | 科研与 RL：Stable-Baselines3、文献综述、科研绘图等 |

合计 **220** 个技能，清单见 `MANIFEST.json`，来源配置见 `sources.json`。

## 在 pi-web-ui 里使用

1. 设置 → 技能 → 技能市场
2. 「GitHub 仓库源」选 **自定义 GitHub 仓库 (owner/repo)**，填 `<你的用户名>/pi-skills-hub`
3. 点「重新加载」→ 220 个技能可搜索（中文关键词直接搜，例如「文献综述」「调试」「PPT」）

## 重新同步上游

```bash
python3 scripts/sync.py                 # 重新下载四个库并重建 skills/
python3 scripts/sync.py --install-local # 额外同步到 ~/.pi/agent/skills（完整目录，立即可用）
```

同步流程：下载 tarball → 平铺复制（跳过 >8MB 的单文件，见 `MANIFEST.json`）→
按 `scripts/zh/*.json` 把 `description` 改成中文 → 可选地复制到本机技能目录。

## 中文描述

`scripts/zh/{A,B,C,D}.json` 是 `技能 id → 中文摘要` 的映射，`scripts/i18n.py` 负责把摘要写进
各 `SKILL.md` 的 frontmatter。上游新增技能会先以英文描述落地，并在同步时提示缺少翻译。

只改 `description:`，正文（指令、脚本、参考资料）与上游一致。

## 已知限制

- pi-web-ui 市场的「安装」只会把 `SKILL.md` 一个文件写到 `~/.pi/agent/skills/<id>/`，
  **不带** `scripts/`、`references/`、模板等附属文件。需要完整技能时用
  `python3 scripts/sync.py --install-local`，它复制整个目录。
- 技能 id 必须匹配 `^[a-zA-Z0-9_-]+$`（pi-web-ui 的安装校验），所以目录名保持英文；
  中文只出现在介绍与检索里。
- 上游改动后 GitHub API 有 1 小时缓存，市场里点「重新加载」可强制刷新。

## 许可

各上游库的许可与第三方声明收集在 `licenses/`。技能内容版权归各上游作者所有，本仓库只做聚合与中文介绍。
