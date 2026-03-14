/**
 * 서울건설정보 — Embeddable Quick-Menu Widget
 * v1.0.0
 *
 * Usage:
 *   <script src="https://seoulmna.kr/embed/widget.js" defer></script>
 *
 * Options (data attributes on the script tag):
 *   data-position="left"        — left | right (default: right)
 *   data-color="#003764"         — brand color override
 *   data-label="건설업 AI 분석"   — tooltip label override
 *   data-yangdo="true"          — show 양도가 산정 (default: true)
 *   data-permit="true"          — show 인허가 검토 (default: true)
 *
 * Example:
 *   <script src="https://seoulmna.kr/embed/widget.js"
 *           data-position="left" defer></script>
 *
 * SECURITY NOTE: All innerHTML assignments below use ONLY compile-time
 * string literal SVGs and hardcoded brand HTML. No user input is ever
 * interpolated into innerHTML. This is safe and intentional.
 */
(function () {
  "use strict";

  // Prevent double-init
  if (window.__seoulmnaWidget) return;
  window.__seoulmnaWidget = true;

  // ── Read config from script tag ──
  var script =
    document.currentScript ||
    document.querySelector('script[src*="widget.js"]');
  var cfg = {
    position: (script && script.getAttribute("data-position")) || "right",
    color: (script && script.getAttribute("data-color")) || "#003764",
    label:
      (script && script.getAttribute("data-label")) || "건설업 AI 분석",
    yangdo: (script && script.getAttribute("data-yangdo")) !== "false",
    permit: (script && script.getAttribute("data-permit")) !== "false",
  };

  var BASE = "https://seoulmna.kr";

  // ── Styles ──
  var css = [
    ".smn-fab{",
    "  position:fixed;bottom:24px;",
    cfg.position === "left" ? "left:24px;" : "right:24px;",
    "  z-index:2147483646;",
    "  font-family:-apple-system,BlinkMacSystemFont,'Pretendard','Noto Sans KR',sans-serif;",
    "  font-size:14px;line-height:1.5;",
    "  -webkit-font-smoothing:antialiased;",
    "}",
    ".smn-fab *{box-sizing:border-box;margin:0;padding:0;}",

    /* Trigger button */
    ".smn-trigger{",
    "  width:56px;height:56px;border-radius:50%;border:none;cursor:pointer;",
    "  background:" + cfg.color + ";color:#fff;",
    "  box-shadow:0 4px 20px rgba(0,55,100,.25);",
    "  display:flex;align-items:center;justify-content:center;",
    "  transition:transform .2s cubic-bezier(.4,0,.2,1),box-shadow .2s;",
    "  outline:none;",
    "}",
    ".smn-trigger:hover{transform:scale(1.08);box-shadow:0 6px 28px rgba(0,55,100,.35);}",
    ".smn-trigger:focus-visible{outline:2px solid " + cfg.color + ";outline-offset:3px;}",
    ".smn-trigger:active{transform:scale(.95);}",
    ".smn-trigger svg{width:26px;height:26px;pointer-events:none;}",

    /* Menu panel */
    ".smn-menu{",
    "  position:absolute;bottom:68px;",
    cfg.position === "left" ? "left:0;" : "right:0;",
    "  min-width:220px;padding:8px 0;",
    "  background:#fff;border-radius:14px;",
    "  box-shadow:0 12px 40px rgba(0,55,100,.14);",
    "  opacity:0;transform:translateY(8px) scale(.96);",
    "  transition:opacity .2s,transform .2s cubic-bezier(.4,0,.2,1);",
    "  pointer-events:none;",
    "  border:1px solid rgba(0,55,100,.08);",
    "}",
    ".smn-menu.smn-open{opacity:1;transform:translateY(0) scale(1);pointer-events:auto;}",

    /* Menu header */
    ".smn-menu-head{",
    "  padding:12px 16px 8px;font-size:11px;font-weight:600;",
    "  color:#8899a6;text-transform:uppercase;letter-spacing:.06em;",
    "}",

    /* Menu items */
    ".smn-item{",
    "  display:flex;align-items:center;gap:10px;",
    "  padding:10px 16px;text-decoration:none;color:#1a1a2e;",
    "  transition:background .15s;cursor:pointer;border:none;background:none;width:100%;",
    "  font-size:14px;font-family:inherit;text-align:left;",
    "}",
    ".smn-item:hover{background:rgba(0,55,100,.04);}",
    ".smn-item:focus-visible{outline:2px solid " + cfg.color + ";outline-offset:-2px;}",
    ".smn-item-icon{",
    "  width:36px;height:36px;border-radius:10px;flex-shrink:0;",
    "  display:flex;align-items:center;justify-content:center;",
    "}",
    ".smn-item-icon svg{width:18px;height:18px;}",
    ".smn-item-label{font-weight:600;color:#1a1a2e;}",
    ".smn-item-desc{font-size:12px;color:#6b7280;margin-top:1px;}",

    /* Divider */
    ".smn-divider{height:1px;background:rgba(0,55,100,.06);margin:4px 12px;}",

    /* Branding */
    ".smn-brand{",
    "  padding:8px 16px 10px;font-size:11px;color:#adb5bd;text-align:center;",
    "}",
    ".smn-brand a{color:#8899a6;text-decoration:none;}",
    ".smn-brand a:hover{text-decoration:underline;}",

    /* Animation: rotate icon */
    ".smn-trigger .smn-icon-close{display:none;}",
    ".smn-trigger.smn-active .smn-icon-open{display:none;}",
    ".smn-trigger.smn-active .smn-icon-close{display:block;}",
    ".smn-trigger.smn-active{background:" + cfg.color + ";}",

    /* Mobile */
    "@media(max-width:480px){",
    "  .smn-fab{bottom:16px;" + (cfg.position === "left" ? "left:16px;" : "right:16px;") + "}",
    "  .smn-trigger{width:50px;height:50px;}",
    "  .smn-menu{min-width:200px;bottom:62px;}",
    "}",

    /* Reduced motion */
    "@media(prefers-reduced-motion:reduce){",
    "  .smn-trigger,.smn-menu{transition:none !important;}",
    "}",
  ].join("\n");

  // ── SVG Icons (compile-time literals — safe for innerHTML) ──
  var SVG_OPEN =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<rect x="3" y="3" width="7" height="7" rx="1"/>' +
    '<rect x="14" y="3" width="7" height="7" rx="1"/>' +
    '<rect x="3" y="14" width="7" height="7" rx="1"/>' +
    '<rect x="14" y="14" width="7" height="7" rx="1"/>' +
    "</svg>";

  var SVG_CLOSE =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<line x1="18" y1="6" x2="6" y2="18"/>' +
    '<line x1="6" y1="6" x2="18" y2="18"/>' +
    "</svg>";

  var SVG_YANGDO =
    '<svg viewBox="0 0 24 24" fill="none" stroke="#003764" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<line x1="12" y1="1" x2="12" y2="23"/>' +
    '<path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>' +
    "</svg>";

  var SVG_PERMIT =
    '<svg viewBox="0 0 24 24" fill="none" stroke="#003764" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M9 11l3 3L22 4"/>' +
    '<path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>' +
    "</svg>";

  // ── Build DOM ──
  function build() {
    var root = document.createElement("div");
    root.className = "smn-fab";
    root.setAttribute("role", "region");
    root.setAttribute("aria-label", cfg.label);

    // Scoped style
    var style = document.createElement("style");
    style.textContent = css;
    root.appendChild(style);

    // Menu
    var menu = document.createElement("div");
    menu.className = "smn-menu";
    menu.id = "smn-menu";
    menu.setAttribute("role", "menu");
    menu.setAttribute("aria-label", "AI 서비스 메뉴");

    var head = document.createElement("div");
    head.className = "smn-menu-head";
    head.textContent = "AI 서비스";
    menu.appendChild(head);

    if (cfg.yangdo) {
      menu.appendChild(
        makeItem(
          SVG_YANGDO,
          "#E8F4FF",
          "AI 양도가 산정",
          "면허 적정가 즉시 분석",
          BASE + "/widget/yangdo"
        )
      );
    }

    if (cfg.yangdo && cfg.permit) {
      var divider = document.createElement("div");
      divider.className = "smn-divider";
      divider.setAttribute("role", "separator");
      menu.appendChild(divider);
    }

    if (cfg.permit) {
      menu.appendChild(
        makeItem(
          SVG_PERMIT,
          "#E6FFF5",
          "AI 인허가 검토",
          "191개 업종 등록기준 진단",
          BASE + "/widget/permit"
        )
      );
    }

    // Branding (compile-time literal HTML — safe)
    var brand = document.createElement("div");
    brand.className = "smn-brand";
    var brandLink = document.createElement("a");
    brandLink.href = BASE;
    brandLink.target = "_blank";
    brandLink.rel = "noopener noreferrer";
    brandLink.textContent = "서울건설정보";
    brand.appendChild(document.createTextNode("powered by "));
    brand.appendChild(brandLink);
    menu.appendChild(brand);

    root.appendChild(menu);

    // Trigger button
    var btn = document.createElement("button");
    btn.className = "smn-trigger";
    btn.setAttribute("aria-label", cfg.label + " 메뉴 열기");
    btn.setAttribute("aria-expanded", "false");
    btn.setAttribute("aria-controls", "smn-menu");

    // Build icon spans using DOM (SVG literals are safe compile-time constants)
    var spanOpen = document.createElement("span");
    spanOpen.className = "smn-icon-open";
    spanOpen.innerHTML = SVG_OPEN; // safe: compile-time SVG literal
    var spanClose = document.createElement("span");
    spanClose.className = "smn-icon-close";
    spanClose.innerHTML = SVG_CLOSE; // safe: compile-time SVG literal
    btn.appendChild(spanOpen);
    btn.appendChild(spanClose);

    var isOpen = false;

    function toggle() {
      isOpen = !isOpen;
      menu.classList.toggle("smn-open", isOpen);
      btn.classList.toggle("smn-active", isOpen);
      btn.setAttribute("aria-expanded", String(isOpen));
      btn.setAttribute(
        "aria-label",
        cfg.label + (isOpen ? " 메뉴 닫기" : " 메뉴 열기")
      );
      if (isOpen) {
        var first = menu.querySelector(".smn-item");
        if (first) first.focus();
      }
    }

    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      toggle();
    });

    // Close on outside click
    document.addEventListener("click", function (e) {
      if (isOpen && !root.contains(e.target)) {
        toggle();
      }
    });

    // Close on Escape
    document.addEventListener("keydown", function (e) {
      if (isOpen && e.key === "Escape") {
        toggle();
        btn.focus();
      }
    });

    root.appendChild(btn);
    document.body.appendChild(root);
  }

  function makeItem(iconSvg, bgColor, label, desc, href) {
    var a = document.createElement("a");
    a.className = "smn-item";
    a.href = href;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.setAttribute("role", "menuitem");

    var icon = document.createElement("span");
    icon.className = "smn-item-icon";
    icon.style.background = bgColor;
    icon.innerHTML = iconSvg; // safe: compile-time SVG literal
    a.appendChild(icon);

    var text = document.createElement("span");
    var lbl = document.createElement("span");
    lbl.className = "smn-item-label";
    lbl.textContent = label;
    text.appendChild(lbl);

    var d = document.createElement("span");
    d.className = "smn-item-desc";
    d.textContent = desc;
    text.appendChild(d);

    a.appendChild(text);
    return a;
  }

  // ── Init ──
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", build);
  } else {
    build();
  }
})();
