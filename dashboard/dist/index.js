/* HALOFLUX dashboard tab — embeds the original HALOFLUX · AI LINK page
 * (served from this plugin's own static files) in a full-area iframe.
 * The page polls /api/plugins/haloflux/stats on the same origin.
 * A "open full screen" link is provided as well: it opens the same page
 * standalone, which is the nicest viewing mode on a phone (landscape). */
(function () {
  "use strict";

  var SDK = window.__HERMES_PLUGIN_SDK__;
  var React = SDK && SDK.React;
  var Plugins = window.__HERMES_PLUGINS__;

  if (!React || !Plugins || typeof Plugins.register !== "function") {
    // SDK 未就绪（Hermes 版本变动等）：显示一句降级提示，而不是抛错白屏。
    var msg = "HALOFLUX：Hermes 插件 SDK 未就绪，无法加载此页签。请升级 Hermes 或刷新页面后重试。";
    if (typeof console !== "undefined") console.warn("[haloflux] " + msg);
    var showNotice = function () {
      try {
        var d = document.createElement("div");
        d.textContent = msg;
        d.style.cssText = "padding:16px;font-size:13px;opacity:0.8";
        (document.body || document.documentElement).appendChild(d);
      } catch (e) { /* ignore */ }
    };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", showNotice);
    else showNotice();
    return;
  }

  var PAGE = "/dashboard-plugins/haloflux/dist/haloflux/index.html";

  function HalofluxPage() {
    return React.createElement(
      "div",
      {
        style: {
          display: "flex",
          flexDirection: "column",
          gap: "8px",
          height: "calc(100vh - 130px)",
          minHeight: "420px",
        },
      },
      React.createElement(
        "div",
        {
          style: {
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          },
        },
        React.createElement(
          "span",
          { style: { fontSize: "12px", opacity: 0.7 } },
          "HALOFLUX · AI LINK — Hermes 实时遥测（数据源：本机 state.db，只读）"
        ),
        React.createElement(
          "a",
          {
            href: PAGE,
            target: "_blank",
            rel: "noreferrer",
            style: { fontSize: "12px", whiteSpace: "nowrap" },
          },
          "全屏打开 ↗"
        )
      ),
      React.createElement("iframe", {
        src: PAGE,
        title: "HALOFLUX · AI LINK",
        style: {
          flex: "1",
          width: "100%",
          border: "0",
          borderRadius: "8px",
          background: "#000",
        },
      })
    );
  }

  Plugins.register("haloflux", HalofluxPage);
})();
