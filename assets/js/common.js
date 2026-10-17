/* 中国人口数据 — 公共脚本
 * 阶段 1：数据加载、格式化、图表统一样式
 */
(function () {
  "use strict";

  var C = {
    ink: "#1c1c1a",
    ink2: "#57544e",
    ink3: "#8b877e",
    line: "#e7e3d9",
    grid: "#f0ede5",
    accent: "#1f4e5f",
    accent2: "#4d8194",
    warm: "#b8552f",
    warm2: "#d08a6a",
    gold: "#b08a2e",
    green: "#5b7c5a"
  };

  var FONT = '"Segoe UI", -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif';

  /* ---------- 格式化 ---------- */

  function yi(v, d) {            // 人 -> 亿
    return (v / 1e8).toFixed(d === undefined ? 2 : d);
  }
  function wan(v, d) {           // 人 -> 万
    return (v / 1e4).toFixed(d === undefined ? 0 : d);
  }
  function signed(v, d) {
    var s = Math.abs(v).toFixed(d === undefined ? 0 : d);
    return (v > 0 ? "+" : v < 0 ? "\u2212" : "") + s;
  }
  function yearList(series) {
    return Object.keys(series.data).map(Number).sort(function (a, b) { return a - b; });
  }
  function values(series, years) {
    return years.map(function (y) {
      var v = series.data[String(y)];
      return v === undefined ? null : v;
    });
  }
  function last(series) {
    var ys = yearList(series);
    var y = ys[ys.length - 1];
    return { year: y, value: series.data[String(y)] };
  }
  function peak(series) {
    var ys = yearList(series), best = null;
    ys.forEach(function (y) {
      var v = series.data[String(y)];
      if (best === null || v > best.value) best = { year: y, value: v };
    });
    return best;
  }

  /* ---------- 数据加载 ---------- */

  function load() {
    return fetch("data/national.json", { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }

  function fail(el, msg) {
    if (!el) return;
    el.innerHTML =
      '<div class="err"><strong>数据加载失败。</strong> ' +
      (msg || "") +
      "<br>若你是直接双击打开的本地文件，浏览器会拦截读取本地 JSON 的请求。" +
      "请通过 http 服务访问，或查看线上站点。</div>";
  }

  /* ---------- 图表统一样式 ---------- */

  function axisCommon(extra) {
    var o = {
      axisLine: { lineStyle: { color: C.line } },
      axisTick: { show: false },
      axisLabel: { color: C.ink3, fontSize: 11.5, fontFamily: FONT, margin: 12 },
      splitLine: { lineStyle: { color: C.grid, type: "solid" } },
      nameTextStyle: { color: C.ink3, fontSize: 11.5, fontFamily: FONT, padding: [0, 0, 6, 0] }
    };
    if (extra) {
      Object.keys(extra).forEach(function (k) { o[k] = extra[k]; });
    }
    return o;
  }

  function tooltipCommon(extra) {
    var o = {
      backgroundColor: "#ffffff",
      borderColor: C.line,
      borderWidth: 1,
      padding: [10, 14],
      textStyle: { color: C.ink, fontSize: 12.5, fontFamily: FONT },
      extraCssText: "box-shadow:0 2px 10px rgba(0,0,0,0.06);border-radius:3px;"
    };
    if (extra) Object.keys(extra).forEach(function (k) { o[k] = extra[k]; });
    return o;
  }

  function lineSeries(name, data, color, opts) {
    opts = opts || {};
    return {
      name: name,
      type: "line",
      data: data,
      smooth: false,
      showSymbol: false,
      symbolSize: 5,
      lineStyle: { width: opts.width || 1.8, color: color },
      itemStyle: { color: color },
      connectNulls: false,
      areaStyle: opts.area ? {
        color: {
          type: "linear", x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: (opts.areaColor || color) + "26" },
            { offset: 1, color: (opts.areaColor || color) + "00" }
          ]
        }
      } : null,
      emphasis: { focus: "series" }
    };
  }

  window.CHP = {
    C: C,
    FONT: FONT,
    yi: yi,
    wan: wan,
    signed: signed,
    yearList: yearList,
    values: values,
    last: last,
    peak: peak,
    load: load,
    fail: fail,
    axisCommon: axisCommon,
    tooltipCommon: tooltipCommon,
    lineSeries: lineSeries
  };
})();
