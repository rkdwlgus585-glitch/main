#!/usr/bin/env python3
"""정밀 진단 - DNS, 응답헤더, 리다이렉트, 프록시 등 확인"""
import socket
import os
import sys
from urllib.request import urlopen, Request, ProxyHandler, build_opener
from urllib.error import HTTPError
from urllib.parse import urlencode
from pathlib import Path
import ssl
import json

config = {}
cfg_path = Path(__file__).parent / "config.txt"
for line in cfg_path.read_text(encoding="utf-8-sig").splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    if "=" in line:
        k, v = line.split("=", 1)
        config[k.strip()] = v.strip()

enc_key = config.get("ENCODING_KEY", "")
dec_key = config.get("DECODING_KEY", "")

print("=" * 60)
print("  G2B API 정밀 진단")
print("=" * 60)

# 1. DNS 확인
print("\n[1] DNS 확인")
try:
    ips = socket.getaddrinfo("apis.data.go.kr", 443)
    unique_ips = set(ip[4][0] for ip in ips)
    print(f"  apis.data.go.kr → {unique_ips}")
except Exception as e:
    print(f"  DNS 오류: {e}")

# 2. 프록시 확인
print("\n[2] 프록시 환경변수")
for var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'no_proxy']:
    val = os.environ.get(var, '')
    if val:
        print(f"  {var} = {val}")
if not any(os.environ.get(v) for v in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']):
    print("  프록시 없음")

# 3. Python 버전
print(f"\n[3] Python {sys.version}")

# 4. 응답 헤더 상세 분석
print("\n[4] HTTP 응답 헤더 상세 분석")
base = "https://apis.data.go.kr/1230000/ao/OrderPlanSttusService/getOrderPlanSttusListCnstwk"
url = f"{base}?serviceKey={enc_key}&type=json&numOfRows=1&pageNo=1"

ctx = ssl.create_default_context()
try:
    req = Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    with urlopen(req, timeout=15, context=ctx) as resp:
        print(f"  상태: {resp.status}")
        for h, v in resp.getheaders():
            print(f"  {h}: {v}")
        print(f"  본문: {resp.read().decode('utf-8')[:300]}")
except HTTPError as e:
    print(f"  HTTP {e.code} {e.reason}")
    for h, v in e.headers.items():
        print(f"  {h}: {v}")
    body = e.read().decode("utf-8", errors="replace")
    print(f"  본문({len(body)}자): [{body[:200]}]")
except Exception as e:
    print(f"  오류: {type(e).__name__}: {e}")

# 5. 리다이렉트 추적
print("\n[5] 리다이렉트 확인")
try:
    import requests
    r = requests.get(url, timeout=15, allow_redirects=False)
    print(f"  리다이렉트 없이: {r.status_code}")
    if r.is_redirect:
        print(f"  → 리다이렉트: {r.headers.get('Location')}")
    
    r2 = requests.get(url, timeout=15, allow_redirects=True)
    print(f"  리다이렉트 허용: {r2.status_code}")
    print(f"  최종 URL: {r2.url[:120]}")
    print(f"  히스토리: {[h.status_code for h in r2.history]}")
    print(f"  응답 헤더:")
    for h, v in r2.headers.items():
        print(f"    {h}: {v}")
except Exception as e:
    print(f"  오류: {e}")

# 6. 단순 GET (serviceKey 없이) - 401 나와야 정상
print("\n[6] serviceKey 없이 호출 (401 나와야 정상)")
try:
    req = Request(f"{base}?type=json&numOfRows=1", headers={"Accept": "application/json"})
    with urlopen(req, timeout=10, context=ctx) as resp:
        print(f"  상태: {resp.status}")
except HTTPError as e:
    print(f"  HTTP {e.code} - {'정상(키 필요)' if e.code == 401 else '비정상'}")
    body = e.read().decode("utf-8", errors="replace")
    print(f"  본문: {body[:200]}")
except Exception as e:
    print(f"  오류: {e}")

# 7. 다른 공공데이터 API로 키 테스트
print("\n[7] 다른 API로 같은 키 테스트 (기상청)")
weather_url = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
try:
    test_url = f"{weather_url}?serviceKey={enc_key}&numOfRows=1&pageNo=1&dataType=JSON&base_date=20260210&base_time=1400&nx=55&ny=127"
    req = Request(test_url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=10, context=ctx) as resp:
        data = resp.read().decode("utf-8")[:150]
        print(f"  상태: {resp.status} | {data}")
except HTTPError as e:
    print(f"  HTTP {e.code}")
    body = e.read().decode("utf-8", errors="replace")[:150]
    print(f"  본문: {body}")
except Exception as e:
    print(f"  오류: {e}")

print("\n" + "=" * 60)
