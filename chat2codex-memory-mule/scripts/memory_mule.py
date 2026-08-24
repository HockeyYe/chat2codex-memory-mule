#!/usr/bin/env python3
"""Deterministic plumbing for the Chat2Codex memory-mule skill.

Semantic distillation stays with Codex. This helper owns repository initialization,
share-page adaptation, hashing, raw storage, inbox, registry, and audit logs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


MEMORY = Path("docs/project-memory")
STATE = Path(".project-memory")
RAW = STATE / "raw"
REGISTRY = STATE / "registry.json"
AGENTS_MARKER = "<!-- chat2codex-memory:start -->"
SOURCE_SCAN_START = "<!-- chat2codex-source-scan:start -->"
SOURCE_SCAN_END = "<!-- chat2codex-source-scan:end -->"
KNOWLEDGE_EXTENSIONS = {".md", ".mdx", ".rst", ".txt", ".adoc", ".org"}
SCAN_EXCLUDED_PARTS = {
    ".git", ".project-memory", ".venv", "venv", "node_modules", "vendor",
    "dist", "build", "target", "coverage", ".next", ".cache", "__pycache__",
}


def now() -> dt.datetime:
    return dt.datetime.now().astimezone()


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


def repo_root(start: str | None) -> Path:
    base = Path(start or Path.cwd()).resolve()
    if base.is_file():
        base = base.parent
    try:
        result = subprocess.run(
            ["git", "-C", str(base), "rev-parse", "--show-toplevel"],
            check=True, capture_output=True, text=True,
        )
        return Path(result.stdout.strip()).resolve()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return base


def create_once(path: Path, content: str) -> bool:
    if path.exists():
        return False
    atomic_write(path, content)
    return True


def knowledge_paths(repo: Path) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            check=True, capture_output=True,
        )
        relatives = [Path(value.decode("utf-8", errors="replace")) for value in result.stdout.split(b"\0") if value]
    except (FileNotFoundError, subprocess.CalledProcessError):
        relatives = [path.relative_to(repo) for path in repo.rglob("*") if path.is_file()]

    candidates = []
    for relative in relatives:
        lowered_parts = {part.lower() for part in relative.parts}
        if lowered_parts & SCAN_EXCLUDED_PARTS:
            continue
        if len(relative.parts) >= 2 and relative.parts[0].lower() == "docs" and relative.parts[1].lower() == "project-memory":
            continue
        absolute = repo / relative
        if not absolute.is_file():
            continue
        name = relative.name.lower()
        suffix = relative.suffix.lower()
        structured_doc = suffix in {".yaml", ".yml", ".json"} and any(
            token in name for token in ("openapi", "spec", "requirements", "roadmap")
        )
        if suffix not in KNOWLEDGE_EXTENSIONS and not structured_doc:
            continue
        if relative.as_posix().lower() == "agents.md":
            try:
                agent_text = absolute.read_text(encoding="utf-8").strip()
            except (OSError, UnicodeError):
                agent_text = ""
            if agent_text.startswith(AGENTS_MARKER) and agent_text.endswith("<!-- chat2codex-memory:end -->"):
                continue
        try:
            if absolute.stat().st_size > 1_500_000:
                continue
        except OSError:
            continue
        candidates.append(relative)
    return sorted(set(candidates), key=lambda path: path.as_posix().lower())


def classify_knowledge_source(relative: Path) -> str:
    value = relative.as_posix().lower()
    name = relative.name.lower()
    if name.startswith("readme") or any(token in value for token in ("product", "overview", "prd", "requirements")):
        return "Project Definition & Requirements"
    if name in {"agents.md", "contributing.md", "development.md", "styleguide.md", "style-guide.md"}:
        return "Engineering Guidance"
    if any(token in value for token in ("/adr/", "architecture", "decision", "/rfc/", "design-doc")):
        return "Architecture & Decisions"
    if any(token in value for token in ("roadmap", "backlog", "milestone", "/plans/", "todo")):
        return "Plans & Roadmap"
    if any(token in value for token in ("research", "analysis", "benchmark", "discovery", "market")):
        return "Research & Analysis"
    if any(token in value for token in ("runbook", "operations", "deployment", "deploy", "release", "/ops/")):
        return "Operations & Runbooks"
    if any(token in value for token in ("guide", "contributing", "development", "conventions", "standards")):
        return "Engineering Guidance"
    return "Reference & Review"


def source_map_template() -> str:
    return f"""# Project Knowledge Source Map

