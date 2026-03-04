import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


ROOT = Path(__file__).resolve().parents[1]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env_map(path: Path):
    out = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _safe_account(raw: str) -> str:
    src = "".join(str(raw or "").strip().lower().split())
    out = "".join(ch for ch in src if ch.isalnum() or ch in "._@-")
    return (out or "member")[:80]


def _safe_rows(rows, limit: int):
    out = []
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        url = str(row.get("url", "")).strip()
        if not url:
            continue
        title = " ".join(str(row.get("title", "")).split()).strip()
        ts = int(row.get("ts", 0) or 0)
        out.append({"url": url, "title": (title or f"listing {url.rstrip('/').split('/')[-1]}")[:80], "ts": ts})
        if len(out) >= limit:
            break
    return out


def _merge_rows(local_rows, browser_rows, limit: int):
    seen = {}
    merged = []
    for src in (browser_rows, local_rows):
        for row in _safe_rows(src, limit * 3):
            key = row["url"]
            prev = seen.get(key)
            if prev is None or int(row.get("ts", 0)) > int(prev.get("ts", 0)):
                seen[key] = row
    merged = list(seen.values())
    merged.sort(key=lambda x: int(x.get("ts", 0)), reverse=True)
    return merged[:limit]


def _load_db(path: Path):
    if not path.exists():
        return {"updated_at": _now_iso(), "accounts": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {"updated_at": _now_iso(), "accounts": {}}


def _save_db(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _login(driver, base_url: str, login_id: str, login_pw: str):
    driver.get(base_url.rstrip("/") + "/bbs/login.php?url=%2Fmna")
    id_box = driver.find_element(By.NAME, "mb_id")
    pw_box = driver.find_element(By.NAME, "mb_password")
    id_box.clear()
    id_box.send_keys(login_id)
    pw_box.clear()
    pw_box.send_keys(login_pw)
    form = driver.find_element(By.CSS_SELECTOR, "form[action*='login_check.php'], form[name='flogin']")
    form.submit()


def _read_browser_state(driver, account: str):
    script = """
      var account = arguments[0];
      var favKey = 'smna_favorite_mna_v2::' + account;
      function parse(v){ try { return JSON.parse(v||'[]'); } catch(_e){ return []; } }
      return {
        last_login_id: localStorage.getItem('smna_last_login_id') || '',
        favorites: parse(localStorage.getItem(favKey)),
        recent: parse(localStorage.getItem('smna_recent_mna_v1'))
      };
    """
    return driver.execute_script(script, account)


def _write_browser_state(driver, account: str, favorites, recent):
    script = """
      var account = arguments[0];
      var favorites = arguments[1] || [];
      var recent = arguments[2] || [];
      localStorage.setItem('smna_last_login_id', account);
      localStorage.setItem('smna_favorite_mna_v2::' + account, JSON.stringify(favorites));
      localStorage.setItem('smna_recent_mna_v1', JSON.stringify(recent));
    """
    driver.execute_script(script, account, favorites, recent)


def main():
    ap = argparse.ArgumentParser(description="Sync MNA favorite/recent state between browser and local AUTO json")
    ap.add_argument("--mode", choices=["pull", "push", "merge"], default="merge")
    ap.add_argument("--site-url", default="https://seoulmna.co.kr")
    ap.add_argument("--data-file", default="logs/local_auto_state.json")
    ap.add_argument("--account", default="")
    ap.add_argument("--login-id", default="")
    ap.add_argument("--login-pw", default="")
    ap.add_argument("--headless", action="store_true")
    args = ap.parse_args()

    env = _env_map(ROOT / ".env")
    login_id = str(args.login_id or env.get("ADMIN_ID", "")).strip()
    login_pw = str(args.login_pw or env.get("ADMIN_PW", "")).strip()
    if not login_id or not login_pw:
        raise SystemExit("login credentials missing (ADMIN_ID/ADMIN_PW)")
    account = _safe_account(args.account or login_id)
    data_file = (ROOT / args.data_file).resolve()

    db = _load_db(data_file)
    account_row = (db.get("accounts") or {}).get(account) or {}
    local_favorites = _safe_rows(account_row.get("favorites", []), 20)
    local_recent = _safe_rows(account_row.get("recent", []), 10)

    options = Options()
    if args.headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    with webdriver.Chrome(options=options) as driver:
        driver.set_window_size(1366, 900)
        _login(driver, args.site_url, login_id, login_pw)
        driver.get(args.site_url.rstrip("/") + "/mna")
        browser = _read_browser_state(driver, account)
        browser_favorites = _safe_rows(browser.get("favorites", []), 20)
        browser_recent = _safe_rows(browser.get("recent", []), 10)
        if args.mode == "push":
            final_favorites = local_favorites
            final_recent = local_recent
            _write_browser_state(driver, account, final_favorites, final_recent)
        elif args.mode == "merge":
            final_favorites = _merge_rows(local_favorites, browser_favorites, 20)
            final_recent = _merge_rows(local_recent, browser_recent, 10)
            _write_browser_state(driver, account, final_favorites, final_recent)
        else:
            final_favorites = browser_favorites
            final_recent = browser_recent

    now = _now_iso()
    db["updated_at"] = now

    db.setdefault("accounts", {})[account] = {
        "favorites": final_favorites,
        "recent": final_recent,
        "updated_at": now,
    }
    _save_db(data_file, db)
    print(json.dumps({
        "ok": True,
        "mode": args.mode,
        "account": account,
        "favorites": len(final_favorites),
        "recent": len(final_recent),
        "data_file": str(data_file),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
