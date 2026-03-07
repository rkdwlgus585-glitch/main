# SeoulMNA KR Platform Front

This Next.js app is the planned public platform front for `seoulmna.kr`.

## Topology
- Main public platform: `seoulmna.kr`
- Listing market site: `seoulmna.co.kr`
- Public calculator mount: `https://seoulmna.kr/_calc/*`
- Private engine host: hidden origin only

## Routes
- `/`: platform landing page
- `/yangdo`: public entry for the AI transfer-price estimator
- `/permit`: public entry for the AI permit precheck
- `/widget/yangdo`: same-domain full-screen widget stage
- `/widget/permit`: same-domain full-screen widget stage

## Traffic Gate
- Public entry pages do not create widget iframe traffic on first render.
- The external engine iframe is created only after an explicit launch click.
- Widget routes remain `noindex` to reduce crawler-triggered engine traffic.
- Validation script:
  - `py -3 ..\\..\\..\\scripts\\validate_kr_traffic_gate.py`

## Environment
- `NEXT_PUBLIC_PLATFORM_FRONT_HOST`
- `NEXT_PUBLIC_LISTING_HOST`
- `NEXT_PUBLIC_CALCULATOR_MOUNT_BASE`
- `NEXT_PUBLIC_PRIVATE_ENGINE_ORIGIN`
- `NEXT_PUBLIC_CONTACT_PHONE`
- `NEXT_PUBLIC_CONTACT_EMAIL`
- `NEXT_PUBLIC_TENANT_ID`

## Build Status
- `npm.cmd run build`: verified on 2026-03-06

## Deploy Direction
- Preferred host: `seoulmna.kr`
- Deploy target: Vercel
- `seoulmna.co.kr` remains the listing market site during transition
- The engine host is not a public-facing brand surface; public calculator traffic should stay under `/_calc/*`

## Config Sync
- Generate front env from channel config:
  - `py -3 ..\\..\\..\\scripts\\sync_kr_platform_front_env.py`
