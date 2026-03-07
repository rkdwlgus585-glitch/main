# WordPress Surface Lab

- Purpose: validate Astra and related WordPress assets inside an isolated lab before any live adoption.
- Live reality: seoulmna.kr is the current WordPress/Astra public site, seoulmna.co.kr is the internal unlimited widget consumer, and the private engine remains hidden behind consumer channels.
- Runtime policy: when PHP or Docker is missing, keep the lab in package extraction and static validation mode only.
- Runtime scaffold: run `scripts/scaffold_wp_surface_lab_runtime.py` to generate a local-only Docker compose runtime under `runtime/` before any live change.
- PHP fallback: run `scripts/prepare_wp_surface_lab_php_runtime.py` and `scripts/bootstrap_wp_surface_lab_php_fallback.py` to build a Docker-free local runtime using the official Windows PHP package and the official SQLite Database Integration plugin.
