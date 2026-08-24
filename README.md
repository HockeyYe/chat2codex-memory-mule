# Chat2Codex Memory Mule

[简体中文](README.md) | [English](README_EN.md)

让 Codex 记住项目，而不必每次读完整个项目。

Chat2Codex Memory Mule 是一个仓库原生的 Codex Skill：它会扫描项目中已有的知识源，也可以提炼公开的 ChatGPT 分享会话，再将它们整理为紧凑、可追溯、可长期维护的项目记忆。Markdown 是各类工具之间的兼容层；原始文件继续留在原位，已经接受的知识不会被静默覆盖。

> 这是一个独立的社区项目，与 OpenAI 不存在隶属或背书关系。ChatGPT 和 Codex 是其各自权利人的商标。

## 功能

- 扫描 README、ADR、架构文档、路线图、研究材料和工程规范等现有知识源。
- 生成轻量的 `docs/project-memory/source-map.md`，不移动或复制原文件。
- 通过可替换的标准化读取接口导入公开的 `chatgpt.com/share/...` 会话。
- 将内容归类为决策、原则、研究、想法、开放问题、计划和已否决方向。
- 合并互相支持或扩展的知识，避免简单追加造成重复。
- 遇到冲突时交给人审，而不是静默修改已接受状态。
- 原始会话默认只保存在本地，并由 Git 忽略。

## 记忆库架构

```text
项目现有知识源                 ChatGPT 分享会话
README / ADR / docs / plans    chatgpt.com/share/...
          │                              │
          └──────────┬───────────────────┘
                     ▼
             扫描、标准化与来源记录
                     ▼
          分类、去重、关联与冲突检测
                     ▼
     docs/project-memory/   .project-memory/
     可读的长期记忆          注册表与本地原文
                     ▼
             Codex 的项目上下文
```

这套结构将“当前共识”“主题知识”“会话经历”和“来源证据”分层保存。项目原文和已接受的 ADR 始终是权威来源；记忆库是它们的精简索引与派生视图，而不是替代品。

## 设计参考与思想来源

本项目没有照搬某个记忆框架，而是组合了下列公开思想，并针对仓库内、Markdown 优先、人工可审查的使用方式做了轻量化取舍：

| 参考来源 | 借鉴的思想 | 在本项目中的对应设计 |
| --- | --- | --- |
| [OpenAI Codex：Use cases](https://learn.chatgpt.com/use-cases) | 将可重复的工作流程封装为可复用 Skill | 用 `SKILL.md` 描述稳定工作流，用 Python 助手承接确定性处理 |
| [Michael Nygard：Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) | 用短小、带上下文和状态的记录保存架构决策，并保留被替代的历史 | `decisions/` 保存编号决策；冲突和替代关系需要显式审查 |
| [MemGPT：Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560) | 通过分层记忆缓解有限上下文问题 | `current-state.md` 提供紧凑工作上下文，分类文档和会话记录承担长期记忆 |
| [Generative Agents](https://arxiv.org/abs/2304.03442) | 从经历记录中提取更高层的反思，并让记忆支持后续计划 | `sessions/` 保存会话经历，原则、决策和计划文件保存逐步提炼的长期知识 |
| [W3C PROV-O](https://www.w3.org/TR/prov-o/) | 来源追踪应描述信息、处理活动及其关系 | 保存来源 URL、处理时间、内容哈希、注册表和处理日志 |

这些来源是设计参考，不是运行时依赖。本项目不是 MemGPT、Generative Agents 或 PROV-O 的完整实现，也不声称与这些项目兼容；它只采用了适合代码仓库记忆管理的概念。

## 仓库结构

```text
chat2codex-memory-mule/
├── SKILL.md
├── agents/openai.yaml
├── references/memory-model.md
└── scripts/memory_mule.py
```

上面的目录就是完整、可安装的 Skill。仓库级文档、测试和 CI 放在该目录之外。

## 环境要求

- 支持个人 Skill 的 Codex
- Python 3.10 或更高版本
- 推荐安装 Git，以便可靠识别仓库根目录和受跟踪文件
- 导入 ChatGPT 分享链接时需要网络或浏览器访问能力

Python 助手仅使用标准库。

## 安装

克隆仓库后，将 Skill 目录复制到个人 Codex Skills 目录。

### Windows PowerShell

```powershell
Copy-Item `
  -LiteralPath '.\chat2codex-memory-mule' `
  -Destination "$env:USERPROFILE\.codex\skills\chat2codex-memory-mule" `
  -Recurse
```

### macOS 或 Linux

```bash
cp -R ./chat2codex-memory-mule "${CODEX_HOME:-$HOME/.codex}/skills/chat2codex-memory-mule"
```

安装后新建一个 Codex 任务，使 Skill 能被发现。

## 使用方式

初始化记忆库并连接项目现有知识：

```text
使用 $chat2codex-memory-mule 初始化这个仓库的项目记忆。
```

导入公开的 ChatGPT 分享会话：

```text
使用 $chat2codex-memory-mule 将这个会话整理进项目记忆：
https://chatgpt.com/share/...
```

只接受 `https://chatgpt.com/share/<id>` 形式的公开分享链接。普通会话链接（例如
`https://chatgpt.com/c/...`）会在本地校验后直接拒绝；Skill 不会为了读取它而打开带登录态的浏览器。

整理单个现有文件，但不移动它：

```text
使用 $chat2codex-memory-mule 将 docs/architecture.md 整理进项目记忆，保留原文件位置。
```

也可以直接调用确定性助手：

```bash
python chat2codex-memory-mule/scripts/memory_mule.py init --repo /path/to/repository
python chat2codex-memory-mule/scripts/memory_mule.py scan --repo /path/to/repository
python chat2codex-memory-mule/scripts/memory_mule.py status --repo /path/to/repository
```

## 生成的项目记忆

```text
docs/project-memory/
├── source-map.md
├── current-state.md
├── principles.md
├── decisions/
├── research/
├── ideas/
├── open-questions.md
├── plans/
└── sessions/

.project-memory/
├── registry.json
└── raw/
```

## 隐私与安全

- 只处理你有权使用的会话。
- 将 ChatGPT 分享链接视为可能公开的信息。
- 提交前审阅提炼后的 Markdown。
- 标准化的原始会话保存在 `.project-memory/raw/`，默认由 Git 忽略。
- Skill 会要求 Codex 从受跟踪的记忆中移除密钥和不必要的个人信息。
- 冲突知识必须经过明确的人工作出决定。

## 开发与验证

运行标准库测试：

```bash
python -m unittest discover -s tests -v
```

如果本机有 Codex `skill-creator`，可运行其验证器：

```bash
python /path/to/skill-creator/scripts/quick_validate.py chat2codex-memory-mule
```

提交改动前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

本项目采用 [MIT License](LICENSE)。
