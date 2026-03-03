import argparse
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_env(path: Path):
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


def build_banner_snippet(
    target_url: str,
    acquisition_url: str = "",
    frame_customer_url: str = "",
    frame_acquisition_url: str = "",
    kakao_openchat_url: str = "",
    contact_phone: str = "010-9926-8661",
    show_main_banner: bool = False,
) -> str:
    target = str(target_url or "").strip() or "https://seoulmna.co.kr/bbs/content.php?co_id=ai_calc"
    acquisition = str(acquisition_url or "").strip() or "https://seoulmna.co.kr/bbs/content.php?co_id=ai_acq"
    frame_customer = str(frame_customer_url or "").strip() or "https://seoulmna.kr/yangdo-ai-customer/"
    frame_acquisition = str(frame_acquisition_url or "").strip() or "https://seoulmna.kr/ai-license-acquisition-calculator/"
    kakao = str(kakao_openchat_url or "").strip()
    phone = str(contact_phone or "").strip() or "010-9926-8661"
    template = """<!-- SEOULMNA GLOBAL BANNER START -->
<script>
(function() {
  if (window.__smna_global_banner_booted__) return;
  window.__smna_global_banner_booted__ = true;
  var TARGET_URL = __TARGET__;
  var ACQUISITION_URL = __ACQUISITION__;
  var FRAME_CUSTOMER_URL = __FRAME_CUSTOMER__;
  var FRAME_ACQUISITION_URL = __FRAME_ACQUISITION__;
  var KAKAO_OPENCHAT_URL = __KAKAO__;
  var CONTACT_PHONE = __PHONE__;
  var SHOW_MAIN_BANNER = __SHOW_MAIN_BANNER__;
  var REPRESENTATIVE_PHONE = "1668-3548";
  var QUICK_MENU_LINK_MAP = {
    "대한건설협회": "https://www.cak.or.kr/",
    "대한전문건설협회": "https://www.kosca.or.kr/",
    "대한기계설비건설협회": "https://www.kmcca.or.kr/main.do",
    "시설물유지관리협회": "https://search.naver.com/search.naver?query=%EC%8B%9C%EC%84%A4%EB%AC%BC%EC%9C%A0%EC%A7%80%EA%B4%80%EB%A6%AC%ED%98%91%ED%9A%8C",
    "대한주택건설협회": "https://www.khba.or.kr/khbaGo.do",
    "한국전기공사협회": "https://www.keca.or.kr/",
    "한국정보통신공사협회": "https://www.kica.or.kr/",
    "한국부동산개발협회": "https://www.koda.or.kr/",
    "한국소방시설협회": "http://www.ekffa.or.kr/front",
    "한국건설기술인협회": "https://homenet.kocea.or.kr:1443/kocea/koc-kr/index.do",
    "한국전기기술인협회": "https://www.keea.or.kr/head/main/intro.do",
    "건설공제조합": "https://www.cgbest.co.kr/cgbest/index.do",
    "전문건설공제조합": "https://www.kfinco.co.kr/",
    "기계설비건설공제조합": "https://www.seolbi.com/main.do",
    "전기공사공제조합": "https://www.ecfc.co.kr/",
    "정보통신공제조합": "https://www.icfc.or.kr:7443/new_ver/main.jsp",
    "소방산업공제조합": "https://www.figu.or.kr/",
  };

  function compactText(v) {
    return String(v || "").replace(/\\s+/g, " ").trim();
  }

  function digitsOnly(v) {
    return String(v || "").replace(/\\D+/g, "");
  }

  function normalizeOutboundUrl(rawUrl) {
    var src = String(rawUrl || "").trim();
    if (!src) return "";
    if (/^javascript:/i.test(src)) return "";
    if (src.indexOf("//") === 0) return "https:" + src;
    if (/^[a-z][a-z0-9+.-]*:/i.test(src)) return src;
    if (/^[\\w.-]+\\.[a-z]{2,}(?:[/?#].*)?$/i.test(src)) return "https://" + src;
    return src;
  }

  function rewriteFooterCopyright() {
    try {
      var nodes = document.querySelectorAll("#ft, #footers, footer, .footer, .copyright, .copy, address, div, p, span, li");
      var changed = false;
      var patt = /COPYRIGHT\\s*[©c]?\\s*2018\\s*0404\\s*Association\\s*CO\\.?\\s*,?\\s*LTD\\.?\\s*ALL\\s*RIGHTS\\s*RESERVED\\.?/i;
      for (var i = 0; i < nodes.length; i += 1) {
        var n = nodes[i];
        var txt = String(n.textContent || "").replace(/\\s+/g, " ").trim();
        if (!txt || txt.length > 180) continue;
        if (!patt.test(txt)) continue;
        n.textContent = "COPYRIGHT © 서울건설정보. ALL RIGHTS RESERVED.";
        changed = true;
      }
      return changed;
    } catch (_e) {
      return false;
    }
  }

  function ensureKakaoOpenChatLink() {
    try {
      if (!KAKAO_OPENCHAT_URL) return;
      if (document.getElementById("smna-kakao-openchat-link")) return;
      var footer = document.querySelector("#ft, #footers, footer, .footer, address, .copy, .copyright");
      if (!footer) return;
      var wrap = document.createElement("div");
      wrap.id = "smna-kakao-openchat-link";
      wrap.style.marginTop = "8px";
      wrap.style.fontSize = "14px";
      wrap.style.fontWeight = "700";
      wrap.style.lineHeight = "1.45";
      wrap.innerHTML = '<a href="' + KAKAO_OPENCHAT_URL + '" target="_blank" rel="noopener noreferrer" style="color:#b87333;text-decoration:none;">대표 행정사 1:1 직접 상담</a> <span style="color:#5b7188;">/ ' + CONTACT_PHONE + "</span>";
      footer.appendChild(wrap);
    } catch (_e) {}
  }

  function faviconUrlForHref(rawHref) {
    try {
      var href = normalizeOutboundUrl(rawHref || "");
      if (!href) return "";
      var host = String(new URL(href, location.href).hostname || "").trim();
      if (!host) return "";
      return "https://www.google.com/s2/favicons?domain=" + encodeURIComponent(host) + "&sz=64";
    } catch (_e) {
      return "";
    }
  }

  function sanitizeUtilityLinks() {
    try {
      var style = document.getElementById("smna-hide-utility-links-style");
      if (!style) {
        style = document.createElement("style");
        style.id = "smna-hide-utility-links-style";
        style.textContent = ""
          + "a.smna-hide-util, li.smna-hide-util, div.smna-hide-util{display:none !important;}"
          + "#ft .smna-hide-util, footer .smna-hide-util{display:none !important;}";
        document.head.appendChild(style);
      }
      var selectors = [
        "#right-side a",
        "#right-side li",
        ".quick_menu a",
        ".quick_menu li",
        "#quicks a",
        "#quicks li",
        ".side_gnb a",
        ".side_gnb li",
        "#ft a",
        "footer a",
      ];
      var hideWords = ["관리자", "정보수정", "로그아웃", "logout", "로그인", "login"];
      var nodes = document.querySelectorAll(selectors.join(","));
      for (var i = 0; i < nodes.length; i += 1) {
        var n = nodes[i];
        var txt = compactText(n.textContent || "").toLowerCase();
        if (!txt) continue;
        var shouldHide = false;
        for (var j = 0; j < hideWords.length; j += 1) {
          var word = String(hideWords[j] || "").toLowerCase();
          if (txt === word || txt.indexOf(word) >= 0) {
            shouldHide = true;
            break;
          }
        }
        if (!shouldHide) continue;
        n.classList.add("smna-hide-util");
        var li = n.closest ? n.closest("li") : null;
        if (li) li.classList.add("smna-hide-util");
      }
    } catch (_e) {}
  }

  function mountRelatedOrganizationsCenter(entries) {
    try {
      var list = Array.isArray(entries) ? entries.slice() : [];
      if (!list.length) return;
      var clean = [];
      var seen = {};
      for (var i = 0; i < list.length; i += 1) {
        var e = list[i] || {};
        var label = compactText(e.label || "");
        var href = normalizeOutboundUrl(e.href || "");
        if (!label || !href) continue;
        if (
          label.indexOf("관리자") >= 0
          || label.indexOf("정보수정") >= 0
          || label.indexOf("로그인") >= 0
          || label.indexOf("로그아웃") >= 0
          || label.indexOf("회원가입") >= 0
        ) continue;
        if (seen[label]) continue;
        seen[label] = true;
        clean.push({ label: label, href: href });
      }
      if (!clean.length) return;

      var style = document.getElementById("smna-related-org-style");
      if (!style) {
        style = document.createElement("style");
        style.id = "smna-related-org-style";
        style.textContent = ""
          + "#smna-related-org-center{max-width:1120px;margin:18px auto 10px;padding:16px 16px 14px;border:1px solid #dbe6f2;border-radius:14px;background:linear-gradient(180deg,#ffffff 0%,#f7fbff 100%);box-shadow:0 8px 22px rgba(0,55,100,.08);}"
          + "#smna-related-org-center .smna-org-head{text-align:center;margin-bottom:10px;}"
          + "#smna-related-org-center .smna-org-title{margin:0;font-size:24px;line-height:1.2;color:#003764;font-weight:900;letter-spacing:.01em;}"
          + "#smna-related-org-center .smna-org-sub{margin:5px 0 0;font-size:14px;line-height:1.45;color:#355775;font-weight:700;}"
          + "#smna-related-org-center .smna-org-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;align-items:stretch;}"
          + "#smna-related-org-center .smna-org-link{display:flex;align-items:center;justify-content:center;gap:9px;min-height:46px;padding:10px 10px;border:1px solid #cfe0f0;border-radius:11px;background:#fff;text-decoration:none;color:#0f3f66;font-size:14px;line-height:1.35;font-weight:800;text-align:center;}"
          + "#smna-related-org-center .smna-org-link:hover{border-color:#91b7d8;box-shadow:0 8px 14px rgba(0,54,100,.12);transform:translateY(-1px);}"
          + "#smna-related-org-center .smna-org-logo{display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;flex:0 0 20px;border-radius:50%;overflow:hidden;border:1px solid #d6e3f0;background:#fff;}"
          + "#smna-related-org-center .smna-org-logo img{width:16px;height:16px;display:block;object-fit:contain;}"
          + "@media(max-width:980px){#smna-related-org-center{margin:14px auto 8px;padding:12px;}#smna-related-org-center .smna-org-title{font-size:20px;}#smna-related-org-center .smna-org-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;}#smna-related-org-center .smna-org-link{min-height:42px;padding:8px 7px;font-size:13px;}}";
        document.head.appendChild(style);
      }

      var mount = document.getElementById("smna-related-org-center");
      if (!mount) {
        mount = document.createElement("section");
        mount.id = "smna-related-org-center";
      }
      mount.innerHTML = ""
        + "<div class='smna-org-head'>"
        + "  <h3 class='smna-org-title'>유관기관 바로가기</h3>"
        + "  <p class='smna-org-sub'>협회/공제조합 공식 사이트를 빠르게 이동하세요.</p>"
        + "</div>";
      var grid = document.createElement("div");
      grid.className = "smna-org-grid";
      for (var k = 0; k < clean.length; k += 1) {
        var item = clean[k];
        var a = document.createElement("a");
        a.className = "smna-org-link";
        a.href = item.href;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        var logo = faviconUrlForHref(item.href);
        a.innerHTML = ""
          + "<span class='smna-org-logo'>" + (logo ? ("<img alt='' src='" + logo + "' loading='lazy' decoding='async' />") : "") + "</span>"
          + "<span>" + item.label + "</span>";
        grid.appendChild(a);
      }
      mount.appendChild(grid);

      var footer = document.querySelector("#ft, footer");
      var anchor = document.querySelector("#bo_list, #container, #contents, #wrapper, #ctt, #bo_w, #sub_wrap, #sub, #content, #main, #site-content, .sub_wrap, .content");
      if (!anchor) anchor = document.body || document.documentElement;
      if (!mount.parentNode) {
        if (footer && footer.parentNode) footer.parentNode.insertBefore(mount, footer);
        else anchor.appendChild(mount);
      } else if (footer && mount.nextSibling !== footer && footer.parentNode) {
        footer.parentNode.insertBefore(mount, footer);
      }
    } catch (_e) {}
  }

  function enhanceQuickMenu() {
    try {
      var sideRoot = document.querySelector("#right-side");
      var quickHead = (sideRoot && sideRoot.querySelector(".quick_menu")) || document.querySelector("#right-side .quick_menu") || document.querySelector(".quick_menu");
      var quickLinks = (sideRoot && sideRoot.querySelector("#quicks")) || document.querySelector("#right-side #quicks") || document.querySelector("#quicks");
      if (!sideRoot) {
        sideRoot = document.getElementById("smna-generated-right-side");
        if (!sideRoot) {
          sideRoot = document.createElement("aside");
          sideRoot.id = "smna-generated-right-side";
          document.body.appendChild(sideRoot);
        }
      }
      if (!quickHead && sideRoot) {
        quickHead = sideRoot.querySelector(".quick_menu");
        if (!quickHead) {
          quickHead = document.createElement("div");
          quickHead.className = "quick_menu";
          quickHead.id = "smna-generated-quick-menu";
          sideRoot.insertBefore(quickHead, sideRoot.firstChild || null);
        }
      }
      if (!quickLinks && sideRoot && quickHead) {
        quickLinks = sideRoot.querySelector("#smna-generated-quicks");
        if (!quickLinks) {
          quickLinks = document.createElement("div");
          quickLinks.id = "smna-generated-quicks";
          if (quickHead.nextSibling) sideRoot.insertBefore(quickLinks, quickHead.nextSibling);
          else sideRoot.appendChild(quickLinks);
        }
      }
      if (!quickHead && !quickLinks) return;

      function refreshAnchorsOnly() {
        if (!quickLinks) return;
        var anchors = quickLinks.querySelectorAll("a");
        for (var k = 0; k < anchors.length; k += 1) {
          var a = anchors[k];
          if (!a) continue;
          var label = compactText(a.textContent || "");
          var mapped = QUICK_MENU_LINK_MAP[label] || "";
          var href = normalizeOutboundUrl(mapped || a.getAttribute("href") || "");
          if (!href) continue;
          if (a.getAttribute("href") !== href) a.setAttribute("href", href);
          if (!/^tel:/i.test(href)) {
            a.setAttribute("target", "_blank");
            a.setAttribute("rel", "noopener noreferrer");
          }
          var isCurrent = false;
          try {
            var normalizedHref = href;
            if (/^https?:\\/\\//i.test(normalizedHref)) {
              normalizedHref = String(new URL(normalizedHref, location.href).pathname || "");
            }
            var pagePath = String(location.pathname || "");
            if (normalizedHref && normalizedHref !== "/" && pagePath.indexOf(normalizedHref) === 0) {
              isCurrent = true;
            }
          } catch (_e) {}
          if (isCurrent) a.classList.add("smna-qm-active");
          else a.classList.remove("smna-qm-active");
        }
      }

      var style = document.getElementById("smna-quick-menu-style");
      if (!style) {
        style = document.createElement("style");
        style.id = "smna-quick-menu-style";
        style.textContent = ""
          + ".smna-quick-upgraded{box-sizing:border-box;}"
          + ".smna-quick-upgraded *, .smna-quick-upgraded *::before, .smna-quick-upgraded *::after{box-sizing:border-box;}"
          + ".smna-quick-upgraded.smna-quick-head{position:relative;background:linear-gradient(162deg,#003764 0%,#00508e 66%,#0f67a3 100%);border:1px solid rgba(255,255,255,.24);border-radius:16px;padding:12px 10px;color:#f3f9ff;box-shadow:0 16px 32px rgba(0,30,56,.34);overflow:hidden;display:grid;gap:10px;}"
          + ".smna-quick-upgraded.smna-quick-head::before{content:'SEOULMNA QUICK';display:block;font-size:11px;letter-spacing:.08em;font-weight:800;color:#d8eafc;opacity:.9;margin:0;}"
          + ".smna-quick-upgraded .smna-quick-contact{margin:0;padding:10px;border-radius:12px;background:linear-gradient(180deg,#ffffff 0%,#f5faff 100%);border:1px solid #cadef1;display:grid;gap:7px;box-shadow:inset 0 1px 0 rgba(255,255,255,.88);}"
          + ".smna-quick-upgraded .smna-quick-contact .smna-quick-badge{display:inline-flex;align-items:center;justify-content:center;width:max-content;max-width:100%;padding:3px 8px;border-radius:999px;background:#e7f3ff;color:#004278;font-size:11px;font-weight:900;line-height:1.2;letter-spacing:.01em;}"
          + ".smna-quick-upgraded .smna-quick-contact a{display:block;text-decoration:none;font-weight:900;line-height:1.22;color:#003764;word-break:keep-all;}"
          + ".smna-quick-upgraded .smna-quick-contact a.main{font-size:24px;color:#ee2d44;}"
          + ".smna-quick-upgraded .smna-quick-contact a.mobile{font-size:22px;color:#003764;}"
          + ".smna-quick-upgraded .smna-quick-contact a.chat-inline{display:block;margin-top:0;font-size:14px;line-height:1.35;color:#0d5f94 !important;font-weight:800;text-decoration:underline;text-underline-offset:2px;}"
          + ".smna-quick-upgraded .smna-quick-contact a.chat{margin-top:2px;display:flex;align-items:center;justify-content:center;min-height:40px;padding:9px 11px;border-radius:10px;background:linear-gradient(135deg,#c3803a 0%,#d59a4d 58%,#b87333 100%);color:#fff !important;font-size:16px;font-weight:900;border:1px solid #a86b30;box-shadow:0 6px 12px rgba(152,97,41,.28);}"
          + ".smna-quick-upgraded .smna-quick-calc-cta{display:grid;grid-template-columns:1fr;gap:8px;}"
          + ".smna-quick-upgraded .smna-quick-calc-cta a{display:flex;align-items:center;justify-content:center;min-height:40px;padding:9px 10px;border-radius:10px;border:1px solid transparent;text-decoration:none;font-size:15px;line-height:1.2;font-weight:900;}"
          + ".smna-quick-upgraded .smna-quick-calc-cta a.primary{background:#ffffff;color:#003764;border-color:#d6e4f2;}"
          + ".smna-quick-upgraded .smna-quick-calc-cta a.secondary{background:#e8eef5;color:#0b3d66;border-color:#d3deea;}"
          + ".smna-quick-upgraded .smna-qm-favorite{display:flex;align-items:center;justify-content:center;min-height:50px;padding:10px 12px;border-radius:13px;background:linear-gradient(135deg,#ffeaa6 0%,#ffd15f 48%,#e4a62a 100%);color:#4c2c00 !important;font-size:22px !important;font-weight:900 !important;box-shadow:0 7px 16px rgba(255,196,66,.42);text-decoration:none !important;}"
          + ".smna-quick-upgraded .smna-qm-favorite::before{content:'★';margin-right:6px;font-size:18px;line-height:1;}"
          + ".smna-quick-upgraded .smna-qm-openchat{display:flex;align-items:center;justify-content:center;min-height:40px;padding:9px 11px;border-radius:10px;background:linear-gradient(135deg,#c3803a 0%,#d59a4d 58%,#b87333 100%);border:1px solid #a86b30;color:#fff !important;font-size:14px;font-weight:900;text-decoration:none !important;}"
          + ".smna-quick-upgraded.smna-quick-links{margin-top:12px !important;display:block !important;padding-top:0 !important;}"
          + ".smna-quick-upgraded.smna-quick-links .smna-qm-title{margin:0 0 8px;padding:0 4px;color:#b8c8d8;font-size:11px;font-weight:900;letter-spacing:.06em;line-height:1.1;}"
          + ".smna-quick-upgraded.smna-quick-links .smna-qm-list{display:grid;gap:10px;}"
          + ".smna-quick-upgraded.smna-quick-links a{display:flex !important;align-items:center !important;min-height:46px !important;padding:11px 10px !important;margin:0 !important;border-radius:11px !important;background:linear-gradient(180deg,#ffffff 0%,#f8fbff 100%) !important;border:1px solid #d8e6f3 !important;font-size:13px !important;line-height:1.35 !important;color:#163f64 !important;font-weight:800 !important;text-decoration:none !important;transition:border-color .16s ease,transform .16s ease,box-shadow .16s ease;}"
          + ".smna-quick-upgraded.smna-quick-links a:hover{border-color:#92b6d6;box-shadow:0 8px 14px rgba(0,54,100,.12);transform:translateY(-1px);}"
          + ".smna-quick-upgraded.smna-quick-links a:focus-visible,.smna-quick-upgraded .smna-qm-favorite:focus-visible,.smna-quick-upgraded .smna-quick-contact a.chat:focus-visible{outline:2px solid #ffc857;outline-offset:2px;}"
          + ".smna-quick-upgraded.smna-quick-links a.smna-qm-active{background:#e7f3ff;border-color:#8fb3d4;color:#003764 !important;}"
          + ".smna-quick-upgraded.smna-quick-head{padding:12px !important;display:grid;gap:10px !important;background:linear-gradient(156deg,#003764 0%,#0d4f84 74%,#175e95 100%) !important;}"
          + ".smna-quick-upgraded .smna-qm-action-grid{display:grid;gap:9px;}"
          + ".smna-quick-upgraded .smna-qm-action{display:flex;align-items:center;justify-content:center;min-height:52px;padding:11px 10px;border-radius:12px;border:1px solid #cfe0f0;background:#fff;color:#003764 !important;text-decoration:none !important;font-size:18px;line-height:1.2;font-weight:900;text-align:center;word-break:keep-all;}"
          + ".smna-quick-upgraded .smna-qm-action .small{display:block;font-size:13px;font-weight:800;line-height:1.35;color:#4d6a84;margin-top:2px;}"
          + ".smna-quick-upgraded .smna-qm-action.primary{background:linear-gradient(140deg,#ffffff 0%,#f5faff 100%);border-color:#b9d2e9;}"
          + ".smna-quick-upgraded .smna-qm-action.call-main{background:linear-gradient(140deg,#ffffff 0%,#fff2f4 100%);border-color:#f3c6cf;color:#d9314b !important;}"
          + ".smna-quick-upgraded .smna-qm-action.call-mobile{background:linear-gradient(140deg,#ffffff 0%,#edf7ff 100%);border-color:#b8d8f0;color:#003764 !important;}"
          + ".smna-quick-upgraded .smna-qm-action.chat{background:linear-gradient(135deg,#fee500 0%,#ffd63b 75%,#ffc400 100%);border-color:#e5c100;color:#2a2300 !important;}"
          + ".smna-quick-upgraded .smna-qm-action.favorite{background:linear-gradient(135deg,#ffeaa6 0%,#ffd15f 48%,#e4a62a 100%);border-color:#d39a29;color:#4c2c00 !important;}"
          + ".smna-quick-upgraded .smna-qm-action.favorite::before{content:'★';margin-right:7px;font-size:17px;line-height:1;}"
          + ".smna-quick-upgraded.smna-quick-links{display:none !important;}"
          + "#smna-generated-right-side{position:fixed;right:12px;top:188px;width:230px;z-index:5900;}"
          + "#smna-generated-right-side .quick_menu{margin:0 !important;}"
          + "@media(max-width:980px){#smna-generated-right-side{display:none !important;}}"
          + "@media(max-width:1200px){.smna-quick-upgraded .smna-qm-action{font-size:16px;min-height:48px;padding:10px 8px;}.smna-quick-upgraded .smna-qm-action .small{font-size:12px;}}";
        document.head.appendChild(style);
      }

      function removeLegacyFavoriteArtifacts() {
        var root = sideRoot || document;
        var nodes = root.querySelectorAll("a,button,div,span,strong,p,img");
        for (var i = 0; i < nodes.length; i += 1) {
          var node = nodes[i];
          if (!node || !node.parentNode) continue;
          if (node.id && node.id.indexOf("smna-") === 0) continue;
          if (node.closest && node.closest(".smna-quick-upgraded")) continue;
          var txt = compactText(node.textContent || "");
          var alt = compactText(node.getAttribute ? (node.getAttribute("alt") || "") : "");
          var title = compactText(node.getAttribute ? (node.getAttribute("title") || "") : "");
          var onclick = compactText(node.getAttribute ? (node.getAttribute("onclick") || "") : "").toLowerCase();
          var matched = (
            txt === "즐겨찾기"
            || alt.indexOf("즐겨찾기") >= 0
            || title.indexOf("즐겨찾기") >= 0
            || onclick.indexOf("bookmarksite") >= 0
            || onclick.indexOf("addfavorite") >= 0
          );
          if (!matched) continue;
          if (node.tagName && node.tagName.toLowerCase() === "img" && node.parentNode.tagName && node.parentNode.tagName.toLowerCase() === "a") {
            node = node.parentNode;
          }
          if (node.parentNode) node.parentNode.removeChild(node);
        }
      }

      function collectQuickEntries() {
        var anchors = [];
        if (quickLinks) anchors = anchors.concat(Array.prototype.slice.call(quickLinks.querySelectorAll("a")));
        if (quickHead) anchors = anchors.concat(Array.prototype.slice.call(quickHead.querySelectorAll("a")));
        var out = [];
        var seen = {};
        for (var i = 0; i < anchors.length; i += 1) {
          var a = anchors[i];
          if (!a) continue;
          if (a.getAttribute && a.getAttribute("data-smna-utility-action") === "1") continue;
          if (a.closest && a.closest(".smna-qm-action-grid")) continue;
          var label = compactText(a.textContent || "");
          if (!label) continue;
          if (
            label.indexOf("즐겨찾기") >= 0
            || label.indexOf("오픈채팅") >= 0
            || label.indexOf("대표전화") >= 0
            || label.indexOf("직접 상담") >= 0
            || label.indexOf("양도양수 매물 즉시 확인") >= 0
            || label.indexOf("카카오 오픈채팅") >= 0
            || label.indexOf("행정사 1:1 상담") >= 0
            || label.indexOf("대표 전화") >= 0
            || label.indexOf("회원가입") >= 0
            || label.indexOf("로그인") >= 0
          ) continue;
          var mapped = QUICK_MENU_LINK_MAP[label] || "";
          var href = normalizeOutboundUrl(mapped || a.getAttribute("href") || "");
          if (!href) continue;
          if (seen[label]) continue;
          seen[label] = true;
          out.push({ label: label, href: href });
        }
        for (var key in QUICK_MENU_LINK_MAP) {
          if (!Object.prototype.hasOwnProperty.call(QUICK_MENU_LINK_MAP, key)) continue;
          if (seen[key]) continue;
          out.push({ label: key, href: normalizeOutboundUrl(QUICK_MENU_LINK_MAP[key]) });
        }
        return out;
      }

      if (quickHead) quickHead.classList.add("smna-quick-upgraded", "smna-quick-head");
      if (quickLinks) quickLinks.classList.add("smna-quick-upgraded", "smna-quick-links");

      var alreadyRebuilt = !!(
        quickHead && quickLinks
        && quickHead.getAttribute("data-smna-qm-rebuilt") === "1"
        && quickLinks.getAttribute("data-smna-qm-rebuilt") === "1"
        && quickLinks.querySelector(".smna-qm-list")
      );
      if (alreadyRebuilt) {
        refreshAnchorsOnly();
        mountRelatedOrganizationsCenter(collectQuickEntries());
        sanitizeUtilityLinks();
        return;
      }

      var entries = collectQuickEntries();
      var repDigits = digitsOnly(REPRESENTATIVE_PHONE);
      var mobileDigits = digitsOnly(CONTACT_PHONE);

      if (quickHead) {
        quickHead.innerHTML = "";
        var actionGrid = document.createElement("div");
        actionGrid.className = "smna-qm-action-grid";

        var quickActions = [];
        quickActions.push({
          cls: "primary",
          label: "양도양수 매물 즉시 확인",
          small: "실시간 매물/협의가 확인",
          href: "https://seoulmna.co.kr/mna",
          calc: false,
        });
        quickActions.push({
          cls: "call-main",
          label: "대표 전화 1668-3548",
          small: "(유료)",
          href: "tel:" + repDigits,
          calc: false,
        });
        quickActions.push({
          cls: "call-mobile",
          label: "행정사 1:1 상담",
          small: CONTACT_PHONE,
          href: "tel:" + mobileDigits,
          calc: false,
        });
        if (KAKAO_OPENCHAT_URL) {
          quickActions.push({
            cls: "chat",
            label: "카카오 오픈채팅",
            small: "클릭 시 즉시 연결",
            href: KAKAO_OPENCHAT_URL,
            calc: false,
          });
        }
        quickActions.push({
          cls: "favorite",
          label: "즐겨찾기",
          small: "서울건설정보 바로가기",
          href: "https://seoulmna.co.kr/",
          calc: false,
        });

        for (var q = 0; q < quickActions.length; q += 1) {
          var info = quickActions[q];
          var btn = document.createElement("a");
          btn.className = "smna-qm-action " + String(info.cls || "");
          btn.setAttribute("data-smna-utility-action", "1");
          btn.href = normalizeOutboundUrl(info.href || "") || "https://seoulmna.co.kr/";
          if (info.calc) btn.setAttribute("data-smna-calc-link", "1");
          if (!/^tel:/i.test(btn.href)) {
            btn.target = "_blank";
            btn.rel = "noopener noreferrer";
          }
          btn.innerHTML = "<span>" + info.label + (info.small ? ("<span class='small'>" + info.small + "</span>") : "") + "</span>";
          actionGrid.appendChild(btn);
        }
        quickHead.appendChild(actionGrid);
        quickHead.setAttribute("data-smna-qm-rebuilt", "1");
      }

      if (quickLinks) {
        quickLinks.innerHTML = "";
        quickLinks.style.display = "none";
        quickLinks.setAttribute("data-smna-qm-rebuilt", "1");
      }

      mountRelatedOrganizationsCenter(entries);
      sanitizeUtilityLinks();
      removeLegacyFavoriteArtifacts();
    } catch (_e) {}
  }

  function dedupeMnaMobileList() {
    try {
      var path = String(location.pathname || "").toLowerCase();
      if (path.indexOf("/mna") !== 0) return;
      if (window.innerWidth > 980) return;
      var tables = document.querySelectorAll("#bo_list table.nmanss");
      if (!tables || !tables.length) return;
      var seen = {};
      for (var i = 0; i < tables.length; i += 1) {
        var t = tables[i];
        var a = t.querySelector('a[href*="/mna/"]');
        if (!a) continue;
        var href = String(a.getAttribute("href") || "");
        var m = href.match(/\\/mna\\/(\\d+)/);
        if (!m) continue;
        var no = m[1];
        if (seen[no]) {
          t.remove();
        } else {
          seen[no] = true;
        }
      }
    } catch (_e) {}
  }

  function stabilizeHeaderAndNav() {
    try {
      var style = document.getElementById("smna-header-stabilize-style");
      if (!style) {
        style = document.createElement("style");
        style.id = "smna-header-stabilize-style";
        style.textContent = ""
          + "#header{overflow:visible !important;}"
          + "#header .header-inner{overflow:visible !important;min-height:74px;display:flex;align-items:center;padding-top:6px;padding-bottom:6px;}"
          + "#header #logo{display:flex !important;align-items:center !important;justify-content:flex-start !important;min-height:58px;line-height:1;overflow:visible !important;padding-right:10px;}"
          + "#header #logo a{display:inline-flex !important;align-items:center !important;justify-content:flex-start !important;line-height:1;overflow:visible !important;}"
          + "#header #logo img{display:block !important;width:auto !important;height:auto !important;max-height:44px !important;object-fit:contain !important;position:static !important;top:auto !important;}"
          + "#header .gnb{display:flex;align-items:center;flex-wrap:wrap;}"
          + "#header .gnb > li > a{display:flex;align-items:center;line-height:1.25 !important;min-height:46px;padding-top:8px;padding-bottom:8px;}"
          + "@media(max-width:1200px){#header #logo img{max-height:40px !important;}#header .header-inner{min-height:68px;}}";
        document.head.appendChild(style);
      }

      var topMenus = document.querySelectorAll("#header .gnb > li");
      for (var i = 0; i < topMenus.length; i += 1) {
        var li = topMenus[i];
        var topAnchor = null;
        for (var k = 0; k < li.children.length; k += 1) {
          var child = li.children[k];
          if (child && child.tagName && child.tagName.toLowerCase() === "a") {
            topAnchor = child;
            break;
          }
        }
        if (!topAnchor) continue;
        var text = compactText(topAnchor.textContent || "");
        var href = normalizeOutboundUrl(topAnchor.getAttribute("href") || "");
        if (!text && !href) {
          if (li.parentNode) li.parentNode.removeChild(li);
          continue;
        }
        if (href) topAnchor.setAttribute("href", href);
        var target = compactText(topAnchor.getAttribute("target") || "");
        if (target === "_") {
          if (/^https?:\\/\\//i.test(href) && href.indexOf(location.origin) !== 0) topAnchor.setAttribute("target", "_blank");
          else topAnchor.setAttribute("target", "_self");
        }
      }

      var allBadTarget = document.querySelectorAll("a[target='_']");
      for (var j = 0; j < allBadTarget.length; j += 1) {
        var a = allBadTarget[j];
        var href2 = normalizeOutboundUrl(a.getAttribute("href") || "");
        if (href2) a.setAttribute("href", href2);
        if (/^https?:\\/\\//i.test(href2) && href2.indexOf(location.origin) !== 0) a.setAttribute("target", "_blank");
        else a.setAttribute("target", "_self");
      }
    } catch (_e) {}
  }

  function computeHeaderOffsetPx() {
    try {
      var selectors = ["#header", "#hd", "#masthead", "header.site-header", ".site-header", ".main-header-bar-wrap"];
      var maxH = 0;
      for (var i = 0; i < selectors.length; i += 1) {
        var node = document.querySelector(selectors[i]);
        if (!node || !node.getBoundingClientRect) continue;
        var rect = node.getBoundingClientRect();
        if (!rect || rect.height <= 0) continue;
        var cs = window.getComputedStyle(node);
        var pos = String((cs && cs.position) || "").toLowerCase();
        var top = Number(rect.top || 0);
        if (pos === "fixed" || pos === "sticky" || top <= 18) {
          maxH = Math.max(maxH, rect.height);
        }
      }
      if (!Number.isFinite(maxH) || maxH <= 0) return 24;
      return Math.max(24, Math.min(220, Math.round(maxH + 18)));
    } catch (_e) {
      return 24;
    }
  }

  function applyBridgeTopOffset() {
    try {
      if (!document.body || !document.documentElement) return;
      var offset = computeHeaderOffsetPx();
      document.documentElement.style.setProperty("--smna-bridge-top-offset", String(offset) + "px");
      document.body.style.setProperty("--smna-bridge-top-offset", String(offset) + "px");
      var bridge = document.getElementById("smna-calc-bridge");
      if (bridge) bridge.style.marginTop = String(offset) + "px";
    } catch (_e) {}
  }

  function applyBannerTextBalance(rail) {
    try {
      if (!rail) return;
      rail.classList.remove("align-left", "align-center", "align-right");
      var title = String((rail.querySelector(".title") || {}).textContent || "").trim();
      var sub = String((rail.querySelector(".sub") || {}).textContent || "").replace(/\\s+/g, " ").trim();
      var desc = String((rail.querySelector(".desc") || {}).textContent || "").replace(/\\s+/g, " ").trim();
      var width = Number(rail.clientWidth || 0);
      if (!width) {
        try {
          width = Number((window.getComputedStyle(rail).width || "").replace("px", "")) || 0;
        } catch (_e) {
          width = 0;
        }
      }
      width = Math.max(160, width || 220);
      var weightedChars = (title.length * 1.9) + (sub.length * 1.2) + (desc.length * 0.95);
      var density = weightedChars / width;
      var alignClass = "align-left";
      if (density <= 0.30) alignClass = "align-right";
      else if (density <= 0.42) alignClass = "align-center";
      rail.classList.add(alignClass);

      var subNode = rail.querySelector(".sub");
      if (subNode) {
        subNode.classList.remove("stacked");
        var shouldStack = (width <= 220) || (sub.length >= 16);
        if (shouldStack) subNode.classList.add("stacked");
      }
    } catch (_e) {}
  }

  function detectCalculatorMode() {
    try {
      var path = String(location.pathname || "").toLowerCase();
      var bo = "";
      var co = "";
      try {
        var q = new URLSearchParams(location.search || "");
        bo = String(q.get("bo_table") || "").toLowerCase();
        co = String(q.get("co_id") || "").toLowerCase();
      } catch (_e) {}
      if (path.indexOf("/bbs/content.php") === 0) {
        if (co === "ai_acq") return "acquisition";
        if (co === "ai_calc") return "customer";
      }
      if (path.indexOf("/yangdo_ai_ops/") === 0 || bo === "yangdo_ai_ops") return "acquisition";
      if (path.indexOf("/yangdo_ai/") === 0 || bo === "yangdo_ai") return "customer";
      return "";
    } catch (_e) {
      return "";
    }
  }

  function isMainPath() {
    try {
      var path = String(location.pathname || "").toLowerCase();
      if (!path || path === "/") return true;
      if (path === "/index.php" || path === "/index.html" || path === "/main.php") return true;
      return false;
    } catch (_e) {
      return false;
    }
  }

  function syncMainBannerOverrideByQuery() {
    try {
      var q = new URLSearchParams(location.search || "");
      var raw = String(q.get("smna_main_banner") || "").trim();
      if (!raw) return;
      if (raw === "1") localStorage.setItem("smna_main_banner_unlock", "1");
      if (raw === "0") localStorage.removeItem("smna_main_banner_unlock");
    } catch (_e) {}
  }

  function syncGlobalBannerOverrideByQuery() {
    try {
      var q = new URLSearchParams(location.search || "");
      var raw = String(q.get("smna_banner") || "").trim();
      if (!raw) return;
      if (raw === "1") localStorage.setItem("smna_banner_unlock", "1");
      if (raw === "0") localStorage.removeItem("smna_banner_unlock");
    } catch (_e) {}
  }

  function shouldShowGlobalBanner() {
    try {
      if (SHOW_MAIN_BANNER) return true;
      syncGlobalBannerOverrideByQuery();
      return localStorage.getItem("smna_banner_unlock") === "1";
    } catch (_e) {
      return false;
    }
  }

  function shouldShowMainBanner() {
    try {
      if (SHOW_MAIN_BANNER) return true;
      syncMainBannerOverrideByQuery();
      if (localStorage.getItem("smna_main_banner_unlock") === "1") return true;
      return shouldShowGlobalBanner();
    } catch (_e) {
      return false;
    }
  }

  function isLoginPage() {
    try {
      var path = String(location.pathname || "").toLowerCase();
      return path.indexOf("/bbs/login.php") === 0;
    } catch (_e) {
      return false;
    }
  }

  function isLikelyLoggedIn() {
    try {
      var anchors = document.querySelectorAll("a[href], button, [data-role]");
      for (var i = 0; i < anchors.length; i += 1) {
        var el = anchors[i];
        var href = compactText(el.getAttribute ? (el.getAttribute("href") || "") : "").toLowerCase();
        var text = compactText(el.textContent || "").toLowerCase();
        if (href.indexOf("/bbs/logout.php") >= 0) return true;
        if (text.indexOf("로그아웃") >= 0) return true;
        if (text.indexOf("logout") >= 0) return true;
        if (href.indexOf("/bbs/mypage.php") >= 0) return true;
      }
      return false;
    } catch (_e) {
      return false;
    }
  }

  function absoluteUrl(raw) {
    try {
      if (!raw) return "";
      return String(new URL(String(raw), location.href).toString());
    } catch (_e) {
      return String(raw || "");
    }
  }

  function buildLoginGateUrl(targetHref) {
    try {
      var absTarget = absoluteUrl(targetHref || TARGET_URL || location.href);
      var login = new URL("/bbs/login.php", location.origin);
      login.searchParams.set("url", absTarget);
      return String(login.toString());
    } catch (_e) {
      var fallback = String(targetHref || TARGET_URL || location.href);
      return "/bbs/login.php?url=" + encodeURIComponent(fallback);
    }
  }

  function applyLoginGateToCalculatorLinks(scope) {
    try {
      var root = scope || document;
      var nodes = root.querySelectorAll(
        "a[data-smna-calc-link='1'],a[href*='co_id=ai_calc'],a[href*='co_id=ai_acq'],a[href*='yangdo-ai-customer'],a[href*='ai-license-acquisition-calculator']"
      );
      if (!nodes || !nodes.length) return;
      var logged = isLikelyLoggedIn();
      for (var i = 0; i < nodes.length; i += 1) {
        var a = nodes[i];
        if (!a) continue;
        var href = String(a.getAttribute("href") || "").trim();
        if (!href) continue;
        if (!a.getAttribute("data-smna-original-href")) a.setAttribute("data-smna-original-href", href);
        if (!a.getAttribute("data-smna-calc-link")) a.setAttribute("data-smna-calc-link", "1");
        if (logged) {
          var originalHref = String(a.getAttribute("data-smna-original-href") || href);
          if (a.getAttribute("href") !== originalHref) a.setAttribute("href", originalHref);
        } else if (!isLoginPage()) {
          a.setAttribute("href", buildLoginGateUrl(a.getAttribute("data-smna-original-href") || href));
        }
      }
    } catch (_e) {}
  }

  function enhanceLoginPageGoogleCta() {
    try {
      if (!isLoginPage()) return;
      var style = document.getElementById("smna-google-login-style");
      if (!style) {
        style = document.createElement("style");
        style.id = "smna-google-login-style";
        style.textContent = ""
          + ".smna-google-login-cta{display:flex !important;align-items:center !important;justify-content:center !important;min-height:52px !important;padding:12px 14px !important;border-radius:12px !important;"
          + "border:2px solid #0f5ea0 !important;background:linear-gradient(180deg,#ffffff 0%,#f4f9ff 100%) !important;color:#003764 !important;font-size:17px !important;font-weight:900 !important;"
          + "text-decoration:none !important;box-shadow:0 8px 20px rgba(0,55,100,.14) !important;}"
          + ".smna-google-login-guide{margin:0 0 12px;padding:12px 14px;border:1px solid #cfe0f0;border-radius:12px;background:#f7fbff;color:#003764;font-size:15px;line-height:1.45;font-weight:800;}";
        document.head.appendChild(style);
      }

      var loginRoot = document.querySelector("#login_fs, #fmemberlogin, form[name=flogin], .login, #mb_login, #login");
      if (!loginRoot) return;

      var allCandidates = document.querySelectorAll("a[href],button,[role='button']");
      var found = [];
      for (var i = 0; i < allCandidates.length; i += 1) {
        var node = allCandidates[i];
        var href = compactText(node.getAttribute ? (node.getAttribute("href") || "") : "").toLowerCase();
        var text = compactText(node.textContent || "").toLowerCase();
        var cls = compactText(node.className || "").toLowerCase();
        if (href.indexOf("google") >= 0 || text.indexOf("구글") >= 0 || text.indexOf("google") >= 0 || cls.indexOf("google") >= 0) {
          found.push(node);
        }
      }
      if (!found.length) return;

      for (var j = 0; j < found.length; j += 1) {
        found[j].classList.add("smna-google-login-cta");
      }

      if (!document.getElementById("smna-google-login-guide")) {
        var guide = document.createElement("div");
        guide.id = "smna-google-login-guide";
        guide.className = "smna-google-login-guide";
        guide.textContent = "AI 계산기 이용은 로그인 후 가능합니다. 가장 빠른 방법은 구글 로그인입니다.";
        var first = found[0];
        var parent = (loginRoot.parentNode && loginRoot.parentNode.insertBefore) ? loginRoot.parentNode : loginRoot;
        parent.insertBefore(guide, loginRoot);
        if (first && first.parentNode && first.parentNode !== guide && first.tagName && first.tagName.toLowerCase() === "a") {
          var clone = first.cloneNode(true);
          clone.className = "smna-google-login-cta";
          clone.style.marginTop = "10px";
          guide.appendChild(document.createElement("br"));
          guide.appendChild(clone);
        }
      }
    } catch (_e) {}
  }

  function frameBaseByMode(mode) {
    var frameBase = mode === "acquisition" ? FRAME_ACQUISITION_URL : FRAME_CUSTOMER_URL;
    if (!frameBase) frameBase = mode === "acquisition" ? "https://seoulmna.kr/ai-license-acquisition-calculator/" : "https://seoulmna.kr/yangdo-ai-customer/";
    return String(frameBase || "");
  }

  function withFrameParams(baseUrl, sourceTag, modeTag) {
    var src = String(baseUrl || "");
    if (!src) return "";
    var hasMode = /[?&]mode=/.test(src);
    if (modeTag && !hasMode) {
      src += (src.indexOf("?") >= 0 ? "&" : "?") + "mode=" + encodeURIComponent(String(modeTag || ""));
    }
    src += (src.indexOf("?") >= 0 ? "&" : "?") + "from=" + encodeURIComponent(sourceTag || "co");
    src += "&cb=" + String(Math.floor(Date.now() / 60000));
    return src;
  }

  function calcTitleByMode(mode) {
    return mode === "acquisition" ? "AI 건설업 신규등록 비용 산정 계산기" : "AI 양도가 산정 계산기";
  }

  function syncCalculatorBodyClass(mode) {
    try {
      if (!document.body) return;
      if (mode) document.body.classList.add("smna-co-calc-bridge-mode");
      else document.body.classList.remove("smna-co-calc-bridge-mode");
    } catch (_e) {}
  }

  function hydrateSanitizedContentIframe(mode) {
    try {
      if (!mode) return false;
      var hostName = String(location.hostname || "").toLowerCase();
      if (hostName.indexOf("seoulmna.co.kr") === -1) return false;
      var frameBase = frameBaseByMode(mode);
      if (!frameBase) return false;
      var frameSrc = withFrameParams(frameBase, "co", mode);
      var candidates = document.querySelectorAll("#ctt iframe, #ctt_con iframe, article#ctt iframe");
      if (!candidates || !candidates.length) return false;
      var changed = false;
      for (var i = 0; i < candidates.length; i += 1) {
        var iframe = candidates[i];
        var src = String(iframe.getAttribute("src") || "").trim();
        if (!src) {
          iframe.setAttribute("src", frameSrc);
          changed = true;
        }
        if (!iframe.getAttribute("title")) {
          iframe.setAttribute("title", calcTitleByMode(mode));
        }
        iframe.setAttribute("loading", "eager");
        iframe.setAttribute("referrerpolicy", "strict-origin-when-cross-origin");
        iframe.style.display = "block";
        iframe.style.width = "100%";
        iframe.style.border = "0";
        if (!String(iframe.style.height || "").trim()) {
          iframe.style.height = (window.innerWidth <= 980 ? "2400px" : "2100px");
        }
      }
      return changed;
    } catch (_e) {
      return false;
    }
  }

  function ensureCalculatorJumpLink(mode) {
    try {
      if (!mode) return;
      if (document.getElementById("smna-calc-fallback-link")) return;
      var root = document.querySelector("#ctt_con, #ctt, #bo_v_con");
      if (!root) return;
      var frameBase = frameBaseByMode(mode);
      if (!frameBase) return;
      var wrap = document.createElement("div");
      wrap.id = "smna-calc-fallback-link";
      wrap.style.margin = "0 0 10px";
      wrap.style.padding = "10px 12px";
      wrap.style.border = "1px solid #d7e0ea";
      wrap.style.background = "#f8fbff";
      wrap.style.borderRadius = "10px";
      wrap.style.fontSize = "14px";
      wrap.style.lineHeight = "1.5";
      wrap.innerHTML = "<strong style='color:#003764;'>계산기 바로 열기:</strong> <a href='" + frameBase + "' target='_blank' rel='noopener noreferrer' style='color:#b87333;font-weight:800;text-decoration:none;'>" + frameBase + "</a>";
      root.insertBefore(wrap, root.firstChild || null);
    } catch (_e) {}
  }

  function runCalculatorMountPass() {
    try {
      var mode = detectCalculatorMode();
      syncCalculatorBodyClass(mode);
      if (!mode) return false;
      var bridged = mountCalculatorBridge();
      if (!bridged) {
        hydrateSanitizedContentIframe(mode);
        ensureCalculatorJumpLink(mode);
      }
      return bridged;
    } catch (_e) {
      return false;
    }
  }

  function forceCalculatorRedirectFallback(mode) {
    try {
      if (!mode) return;
      var hostName = String(location.hostname || "").toLowerCase();
      if (hostName.indexOf("seoulmna.co.kr") === -1) return;
      if (document.getElementById("smna-calc-bridge")) return;
      var hasLiveIframe = !!document.querySelector(
        '#ctt iframe[src*="yangdo-ai-customer"], #ctt iframe[src*="ai-license-acquisition-calculator"], #ctt_con iframe[src*="yangdo-ai-customer"], #ctt_con iframe[src*="ai-license-acquisition-calculator"]'
      );
      if (hasLiveIframe) return;
      var frameBase = frameBaseByMode(mode);
      if (!frameBase) return;
      var to = withFrameParams(frameBase, "co_auto_fallback", mode);
      location.replace(to);
    } catch (_e) {}
  }

  function mountCalculatorBridge() {
    try {
      var hostName = String(location.hostname || "").toLowerCase();
      if (hostName.indexOf("seoulmna.co.kr") === -1) return false;
      var mode = detectCalculatorMode();
      if (!mode) return false;
      if (document.getElementById("smna-calc-bridge")) return true;

      var target = mode === "acquisition" ? ACQUISITION_URL : TARGET_URL;
      if (!target) target = mode === "acquisition" ? "https://seoulmna.co.kr/bbs/content.php?co_id=ai_acq" : "https://seoulmna.co.kr/bbs/content.php?co_id=ai_calc";
      var frameBase = frameBaseByMode(mode);
      if (!frameBase) return false;
      var currentAbs = String(location.href || "");
      if (String(frameBase).split("#")[0] === currentAbs.split("#")[0]) return false;

      var root = document.querySelector("#bo_v_con, #ctt_con, #ctt");
      if (!root) return false;

      var style = document.getElementById("smna-calc-bridge-style");
      if (!style) {
        style = document.createElement("style");
        style.id = "smna-calc-bridge-style";
        style.textContent = ""
          + "#smna-calc-bridge{box-sizing:border-box;font-family:Pretendard,'Noto Sans KR','Malgun Gothic',Arial,sans-serif;background:#f4f7fb;border:1px solid #d7e2ee;border-radius:14px;padding:10px;max-width:1120px;margin:0 auto;margin-top:var(--smna-bridge-top-offset,24px);}"
          + "body.smna-co-calc-bridge-mode #smna-calc-bridge{margin-top:var(--smna-bridge-top-offset,24px);}"
          + "body.smna-co-calc-bridge-mode #header,body.smna-co-calc-bridge-mode #hd,body.smna-co-calc-bridge-mode #masthead,body.smna-co-calc-bridge-mode .site-header,body.smna-co-calc-bridge-mode .main-header-bar-wrap,body.smna-co-calc-bridge-mode .ast-main-header-wrap,body.smna-co-calc-bridge-mode .ast-mobile-header-wrap,body.smna-co-calc-bridge-mode .ast-primary-header-bar,body.smna-co-calc-bridge-mode .ast-site-header-wrap,body.smna-co-calc-bridge-mode #visual{display:none !important;}"
          + "body.smna-co-calc-bridge-mode #container,body.smna-co-calc-bridge-mode #contents,body.smna-co-calc-bridge-mode #wrapper{margin-top:0 !important;padding-top:0 !important;}"
          + "#smna-calc-bridge .head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 14px;min-height:62px;margin-bottom:8px;background:linear-gradient(124deg,#003764 0%,#014477 72%,#0d4f84 100%);border-radius:10px;}"
          + "#smna-calc-bridge .head-copy{flex:1 1 auto;min-width:0;display:flex;flex-direction:column;justify-content:center;}"
          + "#smna-calc-bridge .title{margin:0;font-size:20px;line-height:1.16;font-weight:900;color:#f8fbff;display:block;}"
          + "#smna-calc-bridge .meta{margin:3px 0 0;font-size:13px;line-height:1.35;color:#e3f0fc;}"
          + "#smna-calc-bridge .open{display:inline-flex;flex:0 0 auto;align-items:center;justify-content:center;padding:8px 12px;min-height:40px;height:40px;line-height:1;border-radius:9px;background:#ffffff;color:#003764;text-decoration:none;font-weight:800;white-space:nowrap;box-shadow:0 1px 0 rgba(0,0,0,.08);}"
          + "#smna-calc-bridge iframe{display:block;width:100%;border:0;border-radius:10px;background:#fff;}"
          + "@media(max-width:980px){body.smna-co-calc-bridge-mode #smna-calc-bridge{margin-top:var(--smna-bridge-top-offset,16px);}#smna-calc-bridge{padding:8px;border-radius:10px;max-width:100%;}#smna-calc-bridge .head{padding:9px 10px;min-height:56px;gap:8px;}#smna-calc-bridge .title{font-size:17px;line-height:1.2;}#smna-calc-bridge .meta{font-size:12px;line-height:1.32;}#smna-calc-bridge .open{min-height:34px;height:34px;padding:6px 10px;font-size:13px;}}";
        document.head.appendChild(style);
      }

      var frameSrc = withFrameParams(frameBase, "co", mode);
      var titleText = calcTitleByMode(mode);

      var wrap = document.createElement("section");
      wrap.id = "smna-calc-bridge";
      wrap.innerHTML = ""
        + "<div class='head'>"
        + "  <div class='head-copy'>"
        + "    <div class='title'>" + titleText + "</div>"
        + "    <div class='meta'>서울건설정보 계산기 화면을 안전 모드로 표시합니다.</div>"
        + "  </div>"
        + "  <a class='open' href='https://seoulmna.co.kr/mna'>전체 매물 페이지</a>"
        + "</div>";
      var iframe = document.createElement("iframe");
      iframe.setAttribute("title", titleText);
      iframe.setAttribute("src", frameSrc);
      iframe.setAttribute("loading", "eager");
      iframe.setAttribute("referrerpolicy", "strict-origin-when-cross-origin");

      var resizeFrame = function() {
        var h = window.innerWidth <= 980 ? 2400 : 2100;
        iframe.style.height = String(h) + "px";
        applyBridgeTopOffset();
      };
      resizeFrame();
      window.addEventListener("resize", resizeFrame);

      wrap.appendChild(iframe);
      root.innerHTML = "";
      root.appendChild(wrap);
      applyBridgeTopOffset();
      setTimeout(applyBridgeTopOffset, 120);
      setTimeout(applyBridgeTopOffset, 640);
      return true;
    } catch (e) {
      if (window.console && console.warn) console.warn("[smna-bridge] mount failed", e);
      return false;
    }
  }

  function mountBanner() {
    try {
      var hostName = String(location.hostname || "").toLowerCase();
      if (hostName.indexOf("seoulmna.co.kr") === -1) return;
      if (document.getElementById("smna-global-banner-rail")) return;
      if (isMainPath()) {
        if (!shouldShowMainBanner()) return;
      } else {
        if (!shouldShowGlobalBanner()) return;
      }

      var style = document.createElement("style");
      style.id = "smna-global-banner-style";
      style.textContent = ""
        + "#smna-global-banner-rail{box-sizing:border-box;font-family:Pretendard,'Noto Sans KR','Malgun Gothic',Arial,sans-serif;"
        + "width:220px;border-radius:14px;padding:13px;background:linear-gradient(130deg,#003764 0%,#014477 70%,#0d4f84 100%);"
        + "color:#fff;box-shadow:0 10px 22px rgba(0,26,46,.24);border:1px solid rgba(255,255,255,.18);z-index:6000;}"
        + "#smna-global-banner-rail *{box-sizing:border-box;}"
        + "#smna-global-banner-rail .autobalance{transition:text-align .16s ease;}"
        + "#smna-global-banner-rail.align-left .autobalance{text-align:left;}"
        + "#smna-global-banner-rail.align-center .autobalance{text-align:center;}"
        + "#smna-global-banner-rail.align-right .autobalance{text-align:right;}"
        + "#smna-global-banner-rail .brandline{font-size:16px;font-weight:900;line-height:1.2;color:#e8f3ff;margin-bottom:6px;letter-spacing:.01em;}"
        + "#smna-global-banner-rail .badge{display:inline-block;background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.38);"
        + "border-radius:999px;padding:3px 8px;font-size:11px;font-weight:800;margin-bottom:6px;}"
        + "#smna-global-banner-rail .title{font-size:29px;font-weight:900;line-height:1.08;letter-spacing:-.015em;margin-bottom:8px;}"
        + "#smna-global-banner-rail .desc{font-size:16px;line-height:1.42;color:#e7f2fc;margin-bottom:10px;word-break:keep-all;}"
        + "#smna-global-banner-rail .sub{font-size:13px;line-height:1.4;color:#d9e8f5;margin-bottom:10px;word-break:keep-all;display:flex;flex-wrap:wrap;align-items:center;gap:2px 6px;}"
        + "#smna-global-banner-rail.align-left .sub{justify-content:flex-start;}"
        + "#smna-global-banner-rail.align-center .sub{justify-content:center;}"
        + "#smna-global-banner-rail.align-right .sub{justify-content:flex-end;}"
        + "#smna-global-banner-rail .sub .sub-chat{white-space:normal;display:inline-block;max-width:100%;}"
        + "#smna-global-banner-rail .sub .sub-sep{opacity:.78;}"
        + "#smna-global-banner-rail .sub .sub-phone{font-weight:900;white-space:nowrap;color:#f4fbff;letter-spacing:.01em;}"
        + "#smna-global-banner-rail .sub-openchat{font-size:13px;line-height:1.35;color:#ffe3b8;margin:-6px 0 10px;}"
        + "#smna-global-banner-rail .sub-openchat a{color:#ffe3b8;text-decoration:underline;text-underline-offset:2px;font-weight:900;}"
        + "#smna-global-banner-rail .sub.stacked{display:grid;grid-template-columns:1fr;gap:2px;}"
        + "#smna-global-banner-rail .sub.stacked .sub-sep{display:none;}"
        + "#smna-global-banner-rail .actions{display:flex;flex-direction:column;gap:7px;}"
        + "#smna-global-banner-rail .btn{display:flex;align-items:center;justify-content:center;padding:9px 10px;border-radius:10px;"
        + "text-decoration:none;font-weight:900;font-size:17px;line-height:1.2;border:1px solid transparent;}"
        + "#smna-global-banner-rail .btn-main{background:#fff;color:#003764;}"
        + "#smna-global-banner-rail .btn-sub{background:#e8eef5;color:#0b3d66;}"
        + "#smna-global-banner-rail .btn-chat{background:#b87333;color:#fff;border-color:#a5652d;}"
        + "@media (prefers-reduced-motion: reduce){#smna-global-banner-rail .autobalance,#smna-global-banner-rail .btn{transition:none!important;}}"
        + "#smna-banner-mount{position:relative;display:block;margin-top:12px;}"
        + "#smna-banner-mount.sticky{position:sticky;top:100px;z-index:6000;}"
        + "#smna-banner-mount.fixed{position:fixed;right:14px;top:120px;z-index:6000;}"
        + "@media(max-width:1100px){#smna-global-banner-rail{width:204px;padding:11px;}#smna-global-banner-rail .title{font-size:26px;}#smna-global-banner-rail .btn{font-size:16px;}}"
        + "@media(max-width:980px){#smna-banner-mount,#smna-global-banner-rail{display:none !important;}}";
      document.head.appendChild(style);

      var quickMenu = document.querySelector("#right-side .quick_menu, #right-side #quicks, .quick_menu");
      var quickRect = null;
      var quickVisible = false;
      try {
        if (quickMenu && quickMenu.getBoundingClientRect) {
          quickRect = quickMenu.getBoundingClientRect();
          quickVisible = quickRect.right > 0 && quickRect.left < (window.innerWidth - 24);
        }
      } catch (_e) {}
      var mount = document.createElement("div");
      mount.id = "smna-banner-mount";

      var rail = document.createElement("aside");
      rail.id = "smna-global-banner-rail";
      var chatBtn = KAKAO_OPENCHAT_URL ? '<a class="btn btn-chat" href="' + KAKAO_OPENCHAT_URL + '" target="_blank" rel="noopener noreferrer">1:1 직접 상담</a>' : "";
      var subOpenchat = KAKAO_OPENCHAT_URL ? '<div class="sub-openchat autobalance"><a href="' + KAKAO_OPENCHAT_URL + '" target="_blank" rel="noopener noreferrer">오픈채팅 바로가기</a></div>' : "";
      rail.innerHTML = ""
        + '<div class="badge">전국 최초</div>'
        + '<div class="brandline autobalance">서울건설정보</div>'
        + '<div class="title autobalance">AI 양도가 산정 계산기</div>'
        + '<div class="sub autobalance"><span class="sub-chat">대표 행정사 1:1 직접 상담</span><span class="sub-sep">/</span><span class="sub-phone">' + CONTACT_PHONE + "</span></div>"
        + subOpenchat
        + '<div class="desc autobalance">건설업 전 면허 양도양수·분할합병 예정 고객이라면, 예상 양도가 범위를 먼저 확인하세요.</div>'
        + '<div class="actions">'
        + '  <a class="btn btn-main smna-calc-link" data-smna-calc-link="1" href="' + TARGET_URL + '">양도가 계산</a>'
        + (ACQUISITION_URL ? '  <a class="btn btn-sub smna-calc-link" data-smna-calc-link="1" href="' + ACQUISITION_URL + '">신규등록 비용 계산</a>' : "")
        + chatBtn
        + "</div>";
      mount.appendChild(rail);
      applyBannerTextBalance(rail);
      setTimeout(function(){ applyBannerTextBalance(rail); }, 40);
      setTimeout(function(){ applyBannerTextBalance(rail); }, 260);
      window.addEventListener("resize", function() { applyBannerTextBalance(rail); });

      if (quickMenu && quickMenu.parentNode && quickVisible) {
        mount.className = "sticky";
        if (quickMenu.nextSibling) {
          quickMenu.parentNode.insertBefore(mount, quickMenu.nextSibling);
        } else {
          quickMenu.parentNode.appendChild(mount);
        }
      } else {
        mount.className = "fixed";
        document.body.appendChild(mount);
      }
    } catch (e) {
      if (window.console && console.warn) console.warn("[smna-banner] mount failed", e);
    }
  }

  function boot() {
    var mode = detectCalculatorMode();
    var mainPath = isMainPath();
    var bridged = mode ? runCalculatorMountPass() : false;
    if (!mainPath) {
      stabilizeHeaderAndNav();
      if (bridged) applyBridgeTopOffset();
    }
    rewriteFooterCopyright();
    ensureKakaoOpenChatLink();
    enhanceQuickMenu();
    sanitizeUtilityLinks();
    applyLoginGateToCalculatorLinks(document);
    enhanceLoginPageGoogleCta();
    if (!bridged) {
      mountBanner();
      applyLoginGateToCalculatorLinks(document);
    }
    if (!mainPath) dedupeMnaMobileList();
    setTimeout(rewriteFooterCopyright, 1200);
    setTimeout(ensureKakaoOpenChatLink, 1200);
    setTimeout(enhanceQuickMenu, 160);
    setTimeout(enhanceQuickMenu, 960);
    setTimeout(sanitizeUtilityLinks, 180);
    setTimeout(sanitizeUtilityLinks, 980);
    setTimeout(function() { applyLoginGateToCalculatorLinks(document); }, 260);
    setTimeout(function() { applyLoginGateToCalculatorLinks(document); }, 1200);
    setTimeout(enhanceLoginPageGoogleCta, 180);
    setTimeout(enhanceLoginPageGoogleCta, 1200);
    if (mode) {
      setTimeout(stabilizeHeaderAndNav, 220);
      setTimeout(stabilizeHeaderAndNav, 1200);
      setTimeout(applyBridgeTopOffset, 260);
      setTimeout(applyBridgeTopOffset, 1200);
      setTimeout(runCalculatorMountPass, 500);
      setTimeout(runCalculatorMountPass, 1400);
      setTimeout(runCalculatorMountPass, 3000);
      setTimeout(function() { forceCalculatorRedirectFallback(mode); }, 4200);
    }
    if (!mainPath) {
      setTimeout(dedupeMnaMobileList, 600);
      setTimeout(dedupeMnaMobileList, 1800);
    }
    try {
      if (mode && !window.__smna_mna_observer__) {
        window.__smna_mna_observer__ = new MutationObserver(function() {
          if (window.__smna_observe_timer__) return;
          window.__smna_observe_timer__ = window.setTimeout(function() {
            window.__smna_observe_timer__ = 0;
            stabilizeHeaderAndNav();
            dedupeMnaMobileList();
            runCalculatorMountPass();
            sanitizeUtilityLinks();
            applyLoginGateToCalculatorLinks(document);
            enhanceLoginPageGoogleCta();
          }, 220);
        });
        window.__smna_mna_observer__.observe(document.body, { childList: true, subtree: true });
      }
    } catch (_e) {}
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
</script>
<!-- SEOULMNA GLOBAL BANNER END -->"""
    return (
        template.replace("__TARGET__", repr(target))
        .replace("__ACQUISITION__", repr(acquisition))
        .replace("__FRAME_CUSTOMER__", repr(frame_customer))
        .replace("__FRAME_ACQUISITION__", repr(frame_acquisition))
        .replace("__KAKAO__", repr(kakao))
        .replace("__PHONE__", repr(phone))
        .replace("__SHOW_MAIN_BANNER__", "true" if show_main_banner else "false")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate seoulmna.co.kr global banner snippet for admin config")
    parser.add_argument("--target-url", default="https://seoulmna.co.kr/bbs/content.php?co_id=ai_calc")
    parser.add_argument("--acquisition-url", default="https://seoulmna.co.kr/bbs/content.php?co_id=ai_acq")
    parser.add_argument("--frame-customer-url", default="")
    parser.add_argument("--frame-acquisition-url", default="")
    parser.add_argument("--kakao-openchat-url", default="")
    parser.add_argument("--contact-phone", default="")
    parser.add_argument("--show-main-banner", action="store_true", help="Show banner on main page (default: hidden until manually enabled)")
    parser.add_argument("--snippet-out", default="logs/co_global_banner_snippet.html")
    parser.add_argument("--guide-out", default="logs/co_global_banner_apply_guide.md")
    args = parser.parse_args()

    env = _read_env(ROOT / ".env")
    kakao_openchat_url = str(args.kakao_openchat_url or "").strip() or str(env.get("KAKAO_OPENCHAT_URL", "")).strip()
    contact_phone = (
        str(args.contact_phone or "").strip()
        or str(env.get("CALCULATOR_CONTACT_PHONE", "")).strip()
        or str(env.get("PHONE", "") or env.get("MY_PHONE", "")).strip()
        or "010-9926-8661"
    )
    if "1668" in str(contact_phone):
        contact_phone = "010-9926-8661"
    snippet = build_banner_snippet(
        str(args.target_url).strip(),
        acquisition_url=str(args.acquisition_url).strip(),
        frame_customer_url=str(args.frame_customer_url).strip() or str(env.get("GAS_YANGDO_WEBAPP_URL", "")).strip(),
        frame_acquisition_url=str(args.frame_acquisition_url).strip() or str(env.get("GAS_ACQUISITION_WEBAPP_URL", "")).strip(),
        kakao_openchat_url=kakao_openchat_url,
        contact_phone=contact_phone,
        show_main_banner=bool(args.show_main_banner),
    )
    snippet_path = (ROOT / args.snippet_out).resolve()
    guide_path = (ROOT / args.guide_out).resolve()

    snippet_path.parent.mkdir(parents=True, exist_ok=True)
    snippet_path.write_text(snippet, encoding="utf-8")

    guide = [
        f"# co.kr 전역 배너 적용 가이드 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})",
        "",
        "1. seoulmna.co.kr 관리자 로그인",
        "2. 환경설정 > 기본환경설정 이동",
        "3. 추가 script(또는 공통 head/footer script)에 아래 파일 내용을 붙여넣기",
        f"   - {snippet_path}",
        "4. 메인/게시판/상세 페이지에서 배너 노출 확인",
        "",
        "배너 동작:",
        "- 닫기: 현재 페이지에서 즉시 닫기",
        "- 오늘 그만 보기: 24시간 숨김(localStorage)",
        "- 전체 페이지 배너: 기본 숨김. 임시 표시 `?smna_banner=1`, 다시 숨김 `?smna_banner=0`",
        "- 메인 배너: 기본 숨김(요청 전까지). 임시 표시 `?smna_main_banner=1`, 다시 숨김 `?smna_main_banner=0`",
        "- 계산기 링크: 비로그인 시 `/bbs/login.php`로 먼저 이동 후 계산기 페이지로 복귀",
        "- 로그인 화면: 구글 로그인 버튼 자동 강조",
        "",
        "타겟 링크:",
        f"- {args.target_url}",
        f"- {args.acquisition_url}",
        "",
        "카카오 오픈채팅 삽입:",
        f"- URL: {kakao_openchat_url or '(미설정)'}",
        f"- 대표전화: {contact_phone}",
        "- footer 대표전화 하단에 자동 삽입 시도",
    ]
    guide_path.write_text("\n".join(guide) + "\n", encoding="utf-8")

    print(f"[snippet] {snippet_path}")
    print(f"[guide] {guide_path}")
    print(f"[kakao_openchat] {kakao_openchat_url or 'EMPTY'}")
    print(f"[contact_phone] {contact_phone}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
