# Security Policy

## Supported versions

Security fixes are applied to the latest release and the current `main` branch. Older releases may not receive backported fixes.

## Reporting a vulnerability

Please do not report vulnerabilities, credentials, private ChatGPT links, personal data, or unpublished conversation transcripts in a public issue.

Use GitHub's private vulnerability reporting feature from the repository's **Security** tab when it is available. If private vulnerability reporting is unavailable, contact the maintainer through a private contact method listed on their GitHub profile. Include only the information needed to reproduce and assess the issue.

A useful report includes:

- the affected version or commit;
- the operating system and Python version;
- a concise description of the impact;
- minimal reproduction steps or a proof of concept using synthetic data;
- any suggested mitigation, if known.

Do not include real secrets, private shared links, or raw transcripts. Replace sensitive values with safe placeholders.

The maintainer will make a best effort to acknowledge a report within seven days, confirm the impact, and coordinate a fix and disclosure timeline. Please allow reasonable time for a fix before publishing technical details.

## Security scope

Reports are especially helpful when they involve:

- unintended disclosure or tracking of raw conversation data;
- writing files outside the selected repository or documented output path;
- bypassing public-share URL validation or browser-confirmation boundaries;
- unsafe handling of repository files, registry state, or generated Markdown;
- dependency, workflow, or release-process weaknesses that could compromise users.

The parser's inability to read a changed or unsupported public ChatGPT share-page format is normally a compatibility bug, not a security vulnerability, unless it crosses a security boundary or exposes data.