This file maps existing project knowledge into the memory system without copying or moving the original files. Original canonical documents remain authoritative.

## Source Priority

1. Code, tests, schemas, and configuration
2. Explicit project documentation and accepted ADRs/RFCs
3. Accepted decisions under `docs/project-memory/decisions/`
4. `current-state.md` as a concise derived view
5. Ideas and historical sessions

{SOURCE_SCAN_START}
_No scan has been run._
{SOURCE_SCAN_END}

## Curated Source Roles

Use this section for human- or agent-reviewed overrides, canonical-source declarations, and links between original files and distilled memory. The scanner preserves this section.

_None recorded._
"""


def update_source_map(repo: Path, paths: list[Path], focus: Path | None = None) -> dict[str, Any]:
    destination = repo / MEMORY / "source-map.md"
    current = destination.read_text(encoding="utf-8") if destination.exists() else source_map_template()
    grouped: dict[str, list[Path]] = {}
    for relative in paths:
        grouped.setdefault(classify_knowledge_source(relative), []).append(relative)
    order = (
        "Project Definition & Requirements", "Architecture & Decisions", "Plans & Roadmap",
        "Engineering Guidance", "Research & Analysis", "Operations & Runbooks", "Reference & Review",
    )
    lines = [f"Last scanned: {now().isoformat(timespec='seconds')}", "", "Classifications below are heuristic discovery results. Confirm canonical roles in `Curated Source Roles`."]
    for category in order:
        entries = grouped.get(category, [])
        if not entries:
            continue
        lines += ["", f"### {category}", ""]
        for relative in entries:
            label = relative.as_posix()
            target = "../../" + label.replace(" ", "%20")
            lines.append(f"- [{label}]({target})")
    if len(lines) == 3:
        lines += ["", "_No project knowledge sources discovered._"]
    managed = "\n".join(lines)
    if SOURCE_SCAN_START in current and SOURCE_SCAN_END in current:
        prefix, remainder = current.split(SOURCE_SCAN_START, 1)
        _, suffix = remainder.split(SOURCE_SCAN_END, 1)
        content = prefix.rstrip() + "\n\n" + SOURCE_SCAN_START + "\n" + managed + "\n" + SOURCE_SCAN_END + suffix
    else:
        content = source_map_template().replace("_No scan has been run._", managed)
    atomic_write(destination, content.rstrip() + "\n")
    focus_result = None
    if focus is not None:
        focus_result = {"file": focus.as_posix(), "suggested_category": classify_knowledge_source(focus)}
    return {"discovered": len(paths), "categories": {key: len(value) for key, value in grouped.items()},
            "source_map": destination.relative_to(repo).as_posix(), "focus": focus_result}


def scan_knowledge(repo: Path, file: str | None = None) -> dict[str, Any]:
    paths = knowledge_paths(repo)
    focus = None
    if file:
        absolute = (repo / file).resolve() if not Path(file).is_absolute() else Path(file).resolve()
        try:
            focus = absolute.relative_to(repo)
        except ValueError as exc:
            raise ValueError("The file to organize must stay inside the repository.") from exc
        if not absolute.is_file():
            raise ValueError(f"File does not exist: {absolute}")
        if focus not in paths:
            paths.append(focus)
            paths.sort(key=lambda path: path.as_posix().lower())
    return update_source_map(repo, paths, focus)


def initialize(repo: Path, scan_sources: bool = False) -> dict[str, Any]:
    date = now().date().isoformat()
    root = repo / MEMORY
    should_scan = scan_sources or not (root / "source-map.md").exists()
    discovered = knowledge_paths(repo) if should_scan else []
    for relative in ("decisions", "research", "ideas", "plans/active", "plans/completed", "sessions"):
        (root / relative).mkdir(parents=True, exist_ok=True)
    (repo / RAW).mkdir(parents=True, exist_ok=True)
    templates = {
        root / "README.md": """# Project Memory

