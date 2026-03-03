import argparse
from pathlib import Path


def build_snippet(target_url: str, title: str) -> str:
    return f"""<!-- SeoulMNA AI Yangdo Widget START -->
<div id=\"smna-widget-host\"></div>
<script>
(function() {{
  var targetUrl = {target_url!r};
  var title = {title!r};
  var host = document.getElementById('smna-widget-host');
  if (!host) return;
  host.innerHTML = '' +
    '<div style="position:fixed;right:18px;bottom:18px;z-index:9999;max-width:280px;box-shadow:0 10px 24px rgba(0,0,0,.22);border-radius:14px;overflow:hidden;font-family:Pretendard,\\'Noto Sans KR\\',Arial,sans-serif">' +
    '  <div style="background:linear-gradient(120deg,#003764 0%,#0c4f84 70%,#b0894f 100%);padding:14px;color:#fff">' +
    '    <div style="font-size:12px;opacity:.9;margin-bottom:4px">서울건설정보</div>' +
    '    <div style="font-size:22px;font-weight:900;line-height:1.2">' + title + '</div>' +
    '    <div style="font-size:14px;line-height:1.4;margin-top:6px;opacity:.92">매일 업데이트되는 실거래가 기반 AI 산정</div>' +
    '  </div>' +
    '  <a href="' + targetUrl + '" target="_blank" rel="noopener noreferrer" style="display:block;text-align:center;padding:12px 14px;font-size:18px;font-weight:900;text-decoration:none;background:#fee500;color:#191919">계산기 열기</a>' +
    '</div>';
}})();
</script>
<!-- SeoulMNA AI Yangdo Widget END -->
"""


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate embeddable SeoulMNA widget snippet')
    parser.add_argument('--target-url', default='https://seoulmna.kr/yangdo-ai-customer/')
    parser.add_argument('--title', default='AI 양도가 산정 계산기')
    parser.add_argument('--output', default='output/widget/seoulmna_yangdo_widget_snippet.html')
    args = parser.parse_args()

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_snippet(args.target_url, args.title), encoding='utf-8')
    print(f'[saved] {out.resolve()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
