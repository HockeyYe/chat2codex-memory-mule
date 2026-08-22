# Chat2Codex Memory Model

## Contents

1. Normalized conversation interface
2. Repository layout
3. Existing knowledge compatibility
4. Artifact schemas
5. Candidate and diff model
6. Merge rules
7. Current-state and principle rules
8. Failure and safety rules

## Normalized conversation interface

Make every reader return this provider-independent shape:

```json
{
  "title": "Conversation title",
  "source_url": "https://chatgpt.com/share/...",
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "metadata": {}
}
```

Preserve message order, meaningful text, roles, the source URL, title, and timestamps when available. Remove transport and UI metadata.

## Repository layout

```text
docs/project-memory/
├── README.md
├── source-map.md
├── current-state.md
├── principles.md
├── open-questions.md
├── inbox.md
├── processing-log.md
├── decisions/
├── research/
├── ideas/
├── plans/
│   ├── active/
│   └── completed/
└── sessions/

.project-memory/
├── registry.json
└── raw/
```

Treat Markdown as project knowledge. Treat the registry and raw files as local system state.

## Existing knowledge compatibility

Use `source-map.md` as the only additional compatibility artifact. Keep it lightweight: a scanner-managed inventory plus a preserved `Curated Source Roles` section. Do not create parallel copies of project documentation.

Apply this source priority when claims differ:

1. code, tests, schemas, and configuration for implemented behavior;
2. explicit project documentation and accepted ADRs/RFCs;
3. accepted decisions in project memory;
4. `current-state.md` as a concise derived view;
5. ideas and session history.

The scanner's category is a discovery hint, not a truth claim. After reading a source, record one reviewed role in `Curated Source Roles`:

- `canonical_source`: authoritative for a defined topic;
- `supporting_source`: useful evidence or explanation, but not authoritative;
- `raw_note`: unstructured input that may contain durable candidates;
- `session_like`: episodic discussion or meeting notes;
- `operational_only`: useful for execution but normally not long-term product memory;
- `not_project_memory`: exclude from semantic ingestion.

For every reviewed source, record its repository-relative link, role, topic/category, and any memory artifacts it supports. Prefer a compact line or table entry.

During initialization, read only enough high-signal sources to establish a minimal current state and canonical-source map. Do not exhaustively summarize every discovered file. When an existing ADR/RFC already records a decision, link to it instead of creating a duplicate decision file.

For individual-file organization, keep the original file in place by default. Update its curated role and distill only information that changes future decisions or execution. Move, rename, or rewrite the original only when the user explicitly requests that action.

## Artifact schemas

### Current state

Use `docs/project-memory/current-state.md`:

```markdown
# Current State

Last updated: YYYY-MM-DD

## Product / Project Definition
## Current Phase
## Current Priorities
## Current Architecture
## Confirmed Constraints
## Not Doing Now
## Next Important Steps
```

Keep it near 1,000–2,000 words maximum for a normal project. Prefer links to decisions over repeated rationale.

### Principles

Use `docs/project-memory/principles.md`:

```markdown
# Project Principles

## Principle: Title

### Rule
### Why
### Applies when
### Exceptions
```

### Decisions

Create one file per accepted product, architecture, strategy, or implementation decision at `decisions/NNN-short-name.md`:

```markdown
---
id: DEC-001
status: accepted
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources:
  - https://chatgpt.com/share/...
---

# Title

## Context
## Decision
## Rationale
## Alternatives Considered
## Consequences
## Exceptions
## Revisit When
```

Allow `proposed`, `accepted`, `superseded`, `rejected`, and `needs-review`. Add `superseded_by: DEC-XXX` when applicable. Preserve superseded decisions.

### Research

Create topical files under `research/`:

```markdown
---
status: active
last_checked: YYYY-MM-DD
sources:
  - https://example.com/source
---

# Topic

## Findings
## Evidence
## Implications
## Confidence
## Unknowns
```

Keep external sources when present. Label unsupported or time-sensitive claims as uncertain; do not invent citations.

### Ideas

Create topical files under `ideas/`:

```markdown
---
status: exploration
created: YYYY-MM-DD
sources:
  - https://chatgpt.com/share/...
---

# Title

## Idea
## Why It May Be Valuable
## Dependencies
## Risks
## Validation Needed
```

Allow `exploration`, `candidate`, `validated`, `rejected`, and `promoted`. Preserve and link an idea after promotion.

### Open questions

Keep active questions together in `open-questions.md`:

```markdown
## OQ-001: Title

Status: open
Created: YYYY-MM-DD

### Why It Matters
### Current Hypothesis
### How To Validate
### Related Decisions
### Sources
```

Allow `open`, `investigating`, `resolved`, and `deferred`. Link the resolution when marking a question resolved.

### Plans

Put committed current execution in `plans/active/` and completed work in `plans/completed/`:

```markdown
# Plan title

Status: Active

## Goal
## Scope
## Tasks
- [ ] Task
## Decisions Needed
## Blockers
## Notes
## Completion Criteria
```

Do not promote brainstorming into a plan.

### Session summaries

Create one `sessions/YYYY-MM-DD-short-title.md` per processed snapshot:

```markdown
---
source: https://chatgpt.com/share/...
processed_at: YYYY-MM-DDTHH:MM:SS+TZ
content_hash: sha256:...
---

# Session Title

## Main Topics
## Key Outcomes
## Decisions Extracted
## Ideas Extracted
## Research Findings
## Open Questions
## Next Actions
## Memory Changes
### Created
### Updated
### Confirmed Existing
### Conflicts Found
```

Summarize the episode; never copy the full transcript.

## Candidate and diff model

Distill these required categories before merging:

```json
{
  "main_topics": [],
  "decisions": [],
  "principles": [],
  "research_findings": [],
  "ideas": [],
  "open_questions": [],
  "plans": [],
  "rejected_directions": [],
  "next_actions": []
}
```

Prefer candidate items shaped as:

```json
{
  "summary": "...",
  "evidence": "brief paraphrase or message location",
  "confidence": 0.0,
  "status": "...",
  "source_url": "..."
}
```

For each candidate assign one relationship: `new`, `supports_existing`, `extends_existing`, `duplicates_existing`, `conflicts_existing`, `supersedes_existing`, `resolves_question`, or `promotes_idea`.

## Merge rules

- `new`: create a correctly categorized artifact.
- `supports_existing`: add provenance or concise rationale; do not create a duplicate.
- `extends_existing`: enrich the existing artifact while preserving its earlier meaning.
- `duplicates_existing`: make no project-knowledge change; record it under Confirmed Existing.
- `conflicts_existing`: keep accepted state unchanged and add a clearly labeled `Memory Conflict` review item to `open-questions.md`, including the candidate, target artifact, source, and `needs-review` status.
- `supersedes_existing`: use only for a clearly explicit new decision. Preserve the old file and link both directions.
- `resolves_question`: mark the question resolved and link its decision or research artifact.
- `promotes_idea`: retain the idea, set `status: promoted`, and link the new decision or plan.

Record a rejected direction only when rejection is explicit. Include the reason and a `Revisit when` condition when available. Casual hesitation is not rejection.

## Current-state and principle rules

Update current state only when the session materially changes the project definition, phase, priorities, architecture, confirmed constraints, active execution direction, or explicit not-now decisions. Do not add every idea or automatically promote research findings.

Add a principle only when it is reusable, stable, more general than one implementation choice, and likely to guide future work.

## Failure and safety rules

- Validate that URLs use HTTPS and a recognized ChatGPT share host.
- Keep raw transcripts in `.project-memory/raw/` and gitignore that directory.
- Redact secrets and unnecessary sensitive data from tracked Markdown.
- On a read or parse failure, modify only inbox/log bookkeeping; do not partially update accepted memory.
- On malformed registry JSON, stop and report the issue instead of overwriting it.
- Build the complete semantic write set before applying it.
- Finalize registry state only after all memory files are successfully written.
- Never resolve conflicts autonomously.
- Preserve scanner-managed markers and all content under `Curated Source Roles` when refreshing `source-map.md`.
