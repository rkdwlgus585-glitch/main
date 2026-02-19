# CLAUDE.md

This file provides guidance for AI assistants (Claude and others) working in this repository.

## Repository Overview

**Repository:** `rkdwlgus585-glitch/main`
**Status:** Claude Chat app — Next.js chatbot with streaming, multi-turn, and conversation history.

**Tech stack:** Next.js 15, TypeScript, Tailwind CSS, Anthropic SDK

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

Copy `.env.example` to `.env.local` and fill in your values:

```bash
cp .env.example .env.local
```

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | **Yes** | Anthropic API 키. [console.anthropic.com](https://console.anthropic.com/) 에서 발급 |
| `NTFY_TOPIC` | No | ntfy.sh 알림 토픽. Subscribe at `https://ntfy.sh/<topic>` |
| `NTFY_SERVER` | No | Custom ntfy 서버 URL (기본값: `https://ntfy.sh`) |

> Never commit `.env.local` to version control.

### 로컬 개발 서버 실행

```bash
npm run dev
# → http://localhost:3000
```

### 프로덕션 빌드

```bash
npm run build
npm start
```

### Notifications (`scripts/notify.sh`)

```bash
export NTFY_TOPIC=my-project-alerts
./scripts/notify.sh "배포 완료"
./scripts/notify.sh "테스트 실패" "CI Alert" "high"
```

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
├── app/
│   ├── api/chat/route.ts    # Anthropic streaming API endpoint
│   ├── layout.tsx           # Root layout
│   ├── page.tsx             # Entry point → ChatInterface
│   └── globals.css
├── components/
│   ├── ChatInterface.tsx    # 메인 채팅 UI (상태 관리)
│   ├── Sidebar.tsx          # 대화 목록 사이드바
│   ├── MessageList.tsx      # 메시지 렌더링
│   ├── MessageInput.tsx     # 입력창 + 전송 버튼
│   └── ModelSelector.tsx    # 모델 선택 드롭다운
├── hooks/
│   └── useConversations.ts  # 대화 CRUD + localStorage 영속화
├── types/
│   └── index.ts             # TypeScript 타입 정의 + 모델 목록
├── scripts/
│   └── notify.sh            # ntfy.sh 알림 헬퍼
├── .env.example             # 환경변수 템플릿
└── CLAUDE.md                # This file
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

*Last updated: 2026-02-19 — added Claude Chat Next.js app with streaming, multi-turn conversations, and model selection. Update this file whenever the project structure, tooling, or conventions change.*