Repository-native, distilled project knowledge maintained by Chat2Codex.

Start with `current-state.md`, then read `principles.md` and relevant accepted decisions. Ideas are not requirements; session files are provenance, not default context.
""",
        root / "current-state.md": f"""# Current State

Last updated: {date}

## Product / Project Definition

_Not established yet._

## Current Phase

_Not established yet._

## Current Priorities

_Not established yet._

## Current Architecture

_Not established yet._

## Confirmed Constraints

_None recorded._

## Not Doing Now

_None recorded._

## Next Important Steps

_Not established yet._
""",
        root / "principles.md": "# Project Principles\n\n_None recorded._\n",
        root / "open-questions.md": "# Open Questions\n\n_None recorded._\n",
        root / "inbox.md": "# Memory Inbox\n\n| Added | URL | Status | Note |\n|---|---|---|---|\n",
        root / "processing-log.md": "# Processing Log\n",
        root / "source-map.md": source_map_template(),
        repo / REGISTRY: '{\n  "version": 1,\n  "sources": {}\n}\n',
    }
    created, preserved = [], []
    for path, content in templates.items():
        (created if create_once(path, content) else preserved).append(path.relative_to(repo).as_posix())

    agents = repo / "AGENTS.md"
    block = f"""{AGENTS_MARKER}
## Project Memory

Before non-trivial product or architecture work, read:

1. `docs/project-memory/current-state.md`
2. `docs/project-memory/principles.md`
3. `docs/project-memory/source-map.md` and its relevant canonical sources
4. relevant accepted decisions in `docs/project-memory/decisions/`

For current execution work, read `docs/project-memory/plans/active/`.

