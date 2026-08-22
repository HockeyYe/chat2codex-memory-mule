# Chat2Codex Memory Mule

Make Codex remember it without making Codex read it all.

Chat2Codex Memory Mule is a repository-native Codex skill that turns shared ChatGPT conversations and existing project documentation into compact, durable project memory. It keeps Markdown as the interoperability layer, preserves provenance, and avoids silently duplicating or overwriting accepted knowledge.

> This is an independent community project and is not affiliated with or endorsed by OpenAI. ChatGPT and Codex are trademarks of their respective owner.

## What it does

- Scans existing README files, ADRs, architecture documents, roadmaps, research, and engineering guidance.
- Builds a lightweight `docs/project-memory/source-map.md` without moving or copying original documents.
- Imports public `chatgpt.com/share/...` conversations through a replaceable normalized-reader interface.
- Separates decisions, principles, research, ideas, open questions, plans, and rejected directions.
- Merges supporting or extending knowledge instead of appending duplicates.
- Flags conflicts for human review instead of changing accepted state silently.
- Keeps raw transcripts local and gitignored by default.

## Repository layout

```text
chat2codex-memory-mule/
├── SKILL.md
├── agents/openai.yaml
├── references/memory-model.md
└── scripts/memory_mule.py
```

The folder above is the complete installable skill. Repository-level documentation, tests, and CI remain outside it.

## Requirements

- Codex with personal skill support
- Python 3.10 or newer
- Git is recommended for reliable repository-root and tracked-file discovery
- Network or browser access when importing a ChatGPT shared link

The helper uses only the Python standard library.

## Install

Clone this repository, then copy the skill directory into your personal Codex skills folder.

### Windows PowerShell

```powershell
Copy-Item `
  -LiteralPath '.\chat2codex-memory-mule' `
  -Destination "$env:USERPROFILE\.codex\skills\chat2codex-memory-mule" `
  -Recurse
```

### macOS or Linux

```bash
cp -R ./chat2codex-memory-mule "${CODEX_HOME:-$HOME/.codex}/skills/chat2codex-memory-mule"
```

Open a new Codex task after installation so the skill can be discovered.

## Use

Initialize memory and connect existing project knowledge:

```text
Use $chat2codex-memory-mule to initialize project memory in this repository.
```

Import a public ChatGPT shared conversation:

```text
Use $chat2codex-memory-mule to process this conversation into project memory:
https://chatgpt.com/share/...
```

Organize one existing file without moving it:

```text
Use $chat2codex-memory-mule to organize docs/architecture.md into project memory.
Keep the original file in place.
```

The deterministic helper can also be invoked directly:

```bash
python chat2codex-memory-mule/scripts/memory_mule.py init --repo /path/to/repository
python chat2codex-memory-mule/scripts/memory_mule.py scan --repo /path/to/repository
python chat2codex-memory-mule/scripts/memory_mule.py status --repo /path/to/repository
```

## Generated project memory

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

Original project documents and accepted ADRs remain authoritative. Project memory acts as a concise index and derived view.

## Privacy and safety

- Only import conversations you are authorized to process.
- Treat ChatGPT shared links as potentially public.
- Review distilled Markdown before committing it.
- Raw normalized transcripts are stored under `.project-memory/raw/` and ignored by default.
- The skill instructs Codex to redact secrets and unnecessary personal information from tracked memory.
- Conflicting knowledge is queued for explicit human resolution.

## Development

Run the standard-library test suite:

```bash
python -m unittest discover -s tests -v
```

Validate the installable skill with Codex's `skill-creator` validator when available:

```bash
python /path/to/skill-creator/scripts/quick_validate.py chat2codex-memory-mule
```

See [CONTRIBUTING.md](CONTRIBUTING.md) before submitting changes.

## License

Licensed under the [MIT License](LICENSE).
