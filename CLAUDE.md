# CLAUDE.md

This file provides guidance for AI assistants (Claude and others) working in this repository.

## Repository Overview

**Repository:** `rkdwlgus585-glitch/main`
**Status:** Newly initialized — no application code exists yet.

The repository currently contains only a `.gitkeep` file. This CLAUDE.md will be updated as the codebase grows.

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

> This section will be populated once a tech stack is chosen.

When a language/framework is established, document here:
- Required runtime versions (Node, Python, Go, etc.)
- Dependency installation command
- Environment variable setup (`.env.example` to copy)
- Local server start command

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

> This section will be populated once directories are created.

As the codebase grows, document the top-level layout here:

```
/
├── src/          # Application source code
├── tests/        # Test files
├── docs/         # Documentation
└── CLAUDE.md     # This file
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

*Last updated: 2026-02-19. Update this file whenever the project structure, tooling, or conventions change.*
