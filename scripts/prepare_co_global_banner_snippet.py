import argparse
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_env(path: Path):
    out = {}
    if not path.exists():
        return out
    text = ""
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            text = path.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if not text:
        text = path.read_text(encoding="utf-8", errors="replace")
    for raw in text.splitlines():
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
  var FOOTER_LINE_1 = "주소 : 서울시 영등포구 국제금융로 8길 27-8 NH농협캐피탈 빌딩 4층";
  var FOOTER_LINE_2 = "대표 : 강지현 | 사업자등록번호 :781-01-02142 | 통신판매업신고번호 : 2023-서울강남-04297";
  var FOOTER_LINE_3 = "TEL 010-9926-8661 | FAX 02-6958-9848 | 이메일 : rkdwlgus586@nate.com";
  var TOP_NAV_LABEL_MAP = {
    "/mna": "양도매물",
    "/pages/n1s.php": "신규등록",
    "/pages/bs1.php": "법인설립",
    "/pages/h1.php": "분할합병",
    "/pages/ks2.php": "건설실무",
    "/notice": "상담센터"
  };
  var QUICK_MENU_LINK_MAP = {};
  var ENABLE_MNA_FAVORITES = false;
  var RELATED_ORG_LINKS = [
    { label: "대한건설협회", href: "https://www.cak.or.kr/" },
    { label: "대한전문건설협회", href: "https://www.kosca.or.kr/" },
    { label: "대한기계설비건설협회", href: "https://www.kmcca.or.kr/main.do" },
    { label: "시설물유지관리협회", href: "https://search.naver.com/search.naver?query=시설물유지관리협회" },
    { label: "대한주택건설협회", href: "https://www.khba.or.kr/khbaGo.do" },
    { label: "한국전기공사협회", href: "https://www.keca.or.kr/" },
    { label: "한국정보통신공사협회", href: "https://www.kica.or.kr/" },
    { label: "한국부동산개발협회", href: "https://www.koda.or.kr/" },
    { label: "한국소방시설협회", href: "https://www.ekffa.or.kr/" },
    { label: "한국건설기술인협회", href: "https://www.kocea.or.kr/" },
    { label: "한국엔지니어링협회", href: "https://www.keea.or.kr/" },
    { label: "건설공제조합", href: "https://www.cgbest.co.kr/" },
    { label: "전문건설공제조합", href: "https://www.kfinco.co.kr/" },
    { label: "기계설비건설공제조합", href: "https://www.seolbi.com/" },
    { label: "전기공사공제조합", href: "https://www.ecfc.co.kr/" },
    { label: "정보통신공제조합", href: "https://www.icfc.or.kr/" },
    { label: "소방산업공제조합", href: "https://www.figu.or.kr/" },
    { label: "KISCON", href: "https://www.kiscon.net/" },
    { label: "국토교통부", href: "https://www.molit.go.kr/" }
  ];

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
      var favGuide = document.getElementById("smna-fav-guide");
      if (favGuide && favGuide.parentNode) favGuide.parentNode.removeChild(favGuide);
      var favGuideStyle = document.getElementById("smna-fav-guide-style");
      if (favGuideStyle && favGuideStyle.parentNode) favGuideStyle.parentNode.removeChild(favGuideStyle);

      function _isProtectedFooterLine(txt) {
        return /(주소|대표|사업자|통신판매업|TEL|FAX|이메일|개인정보처리방침|오시는 길|LOGIN|quick|퀵)/i.test(String(txt || ""));
      }
      function _collectFooterRoots() {
        var roots = document.querySelectorAll("#ft, #footers, footer, .footer");
        if (roots && roots.length) return roots;
        return [];
      }

      var footerRoots = _collectFooterRoots();
      var hardTargets = [];
      for (var fr = 0; fr < footerRoots.length; fr += 1) {
        var root = footerRoots[fr];
        if (!root) continue;
        var targetsInRoot = root.querySelectorAll(".copyright a[href*='mnahompy.com'], .copyright img[src*='home.png'], .copy a[href*='mnahompy.com'], .copy img[src*='home.png'], a[href*='mnahompy.com']");
        for (var ti = 0; ti < targetsInRoot.length; ti += 1) hardTargets.push(targetsInRoot[ti]);
      }

      for (var h = 0; h < hardTargets.length; h += 1) {
        var target = hardTargets[h];
        if (!target) continue;
        var box = target.closest(".copyright, .copy, p, li, span, small") || target;
        if (!box || !box.parentNode) continue;
        var boxTxt = compactText(box.textContent || "");
        if (_isProtectedFooterLine(boxTxt)) continue;
        if (boxTxt.length > 280) continue;
        if (!/(0404|Association|mnahompy|copyright)/i.test(boxTxt)) continue;
        if (/^(p|li|span|small)$/i.test(box.tagName || "")) {
          box.style.display = "none";
          box.setAttribute("data-smna-legacy-copyright-hidden", "1");
        } else if (/^a$/i.test(target.tagName || "")) {
          target.style.display = "none";
          target.setAttribute("data-smna-legacy-copyright-hidden", "1");
        }
      }

      var nodes = [];
      for (var r = 0; r < footerRoots.length; r += 1) {
        var scope = footerRoots[r];
        if (!scope) continue;
        var scopedNodes = scope.querySelectorAll(".copyright, .copy, p, li, span, small");
        for (var sn = 0; sn < scopedNodes.length; sn += 1) nodes.push(scopedNodes[sn]);
      }
      var changed = false;
      var patt = /COPYRIGHT\\s*[©c]?\\s*2018[^\\n]{0,220}?(?:0404|Association|mnahompy)[^\\n]{0,260}?ALL\\s*RIGHTS\\s*RESERVED\\.?/i;
      for (var i = 0; i < nodes.length; i += 1) {
        var n = nodes[i];
        if (!n || !n.parentNode) continue;
        var txt = String(n.textContent || "").replace(/\\s+/g, " ").trim();
        if (!txt || txt.length > 480) continue;
        if (_isProtectedFooterLine(txt)) continue;
        var matched = patt.test(txt) || (txt.indexOf("0404 Association") >= 0 && /COPYRIGHT/i.test(txt));
        if (!matched) continue;
        var cleaned = matched ? txt.replace(patt, "").replace(/\\s{2,}/g, " ").trim() : "";
        if (!cleaned || cleaned === txt) {
          if (/^(p|li|span|small)$/i.test(n.tagName || "")) {
            n.style.display = "none";
            n.setAttribute("data-smna-legacy-copyright-hidden", "1");
          }
        } else {
          n.textContent = cleaned;
        }
        changed = true;
      }
      return changed || hardTargets.length > 0;
    } catch (_e) {
      return false;
    }
  }
  function ensureFooterBusinessIdentity() {
    try {
      var desired = [FOOTER_LINE_1, FOOTER_LINE_2, FOOTER_LINE_3];
      var footer = document.querySelector("#ft address, #footers address, footer address, address");
      var footerInfo = document.querySelector("#footers .footer_in, #ft .footer_in, footer .footer_in");
      var changed = false;
      var contrastStyle = document.getElementById("smna-footer-contrast-style");
      if (!contrastStyle) {
        contrastStyle = document.createElement("style");
        contrastStyle.id = "smna-footer-contrast-style";
        contrastStyle.textContent = ""
          + "#footers .footer_in,#ft .footer_in,#footers address,#ft address,footer .footer_in,footer address{color:#eaf4ff !important;}"
          + "#footers .footer_in a,#ft .footer_in a,footer .footer_in a{color:#ffffff !important;text-decoration:underline;text-underline-offset:2px;}"
          + ".smna-ft-links{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 8px;}"
          + ".smna-ft-btn{display:inline-flex;align-items:center;justify-content:center;padding:3px 9px;border-radius:999px;border:1px solid rgba(208,227,245,.86);background:rgba(255,255,255,.14);font-size:12px;line-height:1.3;font-weight:800;color:#fff !important;text-decoration:none !important;}";
        document.head.appendChild(contrastStyle);
      }

      if (footer) {
        var allTxt = compactText(footer.textContent || "");
        var hasAll = true;
        for (var i = 0; i < desired.length; i += 1) {
          if (allTxt.indexOf(compactText(desired[i])) < 0) {
            hasAll = false;
            break;
          }
        }
        if (!hasAll || footer.querySelectorAll(".adr").length < 3) {
          footer.innerHTML = "";
          for (var k = 0; k < desired.length; k += 1) {
            var span = document.createElement("span");
            span.className = "adr";
            span.textContent = desired[k];
            footer.appendChild(span);
          }
          changed = true;
        }
        footer.style.color = "#eaf4ff";
        footer.style.lineHeight = "1.55";
      }

      if (footerInfo) {
        var infoText = compactText(footerInfo.textContent || "");
        var needsNormalize = infoText.indexOf(compactText(FOOTER_LINE_1)) < 0
          || infoText.indexOf(compactText(FOOTER_LINE_2)) < 0
          || infoText.indexOf(compactText(FOOTER_LINE_3)) < 0;
        var lf = String.fromCharCode(10);
        if (footerInfo.textContent.indexOf(lf) < 0) needsNormalize = true;
        if (footerInfo.querySelectorAll("a").length < 3) needsNormalize = true;
        for (var n = 0; n < desired.length; n += 1) {
          if (infoText.indexOf(compactText(desired[n])) < 0) needsNormalize = true;
        }
        if (needsNormalize) {
          footerInfo.style.whiteSpace = "normal";
          footerInfo.style.lineHeight = "1.55";
          footerInfo.innerHTML = '<div class="smna-ft-links"><a class="smna-ft-btn" href="https://seoulmna.co.kr/pages/privacy.php">개인정보처리방침</a><a class="smna-ft-btn" href="https://seoulmna.co.kr/pages/map.php">오시는 길</a><a class="smna-ft-btn" href="https://seoulmna.co.kr/bbs/login.php">LOGIN</a></div><div>' + _escapeHtml(FOOTER_LINE_1) + "</div><div>" + _escapeHtml(FOOTER_LINE_2) + "</div><div>" + _escapeHtml(FOOTER_LINE_3) + "</div>";
          changed = true;
        }
        footerInfo.style.color = "#eaf4ff";
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

  function sanitizeUtilityLinks() {
    try {
      // Avoid hiding login/admin utility links globally.
      // Only collapse truly empty top utility wrappers to prevent blank bars.
      var wraps = document.querySelectorAll(".top_util, .util_menu, .quick_top, .tnb");
      for (var i = 0; i < wraps.length; i += 1) {
        var w = wraps[i];
        if (!w || !w.parentNode) continue;
        var txt = compactText(w.textContent || "");
        if (!txt) {
          w.style.display = "none";
        }
      }
    } catch (_e) {}
  }

  function mountRelatedOrganizationsCenter(entries) {
    try {
      var host = document.getElementById("smna-generated-right-side");
      if (!host) return;
      var wrap = document.getElementById("smna-related-orgs");
      if (!wrap) {
        wrap = document.createElement("section");
        wrap.id = "smna-related-orgs";
        host.appendChild(wrap);
      }

      var pool = [];
      function pushItem(label, href) {
        var t = compactText(label || "");
        var u = normalizeOutboundUrl(href || "");
        if (!t || !u) return;
        if (u.indexOf("javascript:") === 0) return;
        var key = t + "::" + u;
        for (var i = 0; i < pool.length; i += 1) {
          if (pool[i].key === key) return;
        }
        pool.push({ key: key, label: t, href: u });
      }

      for (var j = 0; j < RELATED_ORG_LINKS.length; j += 1) pushItem(RELATED_ORG_LINKS[j].label, RELATED_ORG_LINKS[j].href);
      var src = Array.isArray(entries) ? entries : [];
      for (var s = 0; s < src.length; s += 1) pushItem(src[s].label, src[s].href);
      var items = pool.slice(0);
      if (!items.length) {
        if (wrap.parentNode) wrap.parentNode.removeChild(wrap);
        return;
      }

      var links = "";
      for (var k = 0; k < items.length; k += 1) {
        links += '<a class="smna-rel-link" href="' + _escapeHtml(items[k].href) + '" target="_blank" rel="noopener noreferrer">' + _escapeHtml(items[k].label) + "</a>";
      }
      wrap.innerHTML = '<strong class="smna-rel-title">유관기관</strong><div class="smna-rel-grid">' + links + "</div>";
    } catch (_e) {}
  }

  function _fitQuickMenuByLongestBlock() {
    try {
      var host = document.getElementById("smna-generated-right-side");
      if (!host) return;
      var qwrap = host.querySelector(".smna-qwrap");
      if (!qwrap) return;
      var relWrap = document.getElementById("smna-related-orgs");

      var probe = document.getElementById("smna-quick-size-probe");
      if (!probe) {
        probe = document.createElement("span");
        probe.id = "smna-quick-size-probe";
        probe.style.position = "absolute";
        probe.style.left = "-9999px";
        probe.style.top = "-9999px";
        probe.style.visibility = "hidden";
        probe.style.whiteSpace = "nowrap";
        probe.style.padding = "0";
        probe.style.margin = "0";
        document.body.appendChild(probe);
      }
      function textWidth(text, fontSpec) {
        var t = compactText(text || "");
        if (!t) return 0;
        probe.style.font = fontSpec;
        probe.textContent = t;
        return Math.ceil(probe.getBoundingClientRect().width || 0);
      }

      var maxMain = 0;
      var maxSub = 0;
      var qbtns = qwrap.querySelectorAll(".smna-qbtn");
      for (var i = 0; i < qbtns.length; i += 1) {
        var btn = qbtns[i];
        var subNode = btn.querySelector(".sub");
        var subTxt = compactText(subNode ? (subNode.textContent || "") : "");
        var mainTxt = compactText(btn.textContent || "");
        if (subTxt) mainTxt = compactText(mainTxt.replace(subTxt, ""));
        maxMain = Math.max(maxMain, textWidth(mainTxt, "900 18px 'Noto Sans KR', sans-serif"));
        maxSub = Math.max(maxSub, textWidth(subTxt, "800 13px 'Noto Sans KR', sans-serif"));
      }

      var maxRel = 0;
      var relLinks = relWrap ? relWrap.querySelectorAll(".smna-rel-link") : [];
      for (var j = 0; j < relLinks.length; j += 1) {
        maxRel = Math.max(maxRel, textWidth(relLinks[j].textContent || "", "800 11px 'Noto Sans KR', sans-serif"));
      }

      var qbtnInner = Math.max(190, maxMain + 22, maxSub + 20);
      var relInner = Math.max(124, maxRel + 18);
      var contentInner = Math.max(qbtnInner, relInner);
      var qwrapWidth = Math.max(206, Math.min(260, contentInner + 14));
      var hostWidth = Math.max(238, Math.min(292, qwrapWidth + 20));

      host.style.width = hostWidth + "px";
      qwrap.style.width = qwrapWidth + "px";
      qwrap.style.margin = "0 auto";

      if (relWrap) {
        var relWrapWidth = Math.max(138, Math.min(qwrapWidth - 10, relInner + 10));
        var relLinkWidth = Math.max(126, relWrapWidth - 14);
        relWrap.style.width = relWrapWidth + "px";
        for (var k = 0; k < relLinks.length; k += 1) {
          relLinks[k].style.width = relLinkWidth + "px";
          relLinks[k].style.maxWidth = relLinkWidth + "px";
          relLinks[k].style.whiteSpace = "nowrap";
          relLinks[k].style.margin = "0 auto";
        }
      }
    } catch (_e) {}
  }

  function _isMnaListContext() {
    try {
      var path = String(location.pathname || "").toLowerCase();
      var q = new URLSearchParams(location.search || "");
      var bo = String(q.get("bo_table") || "").toLowerCase();
      if (path.indexOf("/mna/") === 0) return false;
      if (path === "/mna" || path.indexOf("/mna") === 0) return true;
      if (path.indexOf("/bbs/board.php") === 0 && bo === "mna") return true;
      return false;
    } catch (_e) {
      return false;
    }
  }

  function _applyMnaListQuickPolicy() {
    try {
      var host = document.getElementById("smna-generated-right-side");
      var wrap = document.getElementById("smna-related-orgs");
      if (!host || !wrap) return;
      var qwrap = host.querySelector(".smna-qwrap");
      if (!qwrap) return;
      var listMode = _isMnaListContext();
      var toggle = document.getElementById("smna-org-toggle");

      if (!listMode) {
        host.removeAttribute("data-smna-org-collapsed");
        wrap.style.display = "";
        if (toggle && toggle.parentNode) toggle.parentNode.removeChild(toggle);
        return;
      }

      if (!toggle) {
        toggle = document.createElement("button");
        toggle.id = "smna-org-toggle";
        toggle.type = "button";
        toggle.className = "smna-org-toggle";
        if (wrap.parentNode === qwrap) qwrap.insertBefore(toggle, wrap);
        else qwrap.appendChild(toggle);
        toggle.addEventListener("click", function() {
          var collapsed = host.getAttribute("data-smna-org-collapsed") !== "0";
          host.setAttribute("data-smna-org-collapsed", collapsed ? "0" : "1");
          _applyMnaListQuickPolicy();
        });
      }
      if (!host.hasAttribute("data-smna-org-collapsed")) {
        host.setAttribute("data-smna-org-collapsed", "1");
      }
      var collapsedNow = host.getAttribute("data-smna-org-collapsed") !== "0";
      toggle.textContent = collapsedNow ? "유관기관 펼치기" : "유관기관 숨기기";
      wrap.style.display = collapsedNow ? "none" : "block";
    } catch (_e) {}
  }

  function blockLegacyQuickMenu() {
    try {
      var generated = document.getElementById("smna-generated-right-side");
      var generatedReady = !!(generated && generated.querySelector(".smna-qbtn"));
      if (!generatedReady) return;

      var style = document.getElementById("smna-legacy-quick-block-style");
      if (!style) {
        style = document.createElement("style");
        style.id = "smna-legacy-quick-block-style";
        style.textContent = ""
          + "#quick,#quicks{display:none !important;visibility:hidden !important;opacity:0 !important;pointer-events:none !important;}"
          + "#right-side .quick_menu,#right-side #quicks,#right-side #bookmark,#right-side .book_mark,#right-side .favorite,.quick_menu,.book_mark,.favorite{display:none !important;}"
          + "#smna-generated-right-side{display:block !important;visibility:visible !important;opacity:1 !important;pointer-events:auto !important;}";
        document.head.appendChild(style);
      }

      var roots = document.querySelectorAll("#quick, #quicks, #right-side .quick_menu, #right-side #quicks, #right-side #bookmark, #right-side .book_mark, #right-side .favorite");
      for (var i = 0; i < roots.length; i += 1) {
        var n = roots[i];
        if (!n || n.id === "smna-generated-right-side") continue;
        n.setAttribute("data-smna-legacy-quick-blocked", "1");
        n.style.setProperty("display", "none", "important");
        n.style.setProperty("visibility", "hidden", "important");
        n.style.setProperty("opacity", "0", "important");
        n.style.setProperty("pointer-events", "none", "important");
      }
    } catch (_e) {}
  }
  function enhanceQuickMenu() {
    try {
      blockLegacyQuickMenu();
      var style = document.getElementById("smna-quick-menu-style");
      if (!style) {
        style = document.createElement("style");
        style.id = "smna-quick-menu-style";
        style.textContent = ""
          + "#smna-generated-right-side{position:fixed;right:12px;top:170px;width:264px;z-index:99998;}"
          + "#smna-generated-right-side .smna-qwrap{padding:10px;border-radius:14px;background:linear-gradient(156deg,#003764 0%,#0d4f84 80%);border:1px solid rgba(255,255,255,.2);box-shadow:0 14px 28px rgba(0,31,58,.32);}"
          + "#smna-generated-right-side .smna-qttl{display:block;margin:0 0 8px;color:#d7e9fb;font-size:11px;font-weight:900;letter-spacing:.08em;}"
          + "#smna-generated-right-side .smna-qbtn{display:block;margin:0 0 8px;padding:11px 9px;border-radius:11px;border:1px solid #d7e3ef;background:#fff;color:#063a62;text-decoration:none;font-size:18px;line-height:1.22;font-weight:900;text-align:center;word-break:keep-all;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
          + "#smna-generated-right-side .smna-qbtn .sub{display:block;margin-top:2px;font-size:13px;line-height:1.3;color:#4e6b85;font-weight:800;}"
          + "#smna-generated-right-side .smna-qbtn.kakao{background:linear-gradient(135deg,#fee500,#ffd43f);border-color:#e0c118;color:#2d2500;}"
          + "#smna-generated-right-side .smna-qbtn:last-child{margin-bottom:0;}"
          + "#smna-generated-right-side .smna-org-toggle{display:block;width:100%;margin:10px 0 0;padding:8px 9px;border-radius:10px;border:1px solid rgba(203,228,250,.45);background:rgba(19,74,120,.68);color:#e8f4ff;font-size:12px;line-height:1.25;font-weight:900;cursor:pointer;}"
          + "#smna-generated-right-side .smna-org-toggle:hover,#smna-generated-right-side .smna-org-toggle:focus-visible{background:rgba(34,102,157,.8);outline:0;}"
          + "#smna-generated-right-side #smna-related-orgs{width:232px;margin:10px auto 0;padding:8px 7px;border-radius:10px;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.22);max-height:none;overflow:visible;}"
          + "#smna-generated-right-side .smna-rel-title{display:block;margin:0 0 6px;color:#d7e9fb;font-size:12px;font-weight:900;line-height:1.2;}"
          + "#smna-generated-right-side .smna-rel-grid{display:grid;grid-template-columns:minmax(0,1fr);gap:5px;}"
          + "#smna-generated-right-side .smna-rel-link{display:flex;align-items:center;justify-content:center;min-height:33px;padding:6px 6px;border-radius:8px;border:1px solid rgba(255,255,255,.18);background:rgba(5,31,55,.54);color:#f6fbff;text-decoration:none;font-size:11px;line-height:1.15;font-weight:800;text-align:center;letter-spacing:-.01em;word-break:keep-all;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
          + "#smna-generated-right-side .smna-rel-link:hover,#smna-generated-right-side .smna-rel-link:focus-visible{background:rgba(31,93,144,.72);outline:0;}"
          + "@media(max-height:820px){#smna-generated-right-side{top:118px;}}"
          + "@media(max-width:980px){#smna-generated-right-side{display:none !important;}}";
        document.head.appendChild(style);
      }

      var host = document.getElementById("smna-generated-right-side");
      if (!host) {
        host = document.createElement("aside");
        host.id = "smna-generated-right-side";
        document.body.appendChild(host);
      }

      var rep = digitsOnly(REPRESENTATIVE_PHONE) || "16683548";
      var mobile = digitsOnly(CONTACT_PHONE) || "01099268661";
      var chatHref = normalizeOutboundUrl(KAKAO_OPENCHAT_URL || "") || ("tel:" + mobile);

      host.innerHTML = ""
        + '<div class="smna-qwrap">'
        + '  <strong class="smna-qttl">SEOULMNA QUICK</strong>'
        + '  <a class="smna-qbtn" href="https://seoulmna.co.kr/mna" target="_blank" rel="noopener noreferrer">양도양수 매물 즉시 확인</a>'
        + '  <a class="smna-qbtn" href="tel:' + rep + '">대표전화<span class="sub">1668-3548(유료)</span></a>'
        + '  <a class="smna-qbtn" href="tel:' + mobile + '">행정사 1:1 상담<span class="sub">' + CONTACT_PHONE + "</span></a>"
        + '  <a class="smna-qbtn kakao" href="' + _escapeHtml(chatHref) + '" target="_blank" rel="noopener noreferrer">카카오 오픈채팅</a>'
        + "</div>";

      mountRelatedOrganizationsCenter([]);
      _fitQuickMenuByLongestBlock();
      _applyMnaListQuickPolicy();

      blockLegacyQuickMenu();
      sanitizeUtilityLinks();
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

  function _recentMnaKey() {
    return "smna_recent_mna_v1";
  }

  function _favoriteMnaLegacyKey() {
    return "smna_favorite_mna_v1";
  }

  function _localAutoBridgeBase() {
    return "http://127.0.0.1:18777";
  }

  function _readCookieValue(name) {
    try {
      var target = String(name || "").trim();
      if (!target) return "";
      var parts = String(document.cookie || "").split(";");
      for (var i = 0; i < parts.length; i += 1) {
        var p = String(parts[i] || "").trim();
        if (!p || p.indexOf("=") < 0) continue;
        var k = p.slice(0, p.indexOf("=")).trim();
        if (k !== target) continue;
        return decodeURIComponent(p.slice(p.indexOf("=") + 1).trim());
      }
      return "";
    } catch (_e) {
      return "";
    }
  }

  function _sanitizeAccountToken(raw) {
    try {
      var src = compactText(raw || "");
      if (!src) return "";
      var clean = src.toLowerCase().replace(/[^a-z0-9_.@-]+/g, "");
      if (!clean) clean = encodeURIComponent(src).replace(/%/g, "_");
      return String(clean || "").slice(0, 80);
    } catch (_e) {
      return "";
    }
  }

  function _extractMbIdFromHref(rawHref) {
    try {
      var href = String(rawHref || "").trim();
      if (!href) return "";
      var abs = new URL(href, location.href);
      var qid = compactText(abs.searchParams.get("mb_id") || "");
      if (qid) return qid;
      var m = String(abs.pathname || "").match(/\\/member\\/([^/?#]+)/i);
      if (m && m[1]) return compactText(m[1]);
      return "";
    } catch (_e) {
      return "";
    }
  }

  function _resolveMemberToken() {
    try {
      if (!isLikelyLoggedIn()) return "";

      var lastLoginId = _sanitizeAccountToken(localStorage.getItem("smna_last_login_id") || "");
      if (lastLoginId) return lastLoginId;

      var globalCandidates = [
        (window.g5_mb_id || ""),
        (window.mb_id || ""),
        (window.member_id || ""),
        (window.g5_is_admin || ""),
      ];
      for (var g = 0; g < globalCandidates.length; g += 1) {
        var gv = _sanitizeAccountToken(globalCandidates[g]);
        if (gv) return gv;
      }

      var hrefNodes = document.querySelectorAll("a[href*='mb_id='], a[href*='profile.php'], a[href*='member_confirm.php']");
      for (var h = 0; h < hrefNodes.length; h += 1) {
        var hv = _sanitizeAccountToken(_extractMbIdFromHref(hrefNodes[h].getAttribute("href") || ""));
        if (hv) return hv;
      }

      var inputNode = document.querySelector("input[name='mb_id'][value], input[name='userid'][value]");
      if (inputNode) {
        var iv = _sanitizeAccountToken(inputNode.value || "");
        if (iv) return iv;
      }

      var cookieCandidates = ["mb_id", "ck_mb_id", "g5_mb_id", "member_id"];
      for (var c = 0; c < cookieCandidates.length; c += 1) {
        var cv = _sanitizeAccountToken(_readCookieValue(cookieCandidates[c]));
        if (cv) return cv;
      }

      return "member";
    } catch (_e) {
      return "";
    }
  }

  function bindLoginIdCapture() {
    try {
      if (!isLoginPage()) return;
      var form = document.querySelector("form[action*='login_check.php'], form[name=flogin], #login_fs");
      if (!form) return;
      var idInput = form.querySelector("input[name='mb_id'], input[name='userid'], input[type='text'][name*='id']");
      if (!idInput) return;

      var remember = function() {
        var token = _sanitizeAccountToken(idInput.value || "");
        if (token) {
          localStorage.setItem("smna_last_login_id", token);
          _localAutoPostState("login_capture", null, null);
        }
      };

      remember();
      if (!form.getAttribute("data-smna-login-id-bound")) {
        form.setAttribute("data-smna-login-id-bound", "1");
        form.addEventListener("submit", remember, true);
        idInput.addEventListener("change", remember, true);
        idInput.addEventListener("blur", remember, true);
      }
    } catch (_e) {}
  }

  function _localAutoAccountToken() {
    try {
      var token = _sanitizeAccountToken(_resolveMemberToken() || "");
      if (token) return token;
      var lastToken = _sanitizeAccountToken(localStorage.getItem("smna_last_login_id") || "");
      return lastToken || "guest";
    } catch (_e) {
      return "guest";
    }
  }

  function _localAutoPostState(reason, favoriteRows, recentRows) {
    try {
      var payload = {
        account: _localAutoAccountToken(),
        reason: compactText(reason || ""),
        ts: Date.now(),
        page: String(location.pathname || "")
      };
      if (ENABLE_MNA_FAVORITES && Array.isArray(favoriteRows)) payload.favorites = favoriteRows.slice(0, 20);
      if (Array.isArray(recentRows)) payload.recent = recentRows.slice(0, 10);
      var body = JSON.stringify(payload);
      fetch(_localAutoBridgeBase() + "/v1/state", {
        method: "POST",
        mode: "cors",
        cache: "no-store",
        keepalive: true,
        headers: { "Content-Type": "application/json" },
        body: body
      }).catch(function() {});
    } catch (_e) {}
  }

  function _localAutoPullStateOnce() {
    try {
      var account = _localAutoAccountToken();
      var doneKey = "smna_local_auto_pull_done::" + account;
      if (sessionStorage.getItem(doneKey) === "1") return;
      sessionStorage.setItem(doneKey, "1");
      var url = _localAutoBridgeBase() + "/v1/state?account=" + encodeURIComponent(account);
      fetch(url, { mode: "cors", cache: "no-store" })
        .then(function(res) { return res && res.ok ? res.json() : null; })
        .then(function(data) {
          if (!data || typeof data !== "object") return;
          try {
            if (ENABLE_MNA_FAVORITES && Array.isArray(data.favorites)) {
              var fKey = _favoriteMnaKey();
              if (fKey) localStorage.setItem(fKey, JSON.stringify(data.favorites.slice(0, 20)));
            }
            if (Array.isArray(data.recent)) {
              localStorage.setItem(_recentMnaKey(), JSON.stringify(data.recent.slice(0, 10)));
            }
            if (typeof mountMnaPocketPanel === "function") {
              setTimeout(function() { try { mountMnaPocketPanel(); } catch (_e2) {} }, 40);
            }
          } catch (_e3) {}
        })
        .catch(function() {});
    } catch (_e) {}
  }

  function _favoriteMnaKey() {
    if (!ENABLE_MNA_FAVORITES) return "";
    var token = _resolveMemberToken();
    if (!token) return "";
    return "smna_favorite_mna_v2::" + token;
  }

  function _isFavoriteLoginRequired() {
    if (!ENABLE_MNA_FAVORITES) return true;
    return !isLikelyLoggedIn();
  }

  function _migrateLegacyFavoriteIfNeeded(key) {
    try {
      if (!key) return;
      var doneKey = "smna_favorite_mna_migrated::" + key;
      if (localStorage.getItem(doneKey) === "1") return;
      var legacyRaw = localStorage.getItem(_favoriteMnaLegacyKey());
      if (!legacyRaw) {
        localStorage.setItem(doneKey, "1");
        return;
      }
      var currentRaw = localStorage.getItem(key);
      if (!currentRaw) {
        localStorage.setItem(key, legacyRaw);
      }
      localStorage.setItem(doneKey, "1");
    } catch (_e) {}
  }

  function _escapeHtml(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function _normalizeMnaDetailUrl(rawUrl) {
    try {
      var src = normalizeOutboundUrl(rawUrl || "");
      if (!src) return "";
      var abs = new URL(src, location.href);
      var m = String(abs.pathname || "").match(/^\\/mna\\/(\\d+)/i);
      if (!m) return "";
      return location.origin + "/mna/" + m[1];
    } catch (_e) {
      return "";
    }
  }

  function _readRecentMna() {
    try {
      var raw = localStorage.getItem(_recentMnaKey());
      if (!raw) return [];
      var arr = JSON.parse(raw);
      if (!Array.isArray(arr)) return [];
      var out = [];
      for (var i = 0; i < arr.length; i += 1) {
        var row = arr[i] || {};
        var url = _normalizeMnaDetailUrl(row.url || "");
        if (!url) continue;
        var title = compactText(row.title || "");
        var ts = Number(row.ts || 0);
        out.push({
          url: url,
          title: (title || ("매물 " + String(url).split("/").pop())).slice(0, 56),
          ts: Number.isFinite(ts) ? ts : 0
        });
      }
      return out.slice(0, 10);
    } catch (_e) {
      return [];
    }
  }

  function _writeRecentMna(items) {
    try {
      var arr = Array.isArray(items) ? items.slice(0, 10) : [];
      localStorage.setItem(_recentMnaKey(), JSON.stringify(arr));
      _localAutoPostState("recent_write", null, arr);
    } catch (_e) {}
  }

  function _readFavoriteMna() {
    try {
      if (!ENABLE_MNA_FAVORITES) return [];
      var key = _favoriteMnaKey();
      if (!key) return [];
      _migrateLegacyFavoriteIfNeeded(key);
      var raw = localStorage.getItem(key);
      if (!raw) return [];
      var arr = JSON.parse(raw);
      if (!Array.isArray(arr)) return [];
      var out = [];
      for (var i = 0; i < arr.length; i += 1) {
        var row = arr[i] || {};
        var url = _normalizeMnaDetailUrl(row.url || "");
        if (!url) continue;
        var title = compactText(row.title || "");
        var ts = Number(row.ts || 0);
        out.push({
          url: url,
          title: (title || ("매물 " + String(url).split("/").pop())).slice(0, 56),
          ts: Number.isFinite(ts) ? ts : 0
        });
      }
      return out.slice(0, 20);
    } catch (_e) {
      return [];
    }
  }

  function _writeFavoriteMna(items) {
    try {
      if (!ENABLE_MNA_FAVORITES) return;
      var key = _favoriteMnaKey();
      if (!key) return;
      var arr = Array.isArray(items) ? items.slice(0, 20) : [];
      localStorage.setItem(key, JSON.stringify(arr));
      _localAutoPostState("favorite_write", arr, null);
    } catch (_e) {}
  }

  function _isFavoriteMna(url) {
    var normalized = _normalizeMnaDetailUrl(url || "");
    if (!normalized) return false;
    var rows = _readFavoriteMna();
    for (var i = 0; i < rows.length; i += 1) {
      if (rows[i].url === normalized) return true;
    }
    return false;
  }

  function _toggleFavoriteMna(url, title) {
    if (_isFavoriteLoginRequired()) return false;
    var normalized = _normalizeMnaDetailUrl(url || "");
    if (!normalized) return false;
    var rows = _readFavoriteMna();
    var out = [];
    var existed = false;
    for (var i = 0; i < rows.length; i += 1) {
      if (rows[i].url === normalized) existed = true;
      else out.push(rows[i]);
    }
    if (!existed) {
      var label = compactText(title || "");
      if (!label) label = "매물 " + String(normalized).split("/").pop();
      out.unshift({ url: normalized, title: label.slice(0, 56), ts: Date.now() });
    }
    _writeFavoriteMna(out);
    return !existed;
  }

  function _clearFavoriteMna() {
    try {
      if (_isFavoriteLoginRequired()) return false;
      _writeFavoriteMna([]);
      return true;
    } catch (_e) {
      return false;
    }
  }

  function _pushRecentMna(url, title) {
    var normalized = _normalizeMnaDetailUrl(url || "");
    if (!normalized) return;
    var label = compactText(title || "");
    if (!label) label = "매물 " + String(normalized).split("/").pop();
    var existing = _readRecentMna();
    var filtered = [];
    for (var i = 0; i < existing.length; i += 1) {
      if (existing[i].url !== normalized) filtered.push(existing[i]);
    }
    filtered.unshift({ url: normalized, title: label.slice(0, 56), ts: Date.now() });
    _writeRecentMna(filtered);
  }

  function _captureRecentMnaFromPage() {
    try {
      var path = String(location.pathname || "");
      var m = path.match(/^\\/mna\\/(\\d+)/i);
      if (m) {
        var titleNode = document.querySelector("#bo_v_title, .bo_v_title, .bo_v_tit, .content_wrap h1, h1");
        var title = compactText(titleNode ? (titleNode.textContent || "") : "");
        _pushRecentMna(location.origin + "/mna/" + m[1], title || ("매물 " + m[1]));
      }
      if (!window.__smna_recent_mna_click_bound__) {
        window.__smna_recent_mna_click_bound__ = true;
        document.addEventListener("click", function(ev) {
          try {
            var target = ev.target;
            var anchor = target && target.closest ? target.closest("a[href]") : null;
            if (!anchor) return;
            var href = _normalizeMnaDetailUrl(anchor.getAttribute("href") || "");
            if (!href) return;
            var label = compactText(anchor.textContent || "");
            _pushRecentMna(href, label);
          } catch (_e2) {}
        }, true);
      }
    } catch (_e) {}
  }

  function _isMnaBoardContext() {
    try {
      var path = String(location.pathname || "").toLowerCase();
      var q = new URLSearchParams(location.search || "");
      var bo = String(q.get("bo_table") || "").toLowerCase();
      if (path.indexOf("/mna") === 0) return true;
      if (path.indexOf("/bbs/board.php") === 0 && bo === "mna") return true;
      if (path.indexOf("/bbs/write.php") === 0 && bo === "mna") return true;
      return false;
    } catch (_e) {
      return false;
    }
  }

  function _findGeneralCategoryAnchor() {
    try {
      var mshsTable = document.querySelector("table.mshs, .mshs");
      if (mshsTable && compactText(mshsTable.textContent || "").indexOf("일반건설업") >= 0) return mshsTable;

      var fixedAnchor = document.querySelector("#bo_cate, #bo_cate_ul, .bo_cate, .cate, .mna_cate");
      if (fixedAnchor && compactText(fixedAnchor.textContent || "").indexOf("일반건설업") >= 0) return fixedAnchor;

      var nodes = document.querySelectorAll(
        "#bo_list a,#bo_list li,#bo_list button,#bo_list span,#bo_list td,#bo_list th,form#fboardlist a,form#fboardlist li,form#fboardlist span,form#fboardlist td,form#fboardlist th"
      );
      for (var i = 0; i < nodes.length; i += 1) {
        var n = nodes[i];
        if (!n) continue;
        var t = compactText(n.textContent || "");
        if (t.indexOf("일반건설업") < 0) continue;
        var anchor = n.closest ? n.closest("#bo_cate,#bo_cate_ul,.bo_cate,.cate,.mna_cate,.board_top,.bo_fx,.tbl_head01,table,tr,ul,div") : null;
        return anchor || n;
      }
      return null;
    } catch (_e) {
      return null;
    }
  }

  function _renderMnaPocketPanel(panel) {
    if (!panel) return;
    var loggedIn = !_isFavoriteLoginRequired();
    var fav = loggedIn ? _readFavoriteMna().slice(0, 12) : [];
    var favCount = loggedIn ? fav.length : 0;
    var path = String(location.pathname || "");
    var detailMatch = path.match(/^\\/mna\\/(\\d+)/i);
    var currentUrl = detailMatch ? (location.origin + "/mna/" + detailMatch[1]) : "";
    var currentTitleNode = document.querySelector("#bo_v_title, .bo_v_title, .bo_v_tit, .content_wrap h1, h1");
    var currentTitle = compactText(currentTitleNode ? (currentTitleNode.textContent || "") : "");
    var currentFav = (loggedIn && currentUrl) ? _isFavoriteMna(currentUrl) : false;
    var loginHref = buildLoginGateUrl(currentUrl || (location.origin + "/mna"));

    function rowList(rows, emptyText) {
      if (!rows.length) return '<li class="empty">' + _escapeHtml(emptyText) + "</li>";
      var html = "";
      for (var i = 0; i < rows.length; i += 1) {
        var row = rows[i];
        var isFav = _isFavoriteMna(row.url);
        html += ""
          + '<li class="item">'
          + '  <a class="link" href="' + _escapeHtml(row.url) + '">' + _escapeHtml(row.title) + "</a>"
          + '  <button type="button" class="fav" data-smna-fav-url="' + _escapeHtml(row.url) + '" data-smna-fav-title="' + _escapeHtml(row.title) + '" aria-label="찜하기 토글" onclick="return window.__smnaFavToggle ? window.__smnaFavToggle(this) : false;">' + (isFav ? "해제" : "찜") + "</button>"
          + "</li>";
      }
      return html;
    }

    panel.innerHTML = ""
      + '<div class="smna-pocket-head">'
      + '  <strong>' + (loggedIn ? "찜한 매물" : "찜한 매물(로그인 전용)") + "</strong>"
      + (
        loggedIn
          ? (currentUrl ? ('<button type="button" class="smna-current-fav" data-smna-fav-url="' + _escapeHtml(currentUrl) + '" data-smna-fav-title="' + _escapeHtml(currentTitle || ("매물 " + detailMatch[1])) + '" onclick="return window.__smnaFavToggle ? window.__smnaFavToggle(this) : false;">' + (currentFav ? "현재 매물 찜해제" : "현재 매물 찜하기") + "</button>") : "")
          : ('<a class="smna-login-cta" href="' + _escapeHtml(loginHref) + '">로그인 후 찜하기 사용</a>')
      )
      + "</div>"
      + '<section class="col"><h4>찜한 매물 리스트' + (loggedIn ? (" (" + favCount + "건)") : "") + '</h4><ul>' + rowList(fav, loggedIn ? "찜한 매물이 없습니다." : "로그인 후 찜한 매물을 계정별로 자동 저장합니다.") + "</ul></section>"
      + '<div class="smna-pocket-actions">'
      + '  <a class="chip" href="https://seoulmna.co.kr/mna">최신 목록 새로고침</a>'
      + '  <a class="chip" href="https://seoulmna.co.kr/notice">상담센터 바로가기</a>'
      + '  <a class="chip tel" href="tel:16683548">대표전화 1668-3548</a>'
      + (loggedIn ? '<button type="button" class="chip danger" data-smna-fav-clear="1" onclick="return window.__smnaFavClear ? window.__smnaFavClear(this) : false;">찜한 매물 비우기</button>' : "")
      + "</div>";
  }

  function _favoriteCountSafe() {
    try {
      if (_isFavoriteLoginRequired()) return 0;
      return _readFavoriteMna().length;
    } catch (_e) {
      return 0;
    }
  }

  function _scrollToFavoritePocketPanel() {
    try {
      var panel = document.getElementById("smna-mna-pocket");
      if (!panel) return false;
      try {
        panel.scrollIntoView({ behavior: "smooth", block: "start" });
      } catch (_e1) {
        panel.scrollIntoView(true);
      }
      panel.classList.remove("smna-pocket-focus");
      void panel.offsetWidth;
      panel.classList.add("smna-pocket-focus");
      setTimeout(function() {
        try { panel.classList.remove("smna-pocket-focus"); } catch (_e2) {}
      }, 1500);
      return false;
    } catch (_e) {
      return false;
    }
  }

  function removeFavoriteArtifacts() {
    try {
      var panel = document.getElementById("smna-mna-pocket");
      if (panel && panel.parentNode) panel.parentNode.removeChild(panel);
      var fab = document.getElementById("smna-fav-locator");
      if (fab && fab.parentNode) fab.parentNode.removeChild(fab);
      try {
        delete window.__smnaFavToggle;
        delete window.__smnaFavClear;
        delete window.__smnaFavGoPanel;
      } catch (_e1) {
        window.__smnaFavToggle = null;
        window.__smnaFavClear = null;
        window.__smnaFavGoPanel = null;
      }
    } catch (_e) {}
  }

  function mountFavoriteLocatorFab(panel) {
    try {
      if (!ENABLE_MNA_FAVORITES) {
        removeFavoriteArtifacts();
        return;
      }
      if (!_isMnaBoardContext()) return;
      var style = document.getElementById("smna-mna-fav-locator-style");
      if (!style) {
        style = document.createElement("style");
        style.id = "smna-mna-fav-locator-style";
        style.textContent = ""
          + "#smna-fav-locator{position:fixed;left:14px;bottom:14px;z-index:9996;display:inline-flex;align-items:center;gap:8px;min-height:44px;padding:9px 13px;border-radius:999px;border:1px solid #0e568f;background:linear-gradient(145deg,#0f5f9e 0%,#1f7dc2 100%);box-shadow:0 10px 24px rgba(5,54,95,.28);color:#fff;font-size:13px;line-height:1.2;font-weight:900;cursor:pointer;letter-spacing:-.01em;}"
          + "#smna-fav-locator .cnt{display:inline-flex;align-items:center;justify-content:center;min-width:26px;height:26px;padding:0 7px;border-radius:999px;background:#ffdc71;color:#3d2b00;font-size:12px;font-weight:900;line-height:1;}"
          + "#smna-fav-locator .txt{white-space:nowrap;}"
          + "#smna-fav-locator:hover{border-color:#0b4b7b;background:linear-gradient(145deg,#0d578f 0%,#17689f 100%);}"
          + "#smna-fav-locator:focus-visible{outline:2px solid #ffcb5a;outline-offset:2px;}"
          + "#smna-mna-pocket.smna-pocket-focus{animation:smnaPocketPulse 1.35s ease;}"
          + "@keyframes smnaPocketPulse{0%{box-shadow:0 0 0 0 rgba(40,138,214,.44);}100%{box-shadow:0 0 0 18px rgba(40,138,214,0);}}"
          + "@media(max-width:980px){#smna-fav-locator{left:10px;right:10px;bottom:10px;justify-content:center;font-size:12px;min-height:42px;padding:8px 12px;}}";
        document.head.appendChild(style);
      }

      var fab = document.getElementById("smna-fav-locator");
      if (!fab) {
        fab = document.createElement("button");
        fab.type = "button";
        fab.id = "smna-fav-locator";
        fab.setAttribute("aria-label", "찜한 매물 위치 안내");
        fab.onclick = function() { return _scrollToFavoritePocketPanel(); };
      }

      var count = _favoriteCountSafe();
      var loggedIn = !_isFavoriteLoginRequired();
      fab.innerHTML = '<span class="cnt">' + String(count) + '</span><span class="txt">' + (loggedIn ? "찜한 매물 확인" : "로그인 후 찜한 매물 확인") + "</span>";
      fab.title = loggedIn ? "상단 찜한 매물 박스로 이동" : "로그인 후 상단 찜한 매물 박스를 이용할 수 있습니다.";
      fab.style.display = "";

      if (!document.body.contains(fab)) document.body.appendChild(fab);

      // 관리자 트래픽 배지와 겹치지 않도록 하단 여백 자동 조정
      var adminTraffic = document.getElementById("smna-traffic-admin");
      if (adminTraffic && adminTraffic.offsetHeight > 0) {
        fab.style.bottom = (14 + adminTraffic.offsetHeight + 10) + "px";
      } else {
        fab.style.bottom = "";
      }
    } catch (_e) {}
  }

  function mountMnaPocketPanel() {
    try {
      if (!ENABLE_MNA_FAVORITES) {
        removeFavoriteArtifacts();
        return;
      }
      if (!_isMnaBoardContext()) return;
      var style = document.getElementById("smna-mna-pocket-style");
      if (!style) {
        style = document.createElement("style");
        style.id = "smna-mna-pocket-style";
        style.textContent = ""
          + "#smna-mna-pocket{max-width:1120px;margin:10px auto 12px;padding:12px 14px;border:1px solid #b7cee4;border-radius:14px;background:linear-gradient(180deg,#f8fbff 0%,#edf5ff 100%);box-shadow:0 8px 18px rgba(4,54,96,.12);}"
          + "#smna-mna-pocket .smna-pocket-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:10px;}"
          + "#smna-mna-pocket .smna-pocket-head strong{font-size:18px;line-height:1.2;color:#003764;font-weight:900;}"
          + "#smna-mna-pocket .smna-current-fav{border:1px solid #d2a13a;background:linear-gradient(140deg,#fff5cb 0%,#ffe080 100%);color:#3b2a00;font-size:13px;font-weight:900;line-height:1.2;border-radius:999px;min-height:34px;padding:7px 12px;cursor:pointer;}"
          + "#smna-mna-pocket .smna-login-cta{display:inline-flex;align-items:center;justify-content:center;border:1px solid #0e4f83;background:linear-gradient(140deg,#0f5e9c 0%,#1e75b8 100%);color:#fff;text-decoration:none;font-size:13px;font-weight:900;line-height:1.2;border-radius:999px;min-height:34px;padding:7px 12px;}"
          + "#smna-mna-pocket .col{border:1px solid #d4e4f2;border-radius:12px;background:#fff;padding:10px 10px 8px;}"
          + "#smna-mna-pocket .col h4{margin:0 0 8px;font-size:14px;line-height:1.2;color:#0f426b;font-weight:900;}"
          + "#smna-mna-pocket .col ul{margin:0;padding:0;list-style:none;display:grid;gap:7px;}"
          + "#smna-mna-pocket .item{display:grid;grid-template-columns:1fr auto;align-items:center;gap:7px;}"
          + "#smna-mna-pocket .link{display:block;padding:6px 8px;border:1px solid #e2ebf4;border-radius:9px;background:#fdfefe;color:#103c61;font-size:13px;line-height:1.3;font-weight:700;text-decoration:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
          + "#smna-mna-pocket .link:hover{border-color:#9fbddb;background:#f1f8ff;}"
          + "#smna-mna-pocket .fav{min-width:46px;height:34px;padding:0 9px;border:1px solid #d4dee9;border-radius:10px;background:#fff;color:#355a7c;font-size:13px;font-weight:800;line-height:1;cursor:pointer;}"
          + "#smna-mna-pocket .fav:hover{border-color:#d4a53f;background:#fff4d2;color:#4d3200;}"
          + "#smna-mna-pocket .empty{padding:8px;border:1px dashed #d6e2ee;border-radius:8px;color:#5a748e;font-size:12px;line-height:1.35;}"
          + "#smna-mna-pocket .smna-pocket-actions{display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin-top:9px;}"
          + "#smna-mna-pocket .smna-pocket-actions .chip{display:inline-flex;align-items:center;justify-content:center;min-height:30px;padding:4px 10px;border-radius:999px;border:1px solid #c7d9ea;background:#fff;color:#15476f;text-decoration:none;font-size:12px;font-weight:800;line-height:1.2;}"
          + "#smna-mna-pocket .smna-pocket-actions .chip:hover{border-color:#8db0ce;background:#f2f8ff;}"
          + "#smna-mna-pocket .smna-pocket-actions .chip.tel{border-color:#afcbe2;background:#f7fbff;color:#0e4169;}"
          + "#smna-mna-pocket .smna-pocket-actions .chip.danger{border-color:#d1dce8;background:#fff;color:#3f5a73;cursor:pointer;}"
          + "#smna-mna-pocket .smna-pocket-actions .chip.danger:hover{border-color:#b8c5d3;background:#f5f8fb;}"
          + "#smna-mna-pocket button:focus-visible,#smna-mna-pocket a:focus-visible{outline:2px solid #ffcb5a;outline-offset:2px;}"
          + "@media(max-width:980px){#smna-mna-pocket{margin:8px auto 10px;padding:10px;}#smna-mna-pocket .smna-pocket-head{flex-wrap:wrap;}}";
        document.head.appendChild(style);
      }

      var panel = document.getElementById("smna-mna-pocket");
      if (!panel) {
        panel = document.createElement("section");
        panel.id = "smna-mna-pocket";
      }

      var boardForm = document.querySelector("form#fboardlist");
      var target = boardForm || document.querySelector("#bo_list, #bo_v, #bo_v_con, #ctt_con, #ctt, #container");
      if (!target) return;

      var preferredHost = null;
      var preferredAfter = null;
      var generalCategoryAnchor = _findGeneralCategoryAnchor();
      if (generalCategoryAnchor && generalCategoryAnchor.parentNode) {
        preferredHost = generalCategoryAnchor.parentNode;
        preferredAfter = null;
      } else if (boardForm) {
        var globalBoardHeaderAnchor = document.querySelector(".mshs, .bo_sch, .bo_search");
        if (globalBoardHeaderAnchor && globalBoardHeaderAnchor.parentNode) {
          preferredHost = globalBoardHeaderAnchor.parentNode;
          preferredAfter = globalBoardHeaderAnchor;
        } else {
          var boardHeaderAnchor = boardForm.querySelector(".mshs, .bo_sch, .bo_search, .board_top");
          if (boardHeaderAnchor && boardHeaderAnchor.parentNode) {
            preferredHost = boardHeaderAnchor.parentNode;
            preferredAfter = boardHeaderAnchor;
          } else {
            preferredHost = boardForm;
            preferredAfter = boardForm.querySelector("#bo_list");
          }
        }
      } else {
        var globalHeaderAnchorNoForm = document.querySelector(".mshs, .bo_sch, .bo_search");
        if (globalHeaderAnchorNoForm && globalHeaderAnchorNoForm.parentNode) {
          preferredHost = globalHeaderAnchorNoForm.parentNode;
          preferredAfter = globalHeaderAnchorNoForm;
        } else {
          preferredHost = target;
          preferredAfter = target.querySelector(".bo_fx, form[name=fsearch], .board_top, .tbl_head01");
        }
      }

      if (!preferredHost) preferredHost = target;
      if (!panel.parentNode || panel.parentNode !== preferredHost) {
        if (panel.parentNode) panel.parentNode.removeChild(panel);
      }

      if (generalCategoryAnchor && generalCategoryAnchor.parentNode === preferredHost) {
        preferredHost.insertBefore(panel, generalCategoryAnchor);
      } else if (preferredAfter && preferredAfter.parentNode === preferredHost) {
        if (preferredAfter.nextSibling) preferredHost.insertBefore(panel, preferredAfter.nextSibling);
        else preferredHost.appendChild(panel);
      } else if (preferredAfter && preferredAfter.id === "bo_list" && preferredHost === boardForm) {
        preferredHost.insertBefore(panel, preferredAfter);
      } else {
        preferredHost.insertBefore(panel, preferredHost.firstChild || null);
      }

      window.__smnaFavToggle = function(btn) {
        try {
          var activePanel = document.getElementById("smna-mna-pocket");
          if (!activePanel || !btn) return false;
          var favUrl = String(btn.getAttribute("data-smna-fav-url") || "");
          var favTitle = String(btn.getAttribute("data-smna-fav-title") || "");
          if (_isFavoriteLoginRequired()) {
            location.href = buildLoginGateUrl(favUrl || (location.origin + "/mna"));
            return false;
          }
          _toggleFavoriteMna(favUrl, favTitle);
          _renderMnaPocketPanel(activePanel);
          refreshMnaInfoExperience(activePanel);
          mountFavoriteLocatorFab(activePanel);
          return false;
        } catch (_e) {
          return false;
        }
      };
      window.__smnaFavClear = function() {
        try {
          var activePanel = document.getElementById("smna-mna-pocket");
          _clearFavoriteMna();
          if (activePanel) {
            _renderMnaPocketPanel(activePanel);
            refreshMnaInfoExperience(activePanel);
            mountFavoriteLocatorFab(activePanel);
          }
          return false;
        } catch (_e) {
          return false;
        }
      };

      _renderMnaPocketPanel(panel);
      refreshMnaInfoExperience(panel);
      mountFavoriteLocatorFab(panel);
      if (panel.getAttribute("data-smna-bound") !== "1") {
        panel.setAttribute("data-smna-bound", "1");
        panel.addEventListener("click", function(ev) {
          var clearBtn = ev.target && ev.target.closest ? ev.target.closest("button[data-smna-fav-clear]") : null;
          if (clearBtn) {
            _clearFavoriteMna();
            _renderMnaPocketPanel(panel);
            mountFavoriteLocatorFab(panel);
            return;
          }
          var btn = ev.target && ev.target.closest ? ev.target.closest("button[data-smna-fav-url]") : null;
          if (!btn) return;
          var url = btn.getAttribute("data-smna-fav-url") || "";
          var title = btn.getAttribute("data-smna-fav-title") || "";
          if (_isFavoriteLoginRequired()) {
            location.href = buildLoginGateUrl(url || (location.origin + "/mna"));
            return;
          }
          _toggleFavoriteMna(url, title);
          _renderMnaPocketPanel(panel);
          refreshMnaInfoExperience(panel);
          mountFavoriteLocatorFab(panel);
        });
      }
    } catch (_e) {}
  }

  function tuneMnaSearchSelectUx() {
    try {
      if (!_isMnaBoardContext()) return;
      var style = document.getElementById("smna-mna-search-ux-style");
      if (!style) {
        style = document.createElement("style");
        style.id = "smna-mna-search-ux-style";
        style.textContent = ""
          + "#fm_search2 form#fmSearch{overflow-x:hidden;}"
          + "#fm_search2 form#fmSearch table{width:100%;table-layout:fixed;}"
          + "#fm_search2 form#fmSearch td{box-sizing:border-box;vertical-align:middle;}"
          + "#fm_search2 form#fmSearch div[style*='display: inline-block'][style*='width:100%']{display:flex !important;align-items:center;flex-wrap:wrap;gap:8px 10px;line-height:1.35 !important;}"
          + "#fm_search2 form#fmSearch select[name='price_amount']{font-size:16px !important;line-height:1.35 !important;font-weight:700;min-height:34px;height:34px;padding:4px 28px 4px 10px;border-radius:8px;border:1px solid #b9cde0;background:#fff;color:#1a3650;min-width:154px;max-width:100%;box-sizing:border-box;white-space:nowrap;}"
          + "#fm_search2 form#fmSearch input[type='text'],#fm_search2 form#fmSearch input[type='search']{min-height:34px;height:34px;box-sizing:border-box;}"
          + "@media(max-width:980px){#fm_search2 form#fmSearch div[style*='display: inline-block'][style*='width:100%']{gap:6px 8px;}#fm_search2 form#fmSearch select[name='price_amount']{font-size:15px !important;min-width:138px;height:32px;min-height:32px;padding:4px 24px 4px 9px;}}";
        document.head.appendChild(style);
      }
    } catch (_e) {}
  }

  function refreshMnaInfoExperience(panel) {
    try {
      if (!_isMnaBoardContext()) return;

      var legacyKeywords = [
        "본 게시판 정보는 참고용",
        "정밀한 법리, 세무, 재무 검토",
        "검색창에 면허명, 지역명을 입력하면",
        "최신 매물 목록 보기",
        "서울건설정보 홈으로 이동",
        "건설업 양도양수 | 실시간 매물",
        "업종, 지역, 가격 기준으로 매물 비교",
        "핵심 조건을 먼저 확인하고 상담 연계",
        "최신 등록순 기준으로 빠른 탐색 지원"
      ];
      var legacyNodes = document.querySelectorAll("#bo_list section,#bo_list article,#bo_list div,form#fboardlist > div,#container section,#container article,#container div");
      for (var i = 0; i < legacyNodes.length; i += 1) {
        var n = legacyNodes[i];
        if (!n || !n.parentNode) continue;
        if (n.id === "smna-mna-pocket" || n.id === "smna-mna-smart-strip") continue;
        var text = compactText(n.textContent || "");
        if (!text || text.length < 70 || text.length > 1800) continue;
        var hit = 0;
        for (var k = 0; k < legacyKeywords.length; k += 1) {
          if (text.indexOf(legacyKeywords[k]) >= 0) hit += 1;
        }
        if (hit >= 2 || text.indexOf("건설업 양도양수 | 실시간 매물") >= 0 || text.indexOf("본 게시판 정보는 참고용") >= 0) {
          n.style.display = "none";
          n.setAttribute("data-smna-legacy-guide-hidden", "1");
        }
      }

      var style = document.getElementById("smna-mna-smart-strip-style");
      if (!style) {
        style = document.createElement("style");
        style.id = "smna-mna-smart-strip-style";
        style.textContent = ""
          + "#smna-mna-smart-strip{max-width:1120px;margin:0 auto 10px;padding:10px 12px;border:1px solid #cde0f2;border-radius:12px;background:linear-gradient(180deg,#ffffff 0%,#f6faff 100%);box-shadow:0 6px 14px rgba(0,42,78,.08);}"
          + "#smna-mna-smart-strip .title{margin:0 0 8px;color:#0e4169;font-size:15px;line-height:1.25;font-weight:900;}"
          + "#smna-mna-smart-strip .meta{margin:0 0 9px;color:#315a7a;font-size:12px;line-height:1.45;font-weight:700;}"
          + "#smna-mna-smart-strip .actions{display:flex;flex-wrap:wrap;gap:8px;}"
          + "#smna-mna-smart-strip .actions a{display:inline-flex;align-items:center;justify-content:center;min-height:32px;padding:5px 11px;border-radius:999px;border:1px solid #bfd4e9;background:#fff;color:#12446c;text-decoration:none;font-size:12px;line-height:1.2;font-weight:900;}"
          + "#smna-mna-smart-strip .actions a.main{border-color:#0f5c98;background:linear-gradient(145deg,#0f5f9e 0%,#1e78bd 100%);color:#fff;}"
          + "#smna-mna-smart-strip .actions a:hover{border-color:#86abc9;background:#eff7ff;}"
          + "#smna-mna-smart-strip .actions a.main:hover{border-color:#0c5288;background:linear-gradient(145deg,#0c548b 0%,#15649f 100%);}"
          + "@media(max-width:980px){#smna-mna-smart-strip{padding:9px 10px;}#smna-mna-smart-strip .title{font-size:14px;}#smna-mna-smart-strip .actions{gap:6px;}#smna-mna-smart-strip .actions a{min-height:30px;padding:5px 10px;font-size:11px;}}";
        document.head.appendChild(style);
      }

      var strip = document.getElementById("smna-mna-smart-strip");
      if (!strip) {
        strip = document.createElement("section");
        strip.id = "smna-mna-smart-strip";
      }
      strip.innerHTML = ""
        + '<h3 class="title">빠른 탐색 액션</h3>'
        + '<p class="meta">업종/지역 조건을 먼저 선택하면 원하는 매물을 더 빠르게 찾을 수 있습니다.</p>'
        + '<div class="actions">'
        + '  <a class="main" href="#fm_search2">검색영역 바로가기</a>'
        + '  <a href="https://seoulmna.co.kr/mna">최신 목록 새로고침</a>'
        + '  <a href="https://seoulmna.co.kr/notice">상담센터 연결</a>'
        + '  <a href="tel:16683548">대표전화 1668-3548</a>'
        + "</div>";

      var anchorPanel = panel || document.getElementById("smna-mna-pocket");
      if (anchorPanel && anchorPanel.parentNode) {
        if (strip.parentNode !== anchorPanel.parentNode) {
          if (strip.parentNode) strip.parentNode.removeChild(strip);
          if (anchorPanel.nextSibling) anchorPanel.parentNode.insertBefore(strip, anchorPanel.nextSibling);
          else anchorPanel.parentNode.appendChild(strip);
        } else if (anchorPanel.nextSibling !== strip) {
          anchorPanel.parentNode.insertBefore(strip, anchorPanel.nextSibling);
        }
      }
      if (ENABLE_MNA_FAVORITES) window.__smnaFavGoPanel = _scrollToFavoritePocketPanel;
      else window.__smnaFavGoPanel = null;
    } catch (_e) {}
  }

  function stabilizeHeaderAndNav() {
    try {
      try {
        document.documentElement.setAttribute("data-smna-header-mode", "text");
      } catch (_e1) {}

      var style = document.getElementById("smna-header-stabilize-style");
      if (!style) {
        style = document.createElement("style");
        style.id = "smna-header-stabilize-style";
        document.head.appendChild(style);
      }
      style.textContent = ""
        + "html,body{margin:0 !important;padding:0 !important;}"
        + "#wrap,#wrapper{margin-top:0 !important;padding-top:0 !important;}"
        + "#wrap>div:first-child{margin-top:0 !important;padding-top:0 !important;background:#0b1f34 !important;border-top:0 !important;}"
        + "#wrap,#wrapper,#header,.header-inner{border-top:0 !important;}"
        + "#header{position:relative;overflow:visible !important;top:0 !important;margin-top:0 !important;}"
        + "#header .header-inner{position:relative;z-index:2;overflow:visible !important;min-height:96px;display:flex;align-items:center;justify-content:space-between;gap:16px;padding:10px 20px 12px;margin-top:0 !important;}"
        + "#header #logo{display:flex !important;align-items:center !important;justify-content:flex-start !important;min-height:72px;line-height:1;overflow:visible !important;padding-right:10px;margin-left:0 !important;flex:0 0 auto;}"
        + "#header #logo a{display:inline-flex !important;align-items:center !important;justify-content:flex-start !important;line-height:1;overflow:visible !important;height:auto !important;}"
        + "#header #logo img{display:block !important;width:auto !important;height:auto !important;max-height:58px !important;object-fit:contain !important;position:static !important;top:auto !important;}"
        + "#header .gnb{display:flex;justify-content:flex-end;align-items:center;flex-wrap:wrap;position:static !important;right:auto !important;height:auto !important;gap:4px;list-style:none;}"
        + "#header .gnb > li{height:auto !important;line-height:1 !important;padding:0 3px !important;}"
        + "#header .gnb > li > a{display:inline-flex;align-items:center;justify-content:center;line-height:1.2 !important;color:#fff !important;letter-spacing:-.015em;transition:all .22s ease;position:relative;}"
        + "#header a:focus-visible{outline:2px solid #7de8ff;outline-offset:2px;}"
        + "html[data-smna-header-mode='text'] #header{background:#0b1f34 !important;border:0 !important;border-radius:0 !important;backdrop-filter:none !important;-webkit-backdrop-filter:none !important;box-shadow:none !important;}"
        + "html[data-smna-header-mode='text'] #header::before,html[data-smna-header-mode='text'] #header::after{content:none !important;display:none !important;}"
        + "html[data-smna-header-mode='text'] #header .header-inner{padding:8px 22px 4px;border:0 !important;background:#0b1f34 !important;box-shadow:none !important;}"
        + "html[data-smna-header-mode='text'] #header .gnb > li,html[data-smna-header-mode='text'] #header .gnb > li::before,html[data-smna-header-mode='text'] #header .gnb > li::after{background:none !important;border:0 !important;box-shadow:none !important;}"
        + "html[data-smna-header-mode='text'] #header .gnb > li > a{min-height:54px;padding:10px 11px;border:0 !important;border-radius:0 !important;background:transparent !important;color:#f3fbff !important;font-size:30px !important;font-weight:900 !important;text-shadow:0 2px 15px rgba(0,0,0,.42),0 0 16px rgba(54,177,255,.26);box-shadow:none !important;}"
        + "html[data-smna-header-mode='text'] #header .gnb > li > a::before{content:none !important;display:none !important;}"
        + "html[data-smna-header-mode='text'] #header .gnb > li > a::after{content:'';position:absolute;left:10px;right:10px;bottom:7px;height:2px;background:linear-gradient(90deg,rgba(126,220,255,0),rgba(126,220,255,.96),rgba(126,220,255,0));transform:scaleX(.16);transform-origin:50% 50%;opacity:.4;transition:transform .24s ease,opacity .24s ease;pointer-events:none;}"
        + "html[data-smna-header-mode='text'] #header .gnb > li > a:hover,html[data-smna-header-mode='text'] #header .gnb > li > a:focus-visible{background:transparent !important;color:#b9eeff !important;outline:none !important;box-shadow:none !important;transform:translateY(-1px) scale(1.03);text-shadow:0 0 20px rgba(133,228,255,.88),0 1px 12px rgba(0,0,0,.44);}"
        + "html[data-smna-header-mode='text'] #header .gnb > li > a:hover::after,html[data-smna-header-mode='text'] #header .gnb > li > a:focus-visible::after{transform:scaleX(1);opacity:1;}"
        + "html[data-smna-header-mode='text'] #header .gnb > li.smna-active > a{background:transparent !important;color:#c7f5ff !important;box-shadow:none !important;text-shadow:0 0 20px rgba(108,216,255,.88),0 1px 12px rgba(0,0,0,.42);}"
        + "html[data-smna-header-mode='text'] #header .gnb > li.smna-active > a::after{transform:scaleX(1);opacity:1;}"
        + "#header .gnb > li > a:active{transform:translateY(1px);}"
        + "@media(max-width:1200px){#header .header-inner{min-height:84px;padding:8px 14px 10px;}#header #logo img{max-height:50px !important;}html[data-smna-header-mode='text'] #header .gnb > li > a{font-size:24px !important;min-height:48px;padding:9px 8px;}}"
        + "@media(max-width:980px){#header .header-inner{min-height:74px;display:flex;padding:8px 12px;}#header #logo img{max-height:44px !important;}html[data-smna-header-mode='text'] #header .gnb > li > a{font-size:20px !important;min-height:42px;padding:8px 7px;}}";

      var headerInner = document.querySelector("#header .header-inner");
      if (headerInner) {
        var legacyTopAction = document.getElementById("smna-top-action-bar");
        if (legacyTopAction && legacyTopAction.parentNode) legacyTopAction.parentNode.removeChild(legacyTopAction);
        var oldTools = document.getElementById("smna-header-tools");
        if (oldTools && oldTools.parentNode) oldTools.parentNode.removeChild(oldTools);
      }

      var gnb = document.querySelector("#header .gnb");
      if (gnb) {
        gnb.setAttribute("role", "navigation");
        gnb.setAttribute("aria-label", "서울건설정보 주요 메뉴");
      }

      var topMenus = document.querySelectorAll("#header .gnb > li");
      var pagePath = String(location.pathname || "").toLowerCase();
      var supportMenuSeen = false;
      var hiddenNavKeywords = [
        "정책",
        "자금",
        "운전자금",
        "시설자금",
        "r&d",
        "계산기",
        "ai calc",
        "ai acq"
      ];
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
        var submenuLinks = li.querySelectorAll("ul a[href], .snb a[href], .sub a[href], .submenu a[href], .sub-menu a[href]");
        var submenuJoined = "";
        for (var sk = 0; sk < submenuLinks.length; sk += 1) {
          var submenuNode = submenuLinks[sk];
          submenuJoined += " " + compactText(submenuNode.textContent || "");
          submenuJoined += " " + compactText(submenuNode.getAttribute("href") || "");
        }
        submenuJoined = submenuJoined.toLowerCase();
        var hasHiddenKeyword = /pages\\/s\\d+\\.php\\b/.test(submenuJoined)
          || /co_id=ai_(calc|acq)\b/.test(submenuJoined);
        if (!hasHiddenKeyword) {
          for (var hk = 0; hk < hiddenNavKeywords.length; hk += 1) {
            if (submenuJoined.indexOf(hiddenNavKeywords[hk]) >= 0) {
              hasHiddenKeyword = true;
              break;
            }
          }
        }
        if ((!text && !href) || hasHiddenKeyword || (supportMenuSeen && !text)) {
          if (li.parentNode) li.parentNode.removeChild(li);
          continue;
        }
        if (text.indexOf("고객센터") >= 0 || text.indexOf("상담센터") >= 0) supportMenuSeen = true;
        if (href) topAnchor.setAttribute("href", href);
        var navPath = "";
        try {
          navPath = String(new URL(href || "", location.origin).pathname || "").toLowerCase();
        } catch (_e) {
          navPath = "";
        }
        var mappedLabel = TOP_NAV_LABEL_MAP[navPath] || "";
        if (!mappedLabel) {
          if (text.indexOf("양도양수") >= 0) mappedLabel = "양도매물";
          else if (text.indexOf("건설업등록") >= 0) mappedLabel = "신규등록";
          else if (text.indexOf("고객센터") >= 0) mappedLabel = "상담센터";
        }
        if (mappedLabel) {
          topAnchor.textContent = mappedLabel;
          text = mappedLabel;
        }
        var finalLabel = compactText(text || topAnchor.textContent || "");
        if (finalLabel) {
          topAnchor.setAttribute("aria-label", finalLabel + " 페이지 이동");
          topAnchor.setAttribute("title", finalLabel);
        }
        var target = compactText(topAnchor.getAttribute("target") || "");
        if (target === "_") {
          if (/^https?:\\/\\//i.test(href) && href.indexOf(location.origin) !== 0) topAnchor.setAttribute("target", "_blank");
          else topAnchor.setAttribute("target", "_self");
        }
        var isActive = false;
        if (navPath) {
          if (navPath === "/mna" && pagePath.indexOf("/mna") === 0) isActive = true;
          else if (navPath === "/notice" && pagePath.indexOf("/notice") === 0) isActive = true;
          else if (pagePath === navPath || pagePath.indexOf(navPath + "/") === 0) isActive = true;
        }
        if (isActive) li.classList.add("smna-active");
        else li.classList.remove("smna-active");
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

  function fixHeroVideoFraming() {
    try {
      var style = document.getElementById("smna-hero-video-fix-style");
      if (!style) {
        style = document.createElement("style");
        style.id = "smna-hero-video-fix-style";
        style.textContent = ""
          + "#visual,.visual_slider{overflow:hidden !important;}"
          + "#visual .li,#visual .li .jarallax{overflow:hidden !important;}"
          + "#visual .li .jarallax{height:700px !important;min-height:700px !important;max-height:700px !important;}"
          + "#visual .li .jarallax video,#visual video{display:block !important;width:100% !important;height:100% !important;max-width:none !important;object-fit:cover !important;object-position:center center !important;margin:0 !important;transform:none !important;}"
          + "@media(max-width:1200px){#visual .li .jarallax{height:620px !important;min-height:620px !important;max-height:620px !important;}}"
          + "@media(max-width:980px){#visual .li .jarallax{height:56vw !important;min-height:320px !important;max-height:620px !important;}}";
        document.head.appendChild(style);
      }
    } catch (_e) {}
  }

  function tuneHeroCopyForCta() {
    try{var t=document.querySelectorAll("#visual .copy_area h2");for(var i=0;i<t.length;i+=1)t[i].textContent="대한민국 건설 M&A의 기준";var c=document.querySelectorAll("#visual .copy_area");for(var j=0;j<c.length;j+=1){var h=String(c[j].innerHTML||"");var f=h.replace(/건설업 양도 양수\\/신규먼?허\\/인수합병\\/기업진단/g,"자격 기반 데이터 진단·책임 상담");if(f!==h)c[j].innerHTML=f;}}catch(_e){}
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

  function detectPremiumMode() {
    try {
      var path = String(location.pathname || "").toLowerCase();
      var bo = "";
      try {
        bo = String(new URLSearchParams(location.search || "").get("bo_table") || "").toLowerCase();
      } catch (_e) {}
      if (path === "/premium" || path.indexOf("/premium/") === 0) return true;
      if (path.indexOf("/bbs/board.php") === 0 && bo === "premium") return true;
      if (path.indexOf("/bbs/write.php") === 0 && bo === "premium") return true;
      return false;
    } catch (_e) {
      return false;
    }
  }

  function isPremiumListMode() {
    try {
      if (!detectPremiumMode()) return false;
      var path = String(location.pathname || "").toLowerCase();
      if (/^\\/premium\\/\\d+/.test(path)) return false;
      if (document.querySelector("#bo_v_con, #bo_v")) return false;
      return true;
    } catch (_e) {
      return false;
    }
  }

  function _normalizePremiumLead(text) {
    var clean = compactText(text || "");
    if (!clean) return "";
    clean = clean.replace(/\\s*N\\s*새글\\b/gi, "");
    clean = clean.replace(/\\s*새글\\b/gi, "");
    clean = clean.replace(/\\s{2,}/g, " ").trim();
    return clean;
  }

  function _extractPremiumIndustry(text) {
    var clean = _normalizePremiumLead(text);
    if (!clean) return "프리미엄 매물";
    var head = clean.split("|")[0] || clean;
    head = head.replace(/\\(매물\\s*\\d+\\)/gi, "");
    head = head.replace(/\\s+양도.*$/i, "");
    head = compactText(head);
    return head || "프리미엄 매물";
  }

  function _splitPremiumSummaryBits(text) {
    var source = String(text || "");
    var out = [];
    var buf = "";
    for (var i = 0; i < source.length; i += 1) {
      var ch = source.charAt(i);
      if (ch === ",") {
        var prev = i > 0 ? source.charAt(i - 1) : "";
        var next = i + 1 < source.length ? source.charAt(i + 1) : "";
        if (/[0-9]/.test(prev) && /[0-9]/.test(next)) {
          buf += ch;
          continue;
        }
        var item = compactText(buf);
        if (item) out.push(item);
        buf = "";
        continue;
      }
      buf += ch;
    }
    var tail = compactText(buf);
    if (tail) out.push(tail);
    return out;
  }

  function _extractPremiumTags(text) {
    var clean = _normalizePremiumLead(text);
    var parts = clean.split("|");
    var rhs = compactText(parts.length > 1 ? parts.slice(1).join("|") : "");
    var rawBits = rhs ? _splitPremiumSummaryBits(rhs) : [];
    var out = [];
    for (var i = 0; i < rawBits.length; i += 1) {
      var bit = compactText(rawBits[i] || "");
      if (!bit) continue;
      bit = bit.replace(/\\s*N\\s*새글\\b/gi, "").replace(/\\s*새글\\b/gi, "").trim();
      if (!bit) continue;
      out.push(bit);
      if (out.length >= 3) break;
    }
    if (!out.length && clean) {
      var industry = _extractPremiumIndustry(clean);
      if (industry) out.push(industry + " 핵심 매물");
    }
    return out;
  }

  function _collectPremiumFeatureRows(limit) {
    try {
      var rows = [];
      var seen = {};
      var links = document.querySelectorAll('a[href*="/premium/"]');
      for (var i = 0; i < links.length; i += 1) {
        var node = links[i];
        if (!node || !node.getAttribute) continue;
        var href = normalizeOutboundUrl(node.getAttribute("href") || "");
        if (!/\\/premium\\/\\d+\\b/i.test(href)) continue;
        if (seen[href]) continue;
        var title = _normalizePremiumLead(node.textContent || "");
        if (!title || title === "목록") continue;
        seen[href] = true;
        rows.push({
          href: href,
          title: title,
          industry: _extractPremiumIndustry(title),
          tags: _extractPremiumTags(title),
        });
        if (rows.length >= Math.max(1, limit || 4)) break;
      }
      return rows;
    } catch (_e) {
      return [];
    }
  }

  function enhancePremiumLanding() {
    try {
      if (!detectPremiumMode()) return;
      var style = document.getElementById("smna-premium-style");
      if (!style) {
        style = document.createElement("style");
        style.id = "smna-premium-style";
        style.textContent = ""
          + ".sub_visual.smna-premium-hero{position:relative !important;overflow:hidden !important;display:flex !important;align-items:flex-start !important;min-height:248px !important;height:auto !important;margin-bottom:28px !important;background:linear-gradient(132deg,#081c30 0%,#0b3558 54%,#b57a2d 100%) !important;}"
          + ".sub_visual.smna-premium-hero::before{content:'';position:absolute;inset:0;background:radial-gradient(circle at 16% 18%,rgba(255,255,255,.16),transparent 29%),radial-gradient(circle at 88% 22%,rgba(255,214,153,.18),transparent 24%),linear-gradient(180deg,rgba(255,255,255,.05),rgba(0,0,0,.18));pointer-events:none;}"
          + ".sub_visual.smna-premium-hero .title_warp{position:relative;z-index:2;width:100%;height:auto !important;display:block !important;padding:144px 0 38px !important;}"
          + ".sub_visual.smna-premium-hero .table-cell{display:block !important;width:min(1180px,calc(100% - 40px));margin:0 auto;padding:0 14px;text-align:center;vertical-align:bottom;}"
          + ".sub_visual.smna-premium-hero .sub_title{display:block !important;margin:0 0 10px !important;color:rgba(232,244,255,.86) !important;font-size:14px !important;font-weight:900 !important;letter-spacing:.18em !important;text-transform:uppercase !important;}"
          + ".sub_visual.smna-premium-hero h3{display:block !important;max-width:780px !important;margin:0 auto !important;color:#ffffff !important;font-size:clamp(36px,3.8vw,52px) !important;line-height:1.05 !important;font-weight:900 !important;letter-spacing:-.03em !important;word-break:keep-all !important;text-shadow:0 10px 28px rgba(0,0,0,.28) !important;}"
          + ".sub_visual.smna-premium-hero .cover,.sub_visual.smna-premium-hero .bg{display:none !important;}"
          + ".smna-premium-inline-title{display:none !important;}"
          + ".loca-area .smna-premium-current button{cursor:default !important;background:#fff !important;}"
          + ".loca-area .smna-premium-current button span{display:inline-block !important;color:#444 !important;font-weight:700 !important;}"
          + ".loca-area .smna-premium-current button::before,.loca-area .smna-premium-current button::after{display:none !important;}"
          + "#smna-premium-strip{max-width:1180px;margin:0 auto 32px;padding:0 18px;font-family:Pretendard,'Noto Sans KR','Malgun Gothic',Arial,sans-serif;}"
          + "#smna-premium-strip .smna-premium-intro{display:grid;grid-template-columns:minmax(0,1fr);gap:18px;margin-bottom:16px;padding:24px;border:1px solid #d7e2ee;border-radius:22px;background:linear-gradient(180deg,#f9fbfd 0%,#eef4f9 100%);box-shadow:0 16px 34px rgba(10,31,53,.08);}"
          + "#smna-premium-strip .eyebrow{margin:0 0 10px;color:#8c6d42;font-size:12px;line-height:1.3;font-weight:900;letter-spacing:.18em;text-transform:uppercase;}"
          + "#smna-premium-strip h2{margin:0;color:#0b2944;font-size:32px;line-height:1.12;font-weight:900;letter-spacing:-.03em;word-break:keep-all;}"
          + "#smna-premium-strip p{margin:0;color:#4e5968;font-size:16px;line-height:1.72;word-break:keep-all;}"
          + "#smna-premium-strip .chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:2px;}"
          + "#smna-premium-strip .chips span{display:inline-flex;align-items:center;min-height:30px;padding:6px 11px;border-radius:999px;background:#ffffff;border:1px solid #d3dfea;color:#0d426d;font-size:13px;font-weight:800;line-height:1.2;}"
          + "#smna-premium-strip .cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;}"
          + "#smna-premium-strip .card{display:flex;flex-direction:column;min-height:240px;border-radius:22px;overflow:hidden;background:#ffffff;border:1px solid #d7e2ee;box-shadow:0 18px 36px rgba(10,31,53,.09);}"
          + "#smna-premium-strip .card-cover{position:relative;padding:18px 18px 16px;min-height:114px;background:linear-gradient(132deg,#0b2b47 0%,#0d4a79 62%,#c58d42 100%);color:#ffffff;}"
          + "#smna-premium-strip .card-cover::after{content:'';position:absolute;right:-26px;bottom:-28px;width:108px;height:108px;border-radius:50%;background:rgba(255,255,255,.12);}"
          + "#smna-premium-strip .card-badge{display:inline-flex;align-items:center;justify-content:center;min-height:24px;padding:4px 9px;border-radius:999px;border:1px solid rgba(255,255,255,.32);background:rgba(255,255,255,.12);font-size:11px;font-weight:900;letter-spacing:.12em;text-transform:uppercase;}"
          + "#smna-premium-strip .card-cover strong{display:block;position:relative;z-index:1;margin-top:16px;font-size:27px;line-height:1.08;font-weight:900;letter-spacing:-.03em;word-break:keep-all;}"
          + "#smna-premium-strip .card-body{display:flex;flex:1 1 auto;flex-direction:column;gap:12px;padding:18px;}"
          + "#smna-premium-strip .card-title{margin:0;color:#0d2238;font-size:18px;line-height:1.5;font-weight:900;word-break:keep-all;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}"
          + "#smna-premium-strip .tag-list{display:flex;flex-wrap:wrap;gap:8px;min-height:32px;}"
          + "#smna-premium-strip .tag-list span{display:inline-flex;align-items:center;padding:6px 10px;border-radius:999px;background:#eef4f9;color:#24557f;font-size:12px;font-weight:800;line-height:1.2;}"
          + "#smna-premium-strip .card-link{display:inline-flex;align-items:center;justify-content:center;min-height:44px;margin-top:auto;padding:10px 14px;border-radius:12px;background:#0b3558;color:#ffffff !important;text-decoration:none !important;font-size:14px;font-weight:900;line-height:1.2;}"
          + "@media(max-width:980px){.sub_visual.smna-premium-hero{min-height:210px !important;height:auto !important;margin-bottom:20px !important;}.sub_visual.smna-premium-hero .title_warp{padding:98px 0 26px !important;}.sub_visual.smna-premium-hero .table-cell{width:calc(100% - 24px);padding:0 6px;}.sub_visual.smna-premium-hero h3{max-width:92% !important;font-size:34px !important;}#smna-premium-strip{padding:0 12px;}#smna-premium-strip .smna-premium-intro{padding:20px;border-radius:18px;}#smna-premium-strip h2{font-size:27px;}#smna-premium-strip .cards{grid-template-columns:1fr;}#smna-premium-strip .card{min-height:220px;}}";
        document.head.appendChild(style);
      }

      var hero = document.querySelector(".sub_visual");
      var mainTitleNode = document.querySelector("#bo_list h1, #bo_v h1, #bo_v_title .bo_v_tit, .content_wrap h1, h1");
      var mainTitle = compactText(mainTitleNode ? (mainTitleNode.textContent || "") : "");
      if (hero) {
        var sub = hero.querySelector(".sub_title");
        var h3 = hero.querySelector("h3");
        if (sub && !compactText(sub.textContent || "")) sub.textContent = "고객센터";
        if (h3 && !compactText(h3.textContent || "")) h3.textContent = mainTitle || "프리미엄 매물 정보";
        hero.classList.add("smna-premium-hero");
      }

      var loca = document.querySelector(".loca-area");
      if (loca) {
        var locaList = loca.querySelector("ul");
        var locaFirst = locaList ? locaList.querySelector("li") : null;
        var locaSpan = locaFirst ? locaFirst.querySelector("button span") : null;
        if (locaSpan && !compactText(locaSpan.textContent || "")) locaSpan.textContent = "고객센터";
        var emptyRows = loca.querySelectorAll(".next-depth li");
        for (var e = 0; e < emptyRows.length; e += 1) {
          var anchor = emptyRows[e].querySelector("a");
          if (!anchor) continue;
          if (compactText(anchor.textContent || "") || compactText(anchor.getAttribute("href") || "")) continue;
          if (emptyRows[e].parentNode) emptyRows[e].parentNode.removeChild(emptyRows[e]);
        }
        if (locaList && !loca.querySelector(".smna-premium-current")) {
          var current = document.createElement("li");
          current.className = "smna-premium-current";
          current.innerHTML = '<button type="button" aria-current="page"><span>프리미엄 매물 정보</span></button>';
          locaList.appendChild(current);
        }
      }

      if (!isPremiumListMode()) return;
      if (document.getElementById("smna-premium-strip")) return;

      var rows = _collectPremiumFeatureRows(4);
      if (!rows.length) return;
      var table = document.querySelector("#bo_list, .bo_list, table[caption*='프리미엄 매물 정보 목록']");
      if (!table || !table.parentNode) return;
      if (mainTitleNode && mainTitleNode.classList) mainTitleNode.classList.add("smna-premium-inline-title");

      var cards = "";
      for (var i = 0; i < rows.length; i += 1) {
        var row = rows[i];
        var tags = "";
        for (var j = 0; j < row.tags.length; j += 1) {
          tags += "<span>" + _escapeHtml(row.tags[j]) + "</span>";
        }
        cards += ""
          + '<article class="card">'
          + '  <div class="card-cover"><span class="card-badge">PREMIUM</span><strong>' + _escapeHtml(row.industry) + "</strong></div>"
          + '  <div class="card-body">'
          + '    <h3 class="card-title">' + _escapeHtml(row.title) + "</h3>"
          + '    <div class="tag-list">' + tags + "</div>"
          + '    <a class="card-link" href="' + _escapeHtml(row.href) + '">상세 매물 보기</a>'
          + "  </div>"
          + "</article>";
      }

      var strip = document.createElement("section");
      strip.id = "smna-premium-strip";
      strip.innerHTML = ""
        + '<div class="smna-premium-intro">'
        + '  <div>'
        + '    <p class="eyebrow">고객센터 PREMIUM</p>'
        + '    <h2>최근 프리미엄 매물 한눈에 보기</h2>'
        + '    <p>최근 등록된 프리미엄 매물을 한눈에 비교하고, 관심 매물은 상세 페이지에서 실적·실인수·신용·결산 상태까지 바로 확인할 수 있습니다.</p>'
        + "  </div>"
        + '  <div class="chips"><span>실적 비교</span><span>실인수 판단</span><span>신용·시평 체크</span><span>즉시 열람</span></div>'
        + "</div>"
        + '<div class="cards">' + cards + "</div>";

      table.parentNode.insertBefore(strip, table);
    } catch (_e) {}
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
      var g5Member = "";
      if (typeof window.g5_is_member !== "undefined") g5Member = String(window.g5_is_member || "").trim().toLowerCase();
      else if (typeof g5_is_member !== "undefined") g5Member = String(g5_is_member || "").trim().toLowerCase();
      if (g5Member === "1" || g5Member === "true" || g5Member === "y" || g5Member === "yes") return true;
      if (g5Member === "0" || g5Member === "" || g5Member === "false" || g5Member === "n" || g5Member === "no") return false;

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
    return mode === "acquisition" ? "AI 인허가 사전검토 진단기(신규등록 전용)" : "AI 양도가 산정 계산기";
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
        + (ACQUISITION_URL ? '  <a class="btn btn-sub smna-calc-link" data-smna-calc-link="1" href="' + ACQUISITION_URL + '">AI 인허가 사전검토</a>' : "")
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
    bindLoginIdCapture();
    _localAutoPullStateOnce();
    _captureRecentMnaFromPage();
    stabilizeHeaderAndNav();
    mountMnaPocketPanel();
    tuneMnaSearchSelectUx();
    rewriteFooterCopyright();
    ensureFooterBusinessIdentity();
    ensureKakaoOpenChatLink();
    if (!mainPath && bridged) applyBridgeTopOffset();
    fixHeroVideoFraming();
    tuneHeroCopyForCta();
    enhancePremiumLanding();
    enhanceQuickMenu();
    blockLegacyQuickMenu();
    sanitizeUtilityLinks();
    applyLoginGateToCalculatorLinks(document);
    enhanceLoginPageGoogleCta();
    if (!bridged) {
      mountBanner();
      applyLoginGateToCalculatorLinks(document);
    }
    if (!mainPath) dedupeMnaMobileList();
    setTimeout(enhanceQuickMenu, 180);
    setTimeout(enhanceQuickMenu, 1400);
    setTimeout(blockLegacyQuickMenu, 240);
    setTimeout(blockLegacyQuickMenu, 1600);
    setTimeout(_captureRecentMnaFromPage, 180);
    setTimeout(_captureRecentMnaFromPage, 1200);
    setTimeout(fixHeroVideoFraming, 160);
    setTimeout(fixHeroVideoFraming, 1400);
    setTimeout(enhancePremiumLanding, 220);
    setTimeout(enhancePremiumLanding, 1200);
    setTimeout(mountMnaPocketPanel, 280);
    setTimeout(mountMnaPocketPanel, 1400);
    setTimeout(tuneMnaSearchSelectUx, 340);
    setTimeout(tuneMnaSearchSelectUx, 1400);
    setTimeout(rewriteFooterCopyright, 180);
    setTimeout(rewriteFooterCopyright, 1200);
    setTimeout(ensureFooterBusinessIdentity, 260);
    setTimeout(ensureFooterBusinessIdentity, 1200);
    setTimeout(ensureKakaoOpenChatLink, 400);
    setTimeout(ensureKakaoOpenChatLink, 1400);
    setTimeout(sanitizeUtilityLinks, 180);
    setTimeout(sanitizeUtilityLinks, 980);
    setTimeout(function() { applyLoginGateToCalculatorLinks(document); }, 260);
    setTimeout(function() { applyLoginGateToCalculatorLinks(document); }, 1200);
    setTimeout(bindLoginIdCapture, 260);
    setTimeout(bindLoginIdCapture, 1200);
    setTimeout(_localAutoPullStateOnce, 260);
    setTimeout(_localAutoPullStateOnce, 1400);
    setTimeout(enhanceLoginPageGoogleCta, 180);
    setTimeout(enhanceLoginPageGoogleCta, 1200);
    setTimeout(stabilizeHeaderAndNav, 220);
    setTimeout(stabilizeHeaderAndNav, 1200);
    if (mode) {
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
      if (!window.__smna_quick_guard_observer__) {
        window.__smna_quick_guard_observer__ = new MutationObserver(function() {
          if (window.__smna_qg_timer__) return;
          window.__smna_qg_timer__ = window.setTimeout(function() {
            window.__smna_qg_timer__ = 0;
            var host = document.getElementById("smna-generated-right-side");
            var hasLegacy = !!document.querySelector("#right-side, #quick, #quicks, .quick_menu");
            var hostReady = !!(host && host.querySelector(".smna-qbtn"));
            if (!hasLegacy && hostReady) return;
            blockLegacyQuickMenu();
            if (!hostReady) enhanceQuickMenu();
          }, 260);
        });
        window.__smna_quick_guard_observer__.observe(document.body, { childList: true, subtree: true });
      }
    } catch (_e) {}

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
            _captureRecentMnaFromPage();
            mountMnaPocketPanel();
            tuneMnaSearchSelectUx();
            rewriteFooterCopyright();
            ensureFooterBusinessIdentity();
            ensureKakaoOpenChatLink();
            bindLoginIdCapture();
            _localAutoPullStateOnce();
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
    rendered = (
        template.replace("__TARGET__", repr(target))
        .replace("__ACQUISITION__", repr(acquisition))
        .replace("__FRAME_CUSTOMER__", repr(frame_customer))
        .replace("__FRAME_ACQUISITION__", repr(frame_acquisition))
        .replace("__KAKAO__", repr(kakao))
        .replace("__PHONE__", repr(phone))
        .replace("__SHOW_MAIN_BANNER__", "true" if show_main_banner else "false")
    )
    # cf_add_script 저장 길이 한도를 넘기지 않도록 공백/들여쓰기를 적극 압축한다.
    compact_lines = []
    for raw in str(rendered).splitlines():
        line = str(raw or "").strip()
        if not line:
            continue
        compact_lines.append(line)
    return "\n".join(compact_lines).replace("\ufeff", "").replace("\u200b", "")


def build_traffic_counter_snippet(
    namespace: str = "seoulmna.co.kr",
    show_customer: bool = True,
    show_admin: bool = True,
) -> str:
    ns = str(namespace or "").strip() or "seoulmna.co.kr"
    template = """<!-- SEOULMNA TRAFFIC COUNTER START -->
<script>(function(){
if(window.__smna_tc__) return;
window.__smna_tc__ = 1;
var NS=__NAMESPACE__,SC=__SHOW_CUSTOMER__,SA=__SHOW_ADMIN__,API='https://abacus.jasoncameron.dev',
    D=new Date(),
    DAY=D.getFullYear()+('0'+(D.getMonth()+1)).slice(-2)+('0'+D.getDate()).slice(-2),
    ADM=(/[?&]smna_admin_traffic=1/.test(location.search)||/\\/adm\\//i.test(location.pathname)),
    BOT=/bot|crawl|spider|headless/i.test((navigator.userAgent||'').toLowerCase())||!!navigator.webdriver,
    K={ad:'v_all_d_'+DAY,at:'v_all_t',hd:'v_human_d_'+DAY,ht:'v_human_t'},
    CK='smna_tc_cache_'+DAY,
    TTL=600000;
function N(V){V=Number(V||0);return isFinite(V)&&V>0?Math.floor(V):0}
function R(T,K){return fetch(API+'/'+T+'/'+encodeURIComponent(NS)+'/'+encodeURIComponent(K),{cache:'no-store'}).then(function(X){return X.json()}).then(function(J){return N(J&&J.value)}).catch(function(){return 0})}
function G(){try{return JSON.parse(sessionStorage.getItem(CK)||'null')}catch(_e){return null}}
function S(O){try{sessionStorage.setItem(CK,JSON.stringify(O||{}))}catch(_e){}}
function W(ID,TXT,CSS,P){var E=document.getElementById(ID);if(!E){E=document.createElement('div');E.id=ID;var R=P||document.body||document.documentElement;if(!R)return;R.appendChild(E)}if(CSS)E.style.cssText=CSS;E.textContent=TXT}
function H(){
  var old = document.getElementById('smna-traffic-customer');
  if(old && old.parentNode) old.parentNode.removeChild(old);
  var stale = document.querySelectorAll('body > div, #wrap > div, #wrapper > div, #header div');
  for(var i=0;i<stale.length;i+=1){
    var n = stale[i];
    if(!n || n.id==='smna-traffic-admin' || n.id==='smna-traffic-customer-mini') continue;
    var t = String(n.textContent||'').replace(/\\s+/g,' ').trim();
    if(!t || t.length>40) continue;
    if(t.indexOf('오늘 방문')>=0 && t.indexOf('누적 방문')>=0){
      n.style.display='none';
      n.setAttribute('data-smna-traffic-legacy','1');
    }
  }
}
function P(C){
  if(SC){H();W('smna-traffic-customer-mini',String(N(C&&C.at)),'position:fixed;right:10px;bottom:10px;z-index:9998;color:#7a8592;font:600 10px/1.2 sans-serif;letter-spacing:.02em;opacity:.85;pointer-events:none;background:transparent;padding:0;margin:0')}
  if(SA&&ADM)W('smna-traffic-admin','관리자(봇제외) 오늘 '+N(C&&C.hd)+'명 · 누적 '+N(C&&C.ht)+'명','position:fixed;left:12px;bottom:12px;z-index:9999;padding:8px 10px;border-radius:10px;background:#0e2f4f;color:#e8f3ff;font:600 11px/1.35 sans-serif')
}
var C=G(),NOW=Date.now();
try{
  if(sessionStorage.getItem('smna_tc_day')!==DAY){
    sessionStorage.setItem('smna_tc_day',DAY);
    R('hit',K.ad);R('hit',K.at);
    if(!BOT){R('hit',K.hd);R('hit',K.ht)}
    C=null;
  }
}catch(_e){R('hit',K.ad);R('hit',K.at)}
if(C&&NOW-N(C.ts)<TTL&&(!ADM||(typeof C.hd!=='undefined'&&typeof C.ht!=='undefined'))){P(C);return}
var T=[R('get',K.ad),R('get',K.at)];
if(SA&&ADM){T.push(R('get',K.hd));T.push(R('get',K.ht))}
Promise.all(T).then(function(V){var O={ad:N(V[0]),at:N(V[1]),ts:Date.now()};if(SA&&ADM){O.hd=N(V[2]);O.ht=N(V[3])}P(O);S(O)})
})();</script>
<!-- SEOULMNA TRAFFIC COUNTER END -->"""
    rendered = (
        template.replace("__NAMESPACE__", repr(ns))
        .replace("__SHOW_CUSTOMER__", "true" if show_customer else "false")
        .replace("__SHOW_ADMIN__", "true" if show_admin else "false")
    )
    compact_lines = []
    for raw in str(rendered).splitlines():
        line = str(raw or "").strip()
        if not line:
            continue
        compact_lines.append(line)
    return "\n".join(compact_lines).replace("\ufeff", "").replace("\u200b", "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate seoulmna.co.kr global banner snippet for admin config")
    parser.add_argument("--target-url", default="https://seoulmna.co.kr/bbs/content.php?co_id=ai_calc")
    parser.add_argument("--acquisition-url", default="https://seoulmna.co.kr/bbs/content.php?co_id=ai_acq")
    parser.add_argument("--frame-customer-url", default="")
    parser.add_argument("--frame-acquisition-url", default="")
    parser.add_argument("--kakao-openchat-url", default="")
    parser.add_argument("--contact-phone", default="")
    parser.add_argument("--show-main-banner", action="store_true", help="Show banner on main page (default: hidden until manually enabled)")
    parser.add_argument("--traffic-namespace", default="")
    parser.add_argument("--disable-traffic-counter", action="store_true")
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
    banner_snippet = build_banner_snippet(
        str(args.target_url).strip(),
        acquisition_url=str(args.acquisition_url).strip(),
        frame_customer_url=str(args.frame_customer_url).strip() or str(env.get("GAS_YANGDO_WEBAPP_URL", "")).strip(),
        frame_acquisition_url=str(args.frame_acquisition_url).strip() or str(env.get("GAS_ACQUISITION_WEBAPP_URL", "")).strip(),
        kakao_openchat_url=kakao_openchat_url,
        contact_phone=contact_phone,
        show_main_banner=bool(args.show_main_banner),
    )
    traffic_namespace = (
        str(args.traffic_namespace).strip()
        or str(env.get("TRAFFIC_COUNTER_NAMESPACE", "")).strip()
        or "seoulmna.co.kr"
    )
    traffic_enabled_env = str(env.get("TRAFFIC_COUNTER_ENABLED", "1")).strip().lower()
    traffic_enabled = (not bool(args.disable_traffic_counter)) and (traffic_enabled_env not in {"0", "false", "off", "no"})
    traffic_snippet = ""
    if traffic_enabled:
        traffic_snippet = build_traffic_counter_snippet(
            namespace=traffic_namespace,
            show_customer=True,
            show_admin=True,
        )
    snippet = (banner_snippet + ("\n" + traffic_snippet if traffic_snippet else "")).strip()
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
        "- 방문자 카운터: 고객용(오늘/누적), 관리자용(봇 제외 추정) 자동 표시",
        "",
        "타겟 링크:",
        f"- {args.target_url}",
        f"- {args.acquisition_url}",
        "",
        "카카오 오픈채팅 삽입:",
        f"- URL: {kakao_openchat_url or '(미설정)'}",
        f"- 대표전화: {contact_phone}",
        "- footer 대표전화 하단에 자동 삽입 시도",
        "",
        "방문자 카운터:",
        f"- enabled: {'yes' if traffic_enabled else 'no'}",
        f"- namespace: {traffic_namespace}",
        "- abacus.jasoncameron.dev 기반(세션당 1회 hit, 조회값은 세션 캐시(TTL 10분) 사용)",
    ]
    # Windows 기본 편집기에서도 한글이 깨지지 않도록 BOM 포함 UTF-8로 저장한다.
    guide_path.write_text("\n".join(guide) + "\n", encoding="utf-8-sig")

    print(f"[snippet] {snippet_path}")
    print(f"[guide] {guide_path}")
    print(f"[kakao_openchat] {kakao_openchat_url or 'EMPTY'}")
    print(f"[contact_phone] {contact_phone}")
    print(f"[traffic_counter] {'ENABLED' if traffic_enabled else 'DISABLED'} namespace={traffic_namespace}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

