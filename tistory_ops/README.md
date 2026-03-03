# Tistory Ops

Tistory automation for `seoulmna.tistory.com`, fully isolated from legacy pipelines.

## Scope
- Listing-driven post generation with table format
- Browser automation publish (primary)
- Daily sequential publish (1/day) from Google Sheet
- Tistory API publish/list/category/info operations (legacy/diagnostic)
- Isolation verification against legacy entrypoints

## Important
- Tistory Open API is deprecated and unreliable for production automation.
- Use `publish-listing` (browser automation) as the default path.
- Duplicate guard is digest-based: same registration + same content is skipped, changed content can be republished.
- Content policy: source text is removed from body, and internal listing link uses `https://seoulmna.co.kr/mna/{등록번호}`.
- Default image policy: auto-generate 2 summary images per listing unless overridden.

## Required `.env` keys
- `TISTORY_ACCESS_TOKEN`
- `TISTORY_BLOG_NAME` (example: `seoulmna`)
- Optional:
  - `TISTORY_DEFAULT_CATEGORY_ID`
  - `TISTORY_DEFAULT_VISIBILITY` (`3` recommended)
  - `TISTORY_DEFAULT_TAGS`
  - `TISTORY_APP_ID`
  - `TISTORY_APP_SECRET`
  - `TISTORY_REDIRECT_URI`
  - `TISTORY_LOGIN_ID` / `TISTORY_LOGIN_PASSWORD` (optional, for auto-login)
  - `TISTORY_AUTO_LOGIN` (`1` to enable auto-login by default)
  - `TISTORY_ALLOWED_BLOG_DOMAINS` (safety allow-list)
  - `TISTORY_CHROME_DEBUGGER` (optional; leave empty to use direct browser session by default)

## Quick commands
0. One-click launcher (Windows)
```bash
티스토리자동발행.bat 7540
```
```bash
티스토리자동발행.bat
# 인자 없으면 daily-once(1일 1건 순차) 모드
```

1. Verify split
```bash
py -3 tistory_ops/run.py verify-split --out logs/tistory_split_verify_latest.json
```

2. Preview listing post HTML (no publish)
```bash
py -3 tistory_ops/run.py publish-listing --registration 7540 --dry-run --out-html output/tistory_7540.html --print-payload
```

2-1. Daily one-shot publish (sheet sequence, start 7540)
```bash
py -3 tistory_ops/run.py daily-once --start-registration 7540
```

2-2. Startup task registration (Windows Task Scheduler, at logon)
```bash
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/register_tistory_daily_startup_task.ps1
```
```bash
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/unregister_tistory_daily_startup_task.ps1
```
로그온 작업은 기본적으로 `--no-interactive-login`으로 실행되어, 숨김 세션에서 대기하지 않고 자동로그인만 시도합니다.

3. Browser automation publish (primary)
```bash
py -3 tistory_ops/run.py publish-listing --registration 7540 --interactive-login --open-browser
```
로그인 대기 시간을 늘리고 싶으면:
```bash
py -3 tistory_ops/run.py publish-listing --registration 7540 --interactive-login --login-wait-sec 300 --open-browser
```
임시저장 복구 팝업 정책:
```bash
# 기본: 기존 임시저장 버리고 새 글 작성
py -3 tistory_ops/run.py publish-listing --registration 7540 --open-browser --draft-policy discard

# 임시저장 이어쓰기
py -3 tistory_ops/run.py publish-listing --registration 7540 --open-browser --draft-policy resume
```

자동 로그인 시도 후 실패 시 수동 로그인 대기:
```bash
py -3 tistory_ops/run.py publish-listing --registration 7540 --open-browser --auto-login --interactive-login
```

3-1. Republish policy control
```bash
# default: changed content is allowed to republish
py -3 tistory_ops/run.py publish-listing --registration 7540 --open-browser

# block republish even if content changed
py -3 tistory_ops/run.py publish-listing --registration 7540 --open-browser --no-republish-changed
```

4. Attach existing logged-in Chrome session (recommended)
```bash
chrome.exe --remote-debugging-port=9222
py -3 tistory_ops/run.py publish-listing --registration 7540 --debugger 127.0.0.1:9222 --open-browser
```

4-1. Domain safety gate override (optional)
```bash
py -3 tistory_ops/run.py publish-listing --registration 7540 --open-browser --allowed-blog-domain seoulmna.tistory.com
```

5. API diagnostics (legacy)
```bash
py -3 tistory_ops/run.py categories-api
py -3 tistory_ops/run.py publish-listing-api --registration 7540 --dry-run
```

6. OAuth helper
```bash
py -3 tistory_ops/run.py oauth authorize-url
py -3 tistory_ops/run.py oauth exchange-code --code "<auth_code>"
```
