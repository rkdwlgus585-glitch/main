
import re

def _is_duplicate(keyword, existing_titles):
    keyword_normalized = keyword.replace(" ", "").lower()
    keyword_words = set(keyword.split())
    
    print(f"Checking Keyword: '{keyword}'")
    print(f"  Split: {keyword_words}")

    for title in existing_titles:
        title = title.replace("\n", "")
        # Original Logic simulation
        title_normalized = title.replace(" ", "").lower()
        
        if keyword_normalized in title_normalized:
            print(f"  [MATCH-SUBSTRING] Title: {title}")
            return True, f"title substring"
        
        title_words = set(title.split())
        common_words = keyword_words & title_words
        meaningful_common = [w for w in common_words if len(w) >= 2]
        
        print(f"  Title: '{title}'")
        print(f"  Title Split: {title_words}")
        print(f"  Intersection: {meaningful_common} (Count: {len(meaningful_common)})")
        
        if len(meaningful_common) >= 3:
            print(f"  [MATCH-WORDCOUNT] Title: {title}")
            return True, f"word count >= 3"
            
    return False, ""

existing_posts = [
    "대한민국 건설업 면허 총정리 (종합/전문/기타)", 
    "건설업 면허 양도양수, 2026년 성공 전략과 핵심 체크리스트",
    "종합건설업 등록, 2026년 최신 4가지 핵심 기준 완벽 분석",
    "키스콘(kiscon) 완벽 가이드: 2026년 건설업 면허 관리의 핵심",
    "전문건설업 면허 방법, 2026년 최신 등록기준 완벽 정리",
    "건설공제조합 위치 찾기, 2026년 최신 지점 및 출자금 준비",
    "전문건설업 양도양수 진행방법, 2026년 최신 완벽 가이드",
    "건설업 기업진단 질문, 2026년 대표님들이 가장 많이 묻는 5가지",
    "건설업기업진단방법, 2026년 최신 기준과 절차 완벽 가이드"
]

new_keywords = [
    "전문건설업 면허 조건",
    "키스콘 등록",
    "전문건설업 면허 반납 방법",
    "건설업 기업진단보고서",
    "전문건설업 면허 기술인력"
]

for kw in new_keywords:
    is_dup, reason = _is_duplicate(kw, existing_posts)
    print(f"Result for '{kw}': {is_dup} ({reason})\n")
