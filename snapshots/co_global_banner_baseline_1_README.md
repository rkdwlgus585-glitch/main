# co_global_banner Baseline-1 (Locked)

- Baseline name: `co_global_banner_baseline_1`
- Snapshot file: `snapshots/co_global_banner_baseline_1.html`
- Meta file: `snapshots/co_global_banner_baseline_1.meta.json`
- Policy: Rollback must always use Baseline-1 unless explicitly re-frozen.
- Test working file: `snapshots/co_global_banner_test_working.html`
- Rule: edit only `co_global_banner_test_working.html` during test cycle. Do not edit baseline directly.

## Standard Workflow (Test -> Fix -> Live)

1. Reset working file from baseline-1:

```bash
py -3 scripts/reset_co_banner_test_working.py
```

2. Start private test preview (localhost-only, real-site proxy + working snippet injection):

```bash
py -3 scripts/build_co_banner_private_preview.py --port 18778
```

3. Iterate edits on `snapshots/co_global_banner_test_working.html` and refresh preview:
- `http://127.0.0.1:18778/`
- `http://127.0.0.1:18778/notice`

4. Promote tested result to live co.kr only after final confirmation:

```bash
py -3 scripts/promote_co_banner_test_to_live.py --confirm-live YES
```

## Rollback Command (Live)

```bash
py -3 scripts/rollback_co_global_banner_baseline1.py --confirm-live YES
```

Optional:

```bash
py -3 scripts/rollback_co_global_banner_baseline1.py --base-url https://seoulmna.co.kr --confirm-live YES --report logs/co_global_banner_rollback_baseline1_latest.json
```

## Private Local Preview (No live apply)

This preview is now a localhost reverse-proxy of the real site with test working snippet injected into HTML only.
So layout/DOM is effectively identical to the live site.

```bash
py -3 scripts/build_co_banner_private_preview.py --port 18778
```

Preview URL:
- `http://127.0.0.1:18778/`
- `http://127.0.0.1:18778/notice`
