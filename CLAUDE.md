# CLAUDE.md

This file provides guidance for AI assistants (Claude and others) working in this repository.

## Repository Overview

**Repository:** `rkdwlgus585-glitch/main`
**Status:** Initial setup — notification utility added.

Current contents:
- `scripts/notify.sh` — push notification helper via ntfy.sh
- `.env.example` — environment variable template

---

## Git Workflow

### Branch Naming

- Feature branches: `feature/<short-description>`
- Bug fix branches: `fix/<short-description>`
- Claude-managed branches: `claude/<task-description>-<session-id>`

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

[optional body]
```

Common types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

Examples:
```
feat(auth): add JWT login endpoint
fix(api): handle null response from upstream
docs: update README with setup instructions
```

### Push Workflow

Always specify the upstream branch explicitly:

```bash
git push -u origin <branch-name>
```

Never force-push to `master` or `main`.

---

## Development Setup

### Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `NTFY_TOPIC` | Yes | ntfy.sh topic name. Subscribe at `https://ntfy.sh/<topic>` |
| `NTFY_SERVER` | No | Custom ntfy server URL (default: `https://ntfy.sh`) |

> Never commit `.env` to version control.

### Notifications (`scripts/notify.sh`)

Send a push notification to your PC/phone via [ntfy.sh](https://ntfy.sh):

```bash
# Basic
export NTFY_TOPIC=my-project-alerts
./scripts/notify.sh "배포 완료"

# With title and priority (min|low|default|high|urgent)
./scripts/notify.sh "테스트 실패" "CI Alert" "high"
```

**Subscribe on your PC:** open `https://ntfy.sh/<NTFY_TOPIC>` in a browser and allow notifications, or install the [ntfy desktop app](https://docs.ntfy.sh/subscribe/phone/).

---

## Testing

> This section will be populated once a test framework is chosen.

When tests are added, document here:
- How to run the full test suite
- How to run a single test file
- How to run tests in watch mode
- Coverage report command

---

## Code Style & Linting

> This section will be populated once linting is configured.

When linting is set up, document here:
- Linter and formatter in use (ESLint, Prettier, Black, Ruff, etc.)
- Command to lint: e.g., `npm run lint`
- Command to auto-fix: e.g., `npm run lint:fix`
- Whether linting runs in CI and must pass before merge

---

## Project Structure

```
/
├── scripts/
│   └── notify.sh     # Push notification helper (ntfy.sh)
├── .env.example      # Environment variable template
└── CLAUDE.md         # This file
```

---

## Key Conventions for AI Assistants

### General

- **Read before editing.** Always read a file before modifying it.
- **Minimal changes.** Only change what is directly required by the task. Do not refactor surrounding code, add comments, or improve unrelated areas.
- **No new files unless necessary.** Prefer editing existing files. Do not create documentation, README files, or utilities beyond what the task requires.
- **No backwards-compatibility shims.** If something is removed or renamed, delete the old references completely.

### Security

- Never commit secrets, credentials, API keys, or `.env` files.
- Validate inputs at system boundaries (user input, external API responses).
- Avoid introducing OWASP Top 10 vulnerabilities (SQL injection, XSS, command injection, etc.).

### Pull Requests

- Keep PRs focused on a single concern.
- Ensure all tests pass before opening a PR.
- Write a clear PR description explaining *why*, not just *what*.

---

## CI/CD

> This section will be populated once CI is configured.

When a CI pipeline (GitHub Actions, etc.) is added, document here:
- What checks run on pull requests
- How to view CI logs
- How to re-run failed jobs

---

*Last updated: 2026-02-19 — added ntfy.sh notification setup. Update this file whenever the project structure, tooling, or conventions change.*
