# Contributing

Thanks for helping improve Chat2Codex Memory Mule.

## Principles

- Keep the installable skill small and repository-native.
- Prefer links and distilled knowledge over copied documents or transcripts.
- Preserve epistemic status: ideas are not decisions, and research is not project state.
- Never silently resolve conflicts or overwrite canonical project documentation.
- Keep deterministic behavior in the Python helper and semantic judgment in the skill workflow.
- Avoid dependencies unless they provide a clear reliability benefit.

## Development workflow

1. Create a focused branch.
2. Update the skill, reference model, helper, or tests as needed.
3. Run `python -m unittest discover -s tests -v`.
4. Run Codex's `quick_validate.py` against `chat2codex-memory-mule/` when available.
5. Verify that no shared transcripts, credentials, tokens, or generated project memory are staged.
6. Open a pull request explaining behavior changes and compatibility impact.

## Reporting security issues

Do not open a public issue containing secrets, private shared links, personal data, or unpublished transcripts. Contact the repository owner privately through an appropriate GitHub channel until a dedicated security policy is configured.
