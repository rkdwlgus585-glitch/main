#!/usr/bin/env python3
"""G2B API 정밀 진단 (운영 호출 규격 기준)."""

import argparse
import json
import os
import socket
import ssl
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://apis.data.go.kr/1230000/ao/OrderPlanSttusService"
EP_CANDIDATES = {
    "const": ["getOrderPlanSttusListCnstwk"],
    "serv": ["getOrderPlanSttusListServc", "getOrderPlanSttusListServce"],
}
LABELS = {"const": "공사", "serv": "용역"}


def load_config():
    cfg = {}
    cfg_path = Path(__file__).parent / "config.txt"
    for line in cfg_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    return cfg


def resolve_year(cfg):
    now = datetime.now().year
    raw = (cfg.get("YEAR", "") or "").strip()
    if not raw:
        return now
    try:
        year = int(raw)
    except ValueError:
        return now
    if year < 2000 or year > now + 2:
        return now
    return year


def build_profiles(year):
    return [
        {
            "name": "order_ym",
            "params": {
                "inqryDiv": "1",
                "orderBgnYm": f"{year}01",
                "orderEndYm": f"{year}12",
            },
        },
        {
            "name": "date_range",
            "params": {
                "inqryDiv": "1",
                "inqryBgnDt": f"{year}0101",
                "inqryEndDt": f"{year}1231",
            },
        },
        {"name": "minimal", "params": {}},
    ]


def make_url(endpoint, key, key_mode, profile):
    params = {
        "serviceKey": key,
        "pageNo": "1",
        "numOfRows": "1",
        "type": "json",
    }
    params.update(profile["params"])

    if key_mode == "encoding":
        # 인코딩 키는 이미 URL 인코딩돼 있으므로 serviceKey를 직접 붙인다.
        param_str = f"serviceKey={key}"
        rest = {k: v for k, v in params.items() if k != "serviceKey"}
        if rest:
            param_str += "&" + urlencode(rest)
        return f"{BASE}/{endpoint}?{param_str}"

    return f"{BASE}/{endpoint}?{urlencode(params)}"


def parse_payload(raw):
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if "response" in data:
        header = data["response"].get("header", {})
        body = data["response"].get("body", {})
        return {
            "resultCode": header.get("resultCode"),
            "resultMsg": header.get("resultMsg"),
            "totalCount": body.get("totalCount"),
        }

    # nkoneps.com.response.ResponseError 케이스
    err = data.get("nkoneps.com.response.ResponseError", {})
    if isinstance(err, dict):
        header = err.get("header", {})
        return {
            "resultCode": header.get("resultCode"),
            "resultMsg": header.get("resultMsg"),
            "totalCount": None,
        }
    return None


def call_once(url):
    req = Request(url, headers={"Accept": "application/json"})
    ctx = ssl.create_default_context()
    with urlopen(req, timeout=20, context=ctx) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def parse_args():
    parser = argparse.ArgumentParser(description="G2B API 정밀 진단")
    parser.add_argument("--year", type=int, default=None, help="조회 연도 오버라이드")
    parser.add_argument("--json", dest="json_out", default="", help="진단 결과 JSON 파일 경로")
    return parser.parse_args()


def main():
    args = parse_args()
    cfg = load_config()
    env_enc = (os.environ.get("ENCODING_KEY", "") or "").strip()
    env_dec = (os.environ.get("DECODING_KEY", "") or "").strip()
    enc_key = env_enc or cfg.get("ENCODING_KEY", "")
    dec_key = env_dec or cfg.get("DECODING_KEY", "")
    year = args.year if args.year else resolve_year(cfg)

    print("=" * 72)
    print("G2B API 정밀 진단 (운영 호출 규격 기준)")
    print("=" * 72)
    print(f"YEAR={year}")
    print(f"Python={sys.version.split()[0]}")
    print(f"KEY_SOURCE encoding={'env' if env_enc else 'config'}, decoding={'env' if env_dec else 'config'}")
    print()

    print("[1] DNS")
    try:
        ips = sorted(set(ip[4][0] for ip in socket.getaddrinfo("apis.data.go.kr", 443)))
        print(f"  apis.data.go.kr -> {', '.join(ips)}")
    except Exception as e:
        print(f"  DNS 오류: {e}")
    print()

    print("[2] Proxy Env")
    proxy_vars = ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "no_proxy"]
    found = False
    for var in proxy_vars:
        val = os.environ.get(var)
        if val:
            found = True
            print(f"  {var}={val}")
    if not found:
        print("  (none)")
    print()

    keys = [("encoding", enc_key), ("decoding", dec_key)]
    profiles = build_profiles(year)
    matrix_rows = []

    print("[3] Endpoint × Profile Matrix")
    for ep_key in ["const", "serv"]:
        print(f"\n  - {LABELS[ep_key]}")
        for endpoint in EP_CANDIDATES[ep_key]:
            print(f"    endpoint={endpoint}")
            for profile in profiles:
                line_prefix = f"      profile={profile['name']:<10}"
                best = None
                for key_mode, key_value in keys:
                    if not key_value or "여기에" in key_value:
                        continue
                    url = make_url(endpoint, key_value, key_mode, profile)
                    try:
                        status, raw = call_once(url)
                        parsed = parse_payload(raw)
                        if parsed:
                            best = (
                                status,
                                f"{key_mode} rc={parsed['resultCode']} msg={parsed['resultMsg']} total={parsed['totalCount']}",
                            )
                        else:
                            best = (status, f"{key_mode} non-json-or-unknown")
                        if status == 200 and parsed and parsed.get("resultCode") == "00":
                            break
                    except HTTPError as e:
                        best = (e.code, f"{key_mode} HTTP{e.code}")
                    except URLError as e:
                        best = ("URLError", f"{key_mode} {e.reason}")
                    except Exception as e:
                        best = (type(e).__name__, f"{key_mode} {e}")

                if best is None:
                    print(f"{line_prefix} -> no-key")
                    matrix_rows.append(
                        {
                            "biz_type": ep_key,
                            "endpoint": endpoint,
                            "profile": profile["name"],
                            "status": "no-key",
                            "detail": "no-key",
                        }
                    )
                else:
                    print(f"{line_prefix} -> {best[0]} | {best[1]}")
                    matrix_rows.append(
                        {
                            "biz_type": ep_key,
                            "endpoint": endpoint,
                            "profile": profile["name"],
                            "status": best[0],
                            "detail": best[1],
                        }
                    )

    print("\n[4] Quick Conclusion")
    print("  - `order_ym` 프로파일이 200/rc=00이면 운영 수집과 동일 경로가 정상입니다.")
    print("  - `minimal`만 404이면 키 이슈가 아니라 필수 조회 파라미터 누락 가능성이 큽니다.")
    print("=" * 72)

    if args.json_out:
        payload = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "year": year,
            "key_source": {
                "encoding": "env" if env_enc else "config",
                "decoding": "env" if env_dec else "config",
            },
            "matrix": matrix_rows,
        }
        out_path = Path(args.json_out).resolve()
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[JSON] wrote: {out_path}")


if __name__ == "__main__":
    main()
