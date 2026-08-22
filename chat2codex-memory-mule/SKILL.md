---
name: chat2codex-memory-mule
description: Build and maintain lightweight, repository-native project memory for Codex by scanning and classifying existing project knowledge, organizing individual project files into the memory map, and distilling public ChatGPT shared conversations. Use when a user asks to initialize or inspect Chat2Codex memory, scan project docs or knowledge sources, organize a specific project file, remember/import/process a chatgpt.com/share link, or merge session-derived decisions, principles, research, ideas, questions, and plans without duplication or silent overwrites.
---

# Chat2Codex

Compile a shared ChatGPT session into compact, structured project knowledge. Preserve what can change future decisions or execution; do not archive everything said.

## Choose the operation

- For `init`, scan existing knowledge first, initialize repository memory, and bootstrap only high-confidence links and summaries.
- For `scan`, refresh the existing-source inventory without semantically rewriting memory.
- For `organize <file>`, scan and semantically classify one repository file, link it into memory, and extract only durable knowledge.
- For `import <url>` or natural-language equivalents, run the complete import workflow.
- For `status`, run the helper's status command and summarize the result. Treat this as a convenience operation, not part of the MVP contract.

## Locate the helper

Resolve paths relative to this `SKILL.md`:

```text
scripts/memory_mule.py
references/memory-model.md
```

Run the helper with the available Python 3 interpreter. Pass `--repo` when the user's target repository is not the current working directory.

## Initialize project memory and connect existing knowledge

Run:

```bash
python scripts/memory_mule.py init --repo <repository>
```

The helper discovers likely project knowledge before creating memory templates, then writes a single inventory to `docs/project-memory/source-map.md`. It must preserve existing documentation, append only a missing Project Memory navigation block to root `AGENTS.md`, and add `.project-memory/raw/` to `.gitignore` without duplication.

After the command:

1. Read `source-map.md`.
2. Read only high-signal candidates needed to establish the project definition, architecture, accepted decisions, active plans, and engineering guidance.
3. Record reviewed canonical-source roles in the preserved `Curated Source Roles` section.
4. Bootstrap `current-state.md` with concise, high-confidence facts and links to original documents.
5. Create memory decision artifacts only for explicit decisions when no existing ADR/RFC already serves as the canonical record.

Treat original project docs and accepted ADRs/RFCs as authoritative. Use project memory as an index and distilled view. Do not copy whole documents, move files, or populate templates with speculation.

## Refresh or organize project knowledge

Refresh the lightweight inventory with:

```bash
python scripts/memory_mule.py scan --repo <repository>
```

Organize one file with:

```bash
python scripts/memory_mule.py scan --repo <repository> --file <repo-relative-file>
```

For a single file, read the file, `source-map.md`, and only directly relevant memory. Classify the file as one of:

```text
canonical_source
supporting_source
raw_note
session_like
operational_only
not_project_memory
```

Then update `Curated Source Roles` with its role and category. Distill only durable knowledge into the existing memory categories. Prefer links over copied text. Do not relocate, rename, or rewrite the source file unless the user explicitly requests that separate action.

## Import one shared session

### 1. Read existing guidance

Detect the target repository. Read its applicable `AGENTS.md` files before modifying anything. Then read:

1. `docs/project-memory/current-state.md`
2. `docs/project-memory/principles.md`
3. `docs/project-memory/source-map.md` and relevant canonical sources listed there
4. relevant files in `decisions/`, `research/`, `ideas/`, `plans/active/`, and `open-questions.md`

Read historical `sessions/` only when provenance, duplicate detection, or deeper context requires it.

### 2. Prepare the source

Run:

```bash
python scripts/memory_mule.py prepare --repo <repository> --url <chatgpt-share-url> --output <temporary-normalized-json>
```

Interpret the JSON status printed to stdout:

- `ready`: continue with the normalized conversation at `output`.
- `already_processed`: report that no new memory changes are required and stop.
- a nonzero exit: report the concise error. The helper records the failed inbox item and processing-log entry; do not modify accepted project memory.

If the built-in reader cannot parse a currently valid shared page, obtain the full conversation with an available authenticated browser or supported connector, convert it to the normalized interface documented in `references/memory-model.md`, and rerun `prepare` with `--input <normalized-json>`. Do not bypass access controls or request private credentials.

### 3. Distill conservatively

Read the complete normalized conversation. Produce candidate memories for:

- decisions;
- stable principles;
- evidence-backed research;
- uncommitted ideas;
- open questions;
- committed plans;
- explicit rejected directions;
- next actions.

Preserve epistemic status. If unsure whether a statement is a decision, classify it as an idea or open question. Do not turn assistant suggestions into accepted user decisions without evidence. Do not turn research into current project state automatically.

Before writing tracked Markdown, redact secrets, credentials, private customer data, and unnecessary personal identifiers. Never copy a secret merely because the session contains it.

### 4. Compute a memory diff

Read `references/memory-model.md` completely before the first import in a task. For every candidate, search the relevant existing memory and assign exactly one relationship:

```text
new
supports_existing
extends_existing
duplicates_existing
conflicts_existing
supersedes_existing
resolves_question
promotes_idea
```

Apply the documented merge rule and source precedence. Before creating memory from a candidate, compare it with relevant canonical project documents from `source-map.md`, not only files already under `project-memory`. Never silently replace an accepted decision or principle. Keep ideas out of active plans unless the conversation contains an actual commitment.

### 5. Stage and review the complete write set

Prepare all proposed contents before changing accepted memory. The write set normally includes:

- one session summary;
- new or updated category artifacts;
- `current-state.md` only for material state changes;
- `principles.md` only for stable reusable guidance;
- a finalization report JSON for the helper.

Use the schemas and naming rules in `references/memory-model.md`. Preserve existing meaning and source links when extending artifacts. Keep `current-state.md` concise.

Review the complete write set for contradictions, duplicates, speculative claims, and sensitive information. Then write it with the safest available atomic or patch-based mechanism. Do not write the full transcript into tracked files; the helper stores it under the gitignored raw directory.

### 6. Finalize bookkeeping

Create a temporary JSON report using this shape:

```json
{
  "main_topics": [],
  "created": [],
  "updated": [],
  "confirmed_existing": [],
  "conflicts": [],
  "notes": []
}
```

Then run:

```bash
python scripts/memory_mule.py finalize --repo <repository> --url <url> --title <title> --content-hash <sha256:...> --session-file <repo-relative-session-path> --report <report-json>
```

Finalize only after all accepted memory files and the session summary are successfully written. If a write fails, leave the inbox item pending or mark it failed with the helper and explain what remains; do not claim completion.

### 7. Report the result

Lead with `Project memory updated.` Then list the session title, created artifacts, updated artifacts, confirmed duplicates, and conflicts. State explicitly when no conflicts were found.

## Maintain strict boundaries

- Keep repository Markdown as project knowledge and `.project-memory/registry.json` as system state.
- Keep existing canonical project documents authoritative; use `source-map.md` to connect them instead of duplicating them.
- Keep raw transcripts local and gitignored by default.
- Preserve superseded and rejected history with links; do not delete it.
- Require explicit user resolution for conflicts before changing accepted state.
- Avoid vector databases, background synchronization, knowledge graphs, dashboards, and multi-user or cross-agent networks in the MVP.
- Do not hard-code a project name, product domain, model provider, or repository layout beyond the project-memory directories.
