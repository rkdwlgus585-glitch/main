# WordPress Surface Lab Runtime

- Purpose: run the isolated Astra/WordPress lab locally without sending public traffic to `seoulmna.kr`.
- Exposure policy: the lab binds only to `127.0.0.1`, so it is not reachable from the public internet.
- Runtime target: validate the `seoulmna-platform-child` theme, `seoulmna-platform-bridge` plugin, Gutenberg blueprints, and the `/_calc/*` lazy-gate behavior before any live change.

## Files
- `docker-compose.yml`: local-only runtime with WordPress, MariaDB, and WP-CLI.
- `.env.local`: safe default local values for internal testing.
- `.env.example`: template for resetting the lab.

## Runtime Modes
1. Docker runtime
   - `http://127.0.0.1:18080`
2. PHP fallback runtime
   - `http://127.0.0.1:18081`

## Start
1. Install Docker Desktop.
2. From this directory, run:
   - `docker compose --env-file .env.local up -d`
3. Open:
   - `http://127.0.0.1:18080/wp-admin/`

## PHP Fallback
- The PHP fallback path is the active local verification lane when Docker is unavailable.
- Start it with the generated PowerShell script under `php_fallback/`.
- Use `http://127.0.0.1:18081/wp-admin/`.

## Bootstrap
Run the following commands after the containers are healthy:
- `docker compose --env-file .env.local run --rm wpcli core install --url="$WP_SITE_URL" --title="$WP_SITE_TITLE" --admin_user="$WP_ADMIN_USER" --admin_password="$WP_ADMIN_PASSWORD" --admin_email="$WP_ADMIN_EMAIL" --skip-email`
- `docker compose --env-file .env.local run --rm wpcli theme activate seoulmna-platform-child`
- `docker compose --env-file .env.local run --rm wpcli plugin activate seoulmna-platform-bridge`

## Verify
- Homepage `/` renders CTA-only without creating calculator iframes on first load.
- `/yangdo` and `/permit` render lazy calculator gates and create iframes only after explicit click.
- `/knowledge` remains CTA-only.
- `/mna-market` routes to the listing site instead of embedding calculators.
