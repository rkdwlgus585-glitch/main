from google import genai
from google.genai import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import re
import sys
import time
from utils import load_config, require_config

# ======================================================
# [설정 구역]
# ======================================================
CONFIG = load_config({
    "JSON_FILE": "service_account.json",
    "SHEET_NAME": "26양도매물",
    "TAB_CONSULT": "상담관리",
    "TAB_ITEM": "26양도매물",
})

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass


def ensure_config(required_keys, context="match"):
    return require_config(CONFIG, required_keys, context=context)

# ======================================================
# [AI 컨설턴트 엔진]
# ======================================================
class ConsultantAI:
    def __init__(self):
        ensure_config(["GEMINI_API_KEY"], "match:ai")
        self.client = genai.Client(api_key=CONFIG["GEMINI_API_KEY"])
        self.credit_map = {
            'AAA': 30, 'AA+': 29, 'AA': 28, 'AA-': 27,
            'A+': 26, 'A': 25, 'A-': 24,
            'BBB+': 23, 'BBB': 22, 'BBB-': 21,
            'BB+': 20, 'BB': 19, 'BB-': 18,
            'B+': 17, 'B': 16, 'B-': 15,
            'CCC+': 14, 'CCC': 13, 'CCC-': 12,
            'CC': 11, 'C': 10, 'D': 0
        }

    def _score_credit(self, text):
        if not text: return -99
        match = re.search(r'([A-D]{1,3}[+-]?)', str(text).upper())
        if match:
            return self.credit_map.get(match.group(1), -99)
        return -99

    def _get_cell(self, row, idx, default=""):
        if idx < 0 or idx >= len(row):
            return default
        return row[idx]

    def _to_optional_float(self, value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        txt = str(value).strip().lower()
        if not txt or txt in {"null", "none"}:
            return None
        try:
            return float(txt)
        except (ValueError, TypeError):
            return None

    def _license_tokens(self, value):
        if value is None:
            return []
        if isinstance(value, list):
            src = " ".join(str(x) for x in value if x is not None)
        else:
            src = str(value)
        parts = re.split(r"[,/|·\s]+", src)
        return [p.strip() for p in parts if len(p.strip()) >= 2]

    def _parse_money(self, value):
        """
        [핵심] 섞여있는 돈 단위를 '억'으로 통일
        - "1800" -> 0.18 (1800만원으로 해석)
        - "1.1억" -> 1.1
        - "2000" -> 0.2
        - "12" -> 12.0 (시평은 보통 억단위)
        """
        if not value: return 0.0
        s = str(value).replace(',', '').strip()

        # "2.5억-2.7억" 같은 범위 표기는 마지막 가격(최종 양도가) 기준
        parts = re.split(r"\s*(?:~|〜|∼|–|—|-|→|->|to|TO)\s*", s)
        parts = [p for p in parts if p]
        if parts:
            s = parts[-1]
        
        # 1. '억' 글자가 있으면 제거하고 숫자만
        if '억' in s:
            num = re.sub(r'[^0-9.]', '', s.split('억')[0])
            return float(num) if num else 0.0
        
        # 2. 숫자만 있는 경우 판단
        try:
            val = float(s)
            # [판단 로직] 100보다 크면 '만원' 단위로 간주 (100억 넘는 매물은 드무니까)
            # 예: 1800 -> 0.18억 / 12 -> 12억
            if val >= 100:
                return val / 10000
            return val
        except ValueError:
            return 0.0

    def _is_numeric_price(self, value):
        src = str(value or "").strip()
        if not src:
            return False
        if "협의" in src and not re.search(r"\d", src):
            return False
        return bool(re.search(r"\d", src))

    def _resolve_price_source(self, row, idx_price, idx_claim_price):
        primary = self._get_cell(row, idx_price, "")
        claim = self._get_cell(row, idx_claim_price, "")
        if self._is_numeric_price(primary):
            return primary
        if self._is_numeric_price(claim):
            return claim
        return primary if str(primary).strip() else claim

    def parse_requirement(self, title, content):
        combined_text = f"상담제목: {title}\n상담내용: {content}"
        
        prompt = f"""
        너는 건설업 M&A 전문가야. 상담 기록을 분석해서 검색 조건(JSON)을 추출해.
        
        [상담 기록]
        "{combined_text}"

        [해석 규칙]
        1. "실적x", "무실적", "신규급" -> 'perf_3_max'를 1.0 (1억) 이하로.
        2. "최저가", "급매", "싼거" -> 'price_max'를 낮게(1.0~2.5) 잡고, 'perf_3_max'는 null(실적 있어도 됨).
        3. 단위는 '억' 기준.

        [추출 항목]
        license, cap_min/max, perf_3_min/max, price_min/max, credit_min/max

        [출력형식 JSON]
        {{"license": "전기", "cap_min": 10, "cap_max": null, "perf_3_max": null, "price_max": 2.5, "credit_min": "BB"}}
        """
        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash', 
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return json.loads(response.text)
        except Exception:
            return None

    def find_matches(self, req_json, inventory_data):
        if not req_json: return []
        req = json.loads(req_json) if isinstance(req_json, str) else req_json
        if not isinstance(req, dict):
            return []
        matches = []

        IDX_ID = 0; IDX_LIC = 2; IDX_CAP = 4; IDX_PRICE = 18; IDX_REMARK = 31; IDX_CLAIM_PRICE = 33

        def check_range(val, min_v, max_v):
            if val is None: return False
            if min_v is not None and val < min_v: return False
            if max_v is not None and val > max_v: return False
            return True

        req_cap_min = self._to_optional_float(req.get('cap_min'))
        req_cap_max = self._to_optional_float(req.get('cap_max'))
        req_price_min = self._to_optional_float(req.get('price_min'))
        req_price_max = self._to_optional_float(req.get('price_max'))
        req_perf_3_max = self._to_optional_float(req.get('perf_3_max'))
        req_license_tokens = self._license_tokens(req.get('license'))

        for row in inventory_data:
            try:
                row_id = str(self._get_cell(row, IDX_ID, "")).strip()
                if not row_id:
                    continue
                row_lic = str(self._get_cell(row, IDX_LIC, "")).strip()
                
                # [수정] 금액 정규화 적용
                row_cap = self._parse_money(self._get_cell(row, IDX_CAP, ""))    # 시평
                row_price = self._parse_money(self._resolve_price_source(row, IDX_PRICE, IDX_CLAIM_PRICE)) # 양도가(청구 양도가 fallback 포함)
                
                row_credit_score = self._score_credit(self._get_cell(row, IDX_REMARK, ""))

                # 1. 면허 (포함 여부)
                if req_license_tokens:
                    if not any(token in row_lic for token in req_license_tokens):
                        continue
                
                # 2. 시평
                if req_cap_min is not None or req_cap_max is not None:
                    if not check_range(row_cap, req_cap_min, req_cap_max):
                        continue
                
                # 3. 양도가 (조건 있을 때만)
                if req_price_min is not None or req_price_max is not None:
                    # 가격 0(협의)인 경우: "최저가" 검색이면 포함, 아니면 제외 등 정책 필요
                    # 여기서는 0이면 '가격 정보 없음'으로 보고 일단 통과시킬지, 제외할지 결정
                    # -> 안전하게: 0(협의)은 범위 체크에서 제외하거나, 0원으로 보고 체크 (0 < 3억: 통과)
                    if not check_range(row_price, req_price_min, req_price_max):
                        continue

                # 4. 실적X 특수 필터
                if req_perf_3_max is not None and req_perf_3_max <= 1.5:
                    if row_price > 3.0:
                        continue # 껍데기인데 3억 넘으면 탈락

                # 5. 신용등급
                if req.get('credit_min') or req.get('credit_max'):
                    target_min = self._score_credit(req.get('credit_min'))
                    target_max = self._score_credit(req.get('credit_max'))
                    if row_credit_score != -99:
                        if req.get('credit_min') and row_credit_score < target_min: continue
                        if req.get('credit_max') and row_credit_score > target_max: continue

                matches.append(row_id)
            except (ValueError, TypeError, KeyError):
                continue
        return matches

# ======================================================
# [메인 실행 로직]
# ======================================================
def main():
    ensure_config(["GEMINI_API_KEY", "JSON_FILE", "SHEET_NAME", "TAB_CONSULT", "TAB_ITEM"], "match:main")
    print("🕵️ [건설업 매칭 시스템] 가동 중...")
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CONFIG['JSON_FILE'], scope)
    client = gspread.authorize(creds)
    
    try:
        sh = client.open(CONFIG['SHEET_NAME'])
        ws_consult = sh.worksheet(CONFIG['TAB_CONSULT'])
        ws_item = sh.worksheet(CONFIG['TAB_ITEM'])
    except Exception as e:
        print(f"❌ 시트 연결 실패: {e}")
        return

    consult_rows = ws_consult.get_all_values()
    item_rows = ws_item.get_all_values()
    
    print(f"📊 로드된 상담 내역: {len(consult_rows)-1}건")
    print(f"📊 로드된 매물 데이터: {len(item_rows)-1}건")

    if len(item_rows) < 2: return
    inventory = item_rows[1:] 
    ai = ConsultantAI()

    # 상담 내역 순회
    for idx, row in enumerate(consult_rows[1:], start=2):
        if len(row) < 3: continue 
        
        consult_title = str(row[1]).strip()
        consult_content = str(row[2]).strip()
        prev_analysis = row[3] if len(row) > 3 else ""
        
        # [건너뛰기 조건]
        # 1. 제목/내용 둘 다 없음
        if not (consult_title or consult_content): continue
        # 2. 구분선 (===, ---)
        if consult_title.startswith("=") or consult_title.startswith("-"): continue

        analysis_json = prev_analysis
        if not analysis_json:
            print(f"🤖 분석 중 ({idx}행): [{consult_title}]")
            parsed = ai.parse_requirement(consult_title, consult_content)
            if parsed:
                analysis_json = json.dumps(parsed, ensure_ascii=False)
                ws_consult.update_cell(idx, 4, analysis_json)
                time.sleep(1)

        matched_ids = ai.find_matches(analysis_json, inventory)
        result_text = ", ".join(matched_ids) if matched_ids else "매칭 매물 없음"
        
        # 결과가 다를 때만 업데이트 (API 절약)
        current_result = row[4] if len(row) > 4 else ""
        if result_text != current_result:
            ws_consult.update_cell(idx, 5, result_text)
            print(f"   ✅ [{consult_title}] -> {result_text}")

    print("\n🎉 완료되었습니다.")

if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print(str(e))
        raise SystemExit(1)
