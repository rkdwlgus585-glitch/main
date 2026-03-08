# Zero Touch Automation (Monthly Goal: 200,000 KRW)

## What this does
- Runs `autopilot.py` (fast refresh by default).
- Creates an outreach dispatch batch from `sales_activity_latest.csv`.
- Optionally posts outreach payload to a webhook.
- Auto-updates selected lead statuses (`new -> contacted` by default).
- Computes a monthly revenue floor report for the goal amount.

## Run once
```bat
zero_touch.bat
```

## Run directly
```bat
py zero_touch_revenue.py --monthly-goal 200000 --continue-on-error
```

## Scheduler (daily)
```bat
schedule_zero_touch.bat
```

## Optional webhook dispatch
Set one of:
- `OUTREACH_WEBHOOK_URL` environment variable
- `WEBHOOK_URL` in `config.txt`

Then `zero_touch_revenue.py` will post `result/outreach_payload_latest.json` content to that endpoint.

## Main outputs
- `result/outreach_batch_latest.csv`
- `result/outreach_payload_latest.json`
- `result/revenue_floor_latest.json`
- `result/revenue_floor_latest.md`
- `result/zero_touch_ops_latest.md`

## Important limitation
This automation can generate and dispatch payloads, but real-world closing still requires a connected execution channel (for example, webhook target, call center, or sales agency workflow) to act on dispatched leads.
