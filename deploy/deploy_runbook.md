# seoulmna.kr Deployment Runbook

## Pre-deployment Checklist

- [ ] All tests pass: `python -m pytest tests/ -x -q`
- [ ] Smoke test passes locally: `python deploy/smoke_test.py`
- [ ] SSL certificates are in place: `/etc/ssl/seoulmna.kr/origin.pem`
- [ ] Config files exist: `tenant_config/`, `config/`
- [ ] Data/logs directories writable: `data/`, `logs/`

## Deployment Methods

### Method A: systemd (Recommended for single-server)

```bash
# 1. Upload code
rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='tests/' \
    . seoulmna@server:/opt/seoulmna/auto/

# 2. Install/update dependencies
ssh seoulmna@server 'cd /opt/seoulmna/auto && pip install -r requirements.txt'

# 3. Deploy systemd units (first time only)
sudo cp deploy/systemd/seoulmna-yangdo.service /etc/systemd/system/
sudo cp deploy/systemd/seoulmna-permit.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable seoulmna-yangdo seoulmna-permit

# 4. Restart services (zero-downtime with nginx upstream health checks)
sudo systemctl restart seoulmna-permit
sleep 5
python deploy/smoke_test.py --permit-url http://127.0.0.1:8100
sudo systemctl restart seoulmna-yangdo
sleep 5
python deploy/smoke_test.py --yangdo-url http://127.0.0.1:8200

# 5. Deploy nginx config
sudo cp deploy/nginx_seoulmna_kr.conf /etc/nginx/conf.d/seoulmna.kr.conf
sudo nginx -t && sudo systemctl reload nginx

# 6. Full smoke test
python deploy/smoke_test.py
```

### Method B: Docker Compose

```bash
# 1. Build and deploy
cd deploy/
docker compose build --no-cache
docker compose up -d

# 2. Wait for health checks
docker compose ps  # all services should be "healthy"

# 3. Smoke test
python deploy/smoke_test.py --wait 10
```

### Method C: Docker Compose (Rolling Update)

```bash
# 1. Build new images
docker compose build --no-cache

# 2. Rolling restart (one service at a time)
docker compose up -d --no-deps permit-api
sleep 10
docker compose up -d --no-deps yangdo-api
sleep 10
docker compose up -d --no-deps nginx

# 3. Verify
python deploy/smoke_test.py
```

## Rollback Procedure

### systemd Rollback

```bash
# 1. Keep previous version tagged
git tag -a "pre-deploy-$(date +%Y%m%d%H%M)" -m "Pre-deployment snapshot"

# 2. Rollback to previous code
git checkout <previous-commit-hash>

# 3. Restart services
sudo systemctl restart seoulmna-permit seoulmna-yangdo

# 4. Verify
python deploy/smoke_test.py
```

### Docker Rollback

```bash
# 1. List previous images
docker images | grep seoulmna

# 2. Rollback to previous image
docker compose down
git checkout <previous-commit-hash>
docker compose up -d

# 3. Verify
python deploy/smoke_test.py
```

## Health Check URLs

| Service | Health Endpoint | Expected |
|---------|----------------|----------|
| Permit API | `http://127.0.0.1:8100/v1/health` | `{"ok": true, ...}` |
| Yangdo API | `http://127.0.0.1:8200/v1/health` | `{"ok": true, ...}` |
| nginx proxy | `https://seoulmna.kr/_calc/health` | Proxy to permit health |

## Monitoring

### Log locations (systemd)
```
journalctl -u seoulmna-permit -f
journalctl -u seoulmna-yangdo -f
/opt/seoulmna/auto/logs/security_permit_precheck_events.jsonl
/opt/seoulmna/auto/logs/security_yangdo_blackbox_events.jsonl
```

### Log locations (Docker)
```
docker compose logs -f permit-api
docker compose logs -f yangdo-api
```

### Key metrics to watch
- Response time: `/v1/health` should respond < 100ms
- Error rate: 5xx responses in nginx access log
- Memory usage: each API process should stay under 512MB
- Disk usage: `logs/` directory growth

## Troubleshooting

### Service won't start
```bash
# Check logs
journalctl -u seoulmna-permit -n 50 --no-pager
# Check port conflicts
ss -tlnp | grep -E '810[0-9]|820[0-9]'
# Check file permissions
ls -la /opt/seoulmna/auto/data/ /opt/seoulmna/auto/logs/
```

### 502 Bad Gateway from nginx
```bash
# Verify upstream is running
curl -s http://127.0.0.1:8100/v1/health | python -m json.tool
curl -s http://127.0.0.1:8200/v1/health | python -m json.tool
# Check nginx error log
tail -20 /var/log/nginx/error.log
```

### High memory usage
```bash
# Check process memory
ps aux | grep -E 'permit_precheck|yangdo_blackbox'
# Restart affected service
sudo systemctl restart seoulmna-permit
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SMNA_ENV` | `production` | Environment name |
| `PERMIT_PRECHECK_API_PORT` | `8792` | Permit API port |
| `PERMIT_PRECHECK_API_KEY` | `""` | API key for precheck |
| `PERMIT_PRECHECK_ADMIN_API_KEY` | `""` | Admin API key |
| `TENANT_GATEWAY_ENABLED` | `true` | Enable tenant gateway |
| `PYTHONUNBUFFERED` | `1` | Unbuffered Python output |
