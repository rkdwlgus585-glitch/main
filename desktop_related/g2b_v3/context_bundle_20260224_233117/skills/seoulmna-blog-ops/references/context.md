# Blog Ops Context Matrix

## Required for Publish
- `GEMINI_API_KEY`
- `WP_URL`
- WordPress auth: `WP_JWT_TOKEN` or `WP_USER` + `WP_APP_PASSWORD`

## Required for Scheduler
- Same as publish
- Writable lock and state files
- Stable runtime environment (no sleep)

## Optional OpenAI Features
- Enable keyword rerank: `OPENAI_SCAN_ENABLED=true`
- Required key: `OPENAI_API_KEY`
- Optional embedding guard: `SEMANTIC_GUARD_ENABLED=true`

## Search Performance Inputs
- Enable data hub: `SEARCH_DATA_ENABLED=true`
- Preferred source: GSC API (`GSC_PROPERTY_URL`, `GSC_SERVICE_ACCOUNT_FILE`)
- Fallback source: CSV files (`search_console_queries.csv`, `naver_queries.csv`)
- Bootstrap and health check command: `python scripts/bootstrap_search_context.py --check-gsc`
- If GSC API is disabled at project level, keep CSV files populated from exported data.

## Recommended Command Sequence
1. `python mnakr.py --schedule-check`
2. `python mnakr.py --wp-check`
3. `python mnakr.py --cli`
4. `python mnakr.py --scheduler`