Ideas are not requirements. Read historical sessions only when provenance or deeper context is needed.
<!-- chat2codex-memory:end -->
"""
    if not agents.exists():
        atomic_write(agents, block)
        created.append("AGENTS.md")
    else:
        text = agents.read_text(encoding="utf-8")
        if AGENTS_MARKER not in text:
            atomic_write(agents, text.rstrip() + "\n\n" + block)
            created.append("AGENTS.md#Project-Memory")
        else:
            preserved.append("AGENTS.md#Project-Memory")

    gitignore = repo / ".gitignore"
    ignore = ".project-memory/raw/"
    old = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if ignore not in {line.strip() for line in old.splitlines()}:
        atomic_write(gitignore, old.rstrip() + ("\n" if old.strip() else "") + ignore + "\n")
        created.append(".gitignore#project-memory-raw")
    else:
        preserved.append(".gitignore#project-memory-raw")
    result: dict[str, Any] = {"created": created, "preserved": preserved}
    if should_scan:
        result["knowledge_scan"] = update_source_map(repo, discovered)
    return result


def share_id(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or parsed.hostname not in {"chatgpt.com", "www.chatgpt.com", "chat.openai.com"}:
        raise ValueError("Expected an HTTPS ChatGPT shared URL.")
    match = re.fullmatch(r"/share/([A-Za-z0-9-]+?)/?", parsed.path)
    if not match:
        raise ValueError("Expected a URL shaped like https://chatgpt.com/share/<id>.")
    return match.group(1)


URL_PATTERN = re.compile(r"https?://[^\s<>\[\]()\"']+")


def validate_share_url(text: str) -> dict[str, Any]:
    """Extract and validate one ChatGPT share URL without accessing the network."""
    candidates = []
    for match in URL_PATTERN.finditer(text):
        candidate = match.group(0).rstrip(".,;:!?")
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    chatgpt_urls = [
        candidate for candidate in candidates
        if urlparse(candidate).hostname in {"chatgpt.com", "www.chatgpt.com", "chat.openai.com"}
    ]
    if len(chatgpt_urls) != 1:
        return {
            "status": "invalid_share_url",
            "reason": "missing_or_ambiguous_chatgpt_url",
            "message": "Provide exactly one ChatGPT shared link shaped like https://chatgpt.com/share/<id>.",
        }

    url = chatgpt_urls[0]
    try:
        identifier = share_id(url)
    except ValueError:
        return {
            "status": "invalid_share_url",
            "reason": "not_a_share_url",
            "message": "A normal ChatGPT session URL is not importable. Provide https://chatgpt.com/share/<id>.",
        }
    return {
        "status": "valid_share_url",
        "url": f"https://chatgpt.com/share/{identifier}",
        "share_id": identifier,
    }


class Scripts(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.values: list[str] = []
        self.active = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "script":
            self.active, self.parts = True, []

    def handle_data(self, data: str) -> None:
        if self.active:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self.active:
            self.values.append("".join(self.parts))
            self.active = False


def fetch(url: str) -> tuple[str, str]:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 Chat2Codex/1.0", "Accept": "application/json,text/html"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace"), response.headers.get("Content-Type", "")


def walk(value: Any) -> Iterable[Any]:
    """Traverse decoded payloads without following shared or circular references twice."""
    seen: set[int] = set()

    def visit(current: Any) -> Iterable[Any]:
        if isinstance(current, (dict, list)):
            identifier = id(current)
            if identifier in seen:
                return
            seen.add(identifier)
        yield current
        if isinstance(current, dict):
            for child in current.values():
                yield from visit(child)
        elif isinstance(current, list):
            for child in current:
                yield from visit(child)

    yield from visit(value)


def text_of(message: dict[str, Any]) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, dict):
        parts = content.get("parts", content.get("text", ""))
        if isinstance(parts, list):
            return "\n".join(str(part) for part in parts if isinstance(part, (str, int, float))).strip()
        if isinstance(parts, str):
            return parts.strip()
    return ""


def messages_of(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(candidate.get("messages"), list):
        result = []
        for index, item in enumerate(candidate["messages"]):
            if not isinstance(item, dict):
                continue
            author = item.get("author", {})
            role = item.get("role") or (author.get("role") if isinstance(author, dict) else None)
            content = text_of(item)
            if role and content:
                result.append({"role": str(role), "content": content, "index": index})
        if result:
            return result
    mapping = candidate.get("mapping")
    if not isinstance(mapping, dict):
        return []
    current = candidate.get("current_node")
    if isinstance(current, str) and current in mapping:
        chain: list[dict[str, Any]] = []
        seen: set[str] = set()
        while isinstance(current, str) and current in mapping and current not in seen:
            seen.add(current)
            node = mapping[current]
            if not isinstance(node, dict):
                break
            chain.append(node)
            current = node.get("parent")
        result = []
        for index, node in enumerate(reversed(chain)):
            message = node.get("message")
            if not isinstance(message, dict):
                continue
            author = message.get("author", {})
            role = author.get("role") if isinstance(author, dict) else message.get("role")
            content = text_of(message)
            if role and content:
                result.append({"role": str(role), "content": content, "index": index})
        if result:
            return result
    sortable = []
    for order, node in enumerate(mapping.values()):
        message = node.get("message") if isinstance(node, dict) else None
        if not isinstance(message, dict):
            continue
        author = message.get("author", {})
        role = author.get("role") if isinstance(author, dict) else message.get("role")
        content = text_of(message)
        if role and content:
            stamp = message.get("create_time")
            sortable.append((stamp if isinstance(stamp, (int, float)) else float("inf"), order, role, content))
    sortable.sort(key=lambda value: (value[0], value[1]))
    return [{"role": str(role), "content": content, "index": index} for index, (_, _, role, content) in enumerate(sortable)]


def normalize(payload: Any, url: str) -> dict[str, Any] | None:
    for candidate in walk(payload):
        if isinstance(candidate, dict):
            messages = messages_of(candidate)
            if messages:
                return {
                    "title": str(candidate.get("title") or candidate.get("conversation_title") or "Shared ChatGPT session"),
                    "source_url": url,
                    "messages": messages,
                    "metadata": {},
                }
    return None


def javascript_call_arguments(script: str, token: str) -> Iterable[str]:
    """Yield JSON arguments passed to a known inline JavaScript call."""
    cursor = 0
    while (start := script.find(token, cursor)) >= 0:
        pos, depth, quoted, escaped = start + len(token), 0, False, False
        end = pos
        for end in range(pos, len(script)):
            char = script[end]
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char in "[{":
                depth += 1
            elif char in "]}":
                depth -= 1
            elif char == ")" and depth == 0:
                break
        yield script[pos:end]
        cursor = max(end + 1, pos + 1)


def unflatten_react_router_payload(value: Any) -> Any:
    """Restore React Router's compact table form without executing page JavaScript.

    Current share pages send loader data as a JSON array. Object keys such as
    ``_17`` point to the string at index 17, while integer values point to
    other table entries. This is a data-only reconstruction of that graph.
    """
    if not isinstance(value, list):
        return value
    unresolved = object()
    restored: list[Any] = [unresolved] * len(value)

    def resolve_scalar(item: Any) -> Any:
        if isinstance(item, bool) or not isinstance(item, int):
            return item
        if item >= 0:
            return resolve(item)
        # These are the special numeric values used by devalue-style payloads.
        return {
            -1: None,
            -2: float("nan"),
            -3: float("inf"),
            -4: float("-inf"),
            -5: -0.0,
            -6: None,
        }.get(item, item)

    def resolve_inline(item: Any) -> Any:
        if isinstance(item, dict):
            result: dict[str, Any] = {}
            for key, child in item.items():
                if key.startswith("_") and key[1:].isdigit():
                    decoded_key = resolve(int(key[1:]))
                    if not isinstance(decoded_key, str):
                        raise ValueError("React Router object key is not a string")
                else:
                    decoded_key = key
                result[decoded_key] = resolve_inline(child)
            return result
        if isinstance(item, list):
            return [resolve_inline(child) for child in item]
        return resolve_scalar(item)

    def resolve(index: int) -> Any:
        if index < 0 or index >= len(value):
            raise ValueError(f"React Router reference is out of range: {index}")
        if restored[index] is not unresolved:
            return restored[index]
        raw = value[index]
        if isinstance(raw, dict):
            result: dict[str, Any] = {}
            restored[index] = result
            for key, child in raw.items():
                if key.startswith("_") and key[1:].isdigit():
                    decoded_key = resolve(int(key[1:]))
                    if not isinstance(decoded_key, str):
                        raise ValueError("React Router object key is not a string")
                else:
                    decoded_key = key
                result[decoded_key] = resolve_inline(child)
            return result
        if isinstance(raw, list):
            result: list[Any] = []
            restored[index] = result
            result.extend(resolve_inline(child) for child in raw)
            return result
        restored[index] = raw
        return raw

    return resolve(0)


def react_router_payloads(scripts: Iterable[str]) -> Iterable[Any]:
    """Extract data-only React Router stream frames from share-page scripts."""
    token = "window.__reactRouterContext.streamController.enqueue("
    for script in scripts:
        for argument in javascript_call_arguments(script, token):
            try:
                frame = json.loads(argument)
            except json.JSONDecodeError:
                continue
            if not isinstance(frame, str):
                continue
            try:
                packed = json.loads(frame)
            except json.JSONDecodeError:
                # Deferred turbo-stream frames (for example, P123:...) are
                # not needed to recover an already-rendered conversation.
                continue
            try:
                yield unflatten_react_router_payload(packed)
            except (TypeError, ValueError):
                continue


def html_payloads(source: str) -> Iterable[Any]:
    collector = Scripts()
    collector.feed(source)
    yield from react_router_payloads(collector.values)
    for script in collector.values:
        stripped = script.strip()
        if stripped.startswith(("{", "[")):
            try:
                yield json.loads(stripped)
            except json.JSONDecodeError:
                pass
        for argument in javascript_call_arguments(script, "self.__next_f.push("):
            try:
                pushed = json.loads(argument)
                yield pushed
                if isinstance(pushed, list) and len(pushed) > 1 and isinstance(pushed[1], str):
                    embedded = pushed[1].strip()
                    if embedded.startswith(("{", "[")):
                        try:
                            yield json.loads(embedded)
                        except json.JSONDecodeError:
                            pass
            except json.JSONDecodeError:
                pass


def read_chatgpt_share(url: str) -> dict[str, Any]:
    identifier = share_id(url)
    endpoints = [f"https://chatgpt.com/backend-api/share/{identifier}", f"https://chat.openai.com/backend-api/share/{identifier}", url]
    errors = []
    for endpoint in endpoints:
        try:
            source, content_type = fetch(endpoint)
        except (HTTPError, URLError, TimeoutError) as exc:
            errors.append(f"{endpoint}: {exc}")
            continue
        payloads: list[Any] = []
        if "json" in content_type or source.lstrip().startswith(("{", "[")):
            try:
                payloads.append(json.loads(source))
            except json.JSONDecodeError:
                pass
        payloads.extend(html_payloads(source))
        for payload in payloads:
            result = normalize(payload, url)
            if result:
                return result
        errors.append(f"{endpoint}: conversation data not found")
    raise RuntimeError("Unable to parse the shared conversation. " + " | ".join(errors[-2:]))


def normalized_input(path: str, url: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    result = normalize(payload, url)
    if not result:
        raise ValueError("Normalized input contains no readable messages.")
    result["metadata"] = payload.get("metadata", {}) if isinstance(payload, dict) else {}
    return result


def digest(conversation: dict[str, Any]) -> str:
    stable = {"title": conversation["title"], "source_url": conversation["source_url"], "messages": [
        {"role": item["role"], "content": item["content"]} for item in conversation["messages"]
    ]}
    data = json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(data).hexdigest()


def load_registry(repo: Path) -> dict[str, Any]:
    path = repo / REGISTRY
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid registry JSON at {path}: {exc}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("sources"), dict):
        raise ValueError(f"Invalid registry structure at {path}")
    return value


def inbox(repo: Path, url: str, status: str | None, note: str = "") -> None:
    path = repo / MEMORY / "inbox.md"
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if f"| {url} |" not in line]
    if status:
        clean = note.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {now().strftime('%Y-%m-%d %H:%M')} | {url} | {status} | {clean} |")
    atomic_write(path, "\n".join(lines).rstrip() + "\n")


def bullets(value: Any) -> str:
    return "\n".join(f"- {item}" for item in value) if isinstance(value, list) and value else "- None"


def log(repo: Path, url: str, title: str, status: str, report: dict[str, Any] | None = None, reason: str = "") -> None:
    path = repo / MEMORY / "processing-log.md"
    old = path.read_text(encoding="utf-8").rstrip()
    parts = [f"## {now().strftime('%Y-%m-%d %H:%M')}", "", "Source:", url, "", "Session:", title, "", "Status:", status]
    if reason:
        parts += ["", "Reason:", reason]
    else:
        report = report or {}
        for label, key in (("Main topics", "main_topics"), ("Created", "created"), ("Updated", "updated"),
                           ("Confirmed existing", "confirmed_existing"), ("Conflicts", "conflicts"), ("Notes", "notes")):
            parts += ["", f"{label}:", bullets(report.get(key))]
    atomic_write(path, old + "\n\n" + "\n".join(parts) + "\n")


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    repo = repo_root(args.repo)
    share_id(args.url)
    try:
        conversation = normalized_input(args.input, args.url) if args.input else read_chatgpt_share(args.url)
    except Exception as exc:
        if args.input:
            raise
        return {
            "status": "browser_fallback_required",
            "url": args.url,
            "error": str(exc).replace("\n", " "),
            "browser_fallback": {
                "requires_confirmation": True,
                "instruction": "Ask the user before opening the public shared link in a browser to read it.",
            },
        }

    initialize(repo)
    inbox(repo, args.url, "processing")
    try:
        content_hash = digest(conversation)
        prior = load_registry(repo)["sources"].get(args.url)
        if isinstance(prior, dict) and prior.get("status") == "processed" and prior.get("content_hash") == content_hash:
            inbox(repo, args.url, None)
            log(repo, args.url, conversation["title"], "SUCCESS", {"notes": ["Already processed; content unchanged."]})
            return {"status": "already_processed", "title": conversation["title"], "content_hash": content_hash}
        raw_path = repo / RAW / (content_hash.split(":", 1)[1] + ".json")
        serialized = json.dumps(conversation, ensure_ascii=False, indent=2) + "\n"
        atomic_write(raw_path, serialized)
        output = Path(args.output).resolve()
        atomic_write(output, serialized)
        inbox(repo, args.url, "pending", "Distillation and memory diff pending")
        return {"status": "ready", "title": conversation["title"], "content_hash": content_hash,
                "output": str(output), "raw_file": raw_path.relative_to(repo).as_posix(), "updated_snapshot": isinstance(prior, dict)}
    except Exception as exc:
        message = str(exc).replace("\n", " ")
        inbox(repo, args.url, "failed", message[:240])
        log(repo, args.url, "Unknown", "FAILED", reason=message)
        raise


def finalize(args: argparse.Namespace) -> dict[str, Any]:
    repo = repo_root(args.repo)
    initialize(repo)
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ValueError("Finalization report must be a JSON object.")
    session = (repo / args.session_file).resolve()
    try:
        relative = session.relative_to(repo)
    except ValueError as exc:
        raise ValueError("Session file must stay inside the repository.") from exc
    if not session.is_file():
        raise ValueError(f"Session file does not exist: {session}")
    registry = load_registry(repo)
    registry["sources"][args.url] = {"status": "processed", "processed_at": now().isoformat(timespec="seconds"),
        "content_hash": args.content_hash, "session_file": relative.as_posix(), "title": args.title}
    atomic_write(repo / REGISTRY, json.dumps(registry, ensure_ascii=False, indent=2) + "\n")
    inbox(repo, args.url, None)
    log(repo, args.url, args.title, "SUCCESS", report)
    return {"status": "processed", "session_file": relative.as_posix()}


def mark_failed(args: argparse.Namespace) -> dict[str, Any]:
    repo = repo_root(args.repo)
    initialize(repo)
    inbox(repo, args.url, "failed", args.reason[:240])
    log(repo, args.url, args.title or "Unknown", "FAILED", reason=args.reason)
    return {"status": "failed", "reason": args.reason}


def get_status(repo: Path) -> dict[str, Any]:
    initialize(repo)
    registry = load_registry(repo)
    lines = (repo / MEMORY / "inbox.md").read_text(encoding="utf-8").splitlines()
    return {"repository": str(repo), "processed_sources": len(registry["sources"]),
            "pending": sum("| pending |" in line or "| processing |" in line for line in lines),
            "failed": sum("| failed |" in line for line in lines)}


def build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Chat2Codex deterministic repository-memory helper")
    commands = root.add_subparsers(dest="command", required=True)
    command = commands.add_parser("init"); command.add_argument("--repo")
    command = commands.add_parser("scan"); command.add_argument("--repo"); command.add_argument("--file")
    command = commands.add_parser("prepare"); command.add_argument("--repo"); command.add_argument("--url", required=True)
    command.add_argument("--output", required=True); command.add_argument("--input")
    command = commands.add_parser("validate-share-url"); command.add_argument("--text", required=True)
    command = commands.add_parser("finalize"); command.add_argument("--repo"); command.add_argument("--url", required=True)
    command.add_argument("--title", required=True); command.add_argument("--content-hash", required=True)
    command.add_argument("--session-file", required=True); command.add_argument("--report", required=True)
    command = commands.add_parser("fail"); command.add_argument("--repo"); command.add_argument("--url", required=True)
    command.add_argument("--title"); command.add_argument("--reason", required=True)
    command = commands.add_parser("status"); command.add_argument("--repo")
    return root


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "init":
            result = {"status": "initialized", **initialize(repo_root(args.repo), scan_sources=True)}
        elif args.command == "scan":
            target = repo_root(args.repo)
            initialize(target)
            result = {"status": "scanned", **scan_knowledge(target, args.file)}
        elif args.command == "prepare":
            result = prepare(args)
        elif args.command == "validate-share-url":
            result = validate_share_url(args.text)
        elif args.command == "finalize":
            result = finalize(args)
        elif args.command == "fail":
            result = mark_failed(args)
        else:
            result = get_status(repo_root(args.repo))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
