(function () {
  "use strict";
  var all = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  function evaluate(rpn, env) {
    var st = [];
    rpn.forEach(function (t) {
      if (t[0] === "n") st.push(t[1]);
      else if (t[0] === "v") st.push(env[t[1]]);
      else if (t[0] === "f") {
        if (t[1] === "round") st.push(Math.floor(st.pop() + 0.5));
        else if (t[1] === "abs") st.push(Math.abs(st.pop()));
        else { var b = st.pop(), a = st.pop(); st.push(t[1] === "min" ? Math.min(a, b) : Math.max(a, b)); }
      } else if (t[1] === "neg") st.push(-st.pop());
      else {
        var y = st.pop(), x = st.pop();
        switch (t[1]) {
          case "+": st.push(x + y); break;
          case "-": st.push(x - y); break;
          case "*": st.push(x * y); break;
          case "/": st.push(y ? x / y : NaN); break;
          case "<": st.push(+(x < y)); break;
          case "<=": st.push(+(x <= y)); break;
          case ">": st.push(+(x > y)); break;
          case ">=": st.push(+(x >= y)); break;
          case "==": st.push(+(x === y)); break;
          case "!=": st.push(+(x !== y)); break;
          case "&&": st.push(+(!!x && !!y)); break;
          default: st.push(+(!!x || !!y));
        }
      }
    });
    return st[0];
  }

  function fmt(v, digits) {
    if (!isFinite(v)) return "계산 불가";
    var s = v.toFixed(digits).replace(/^(-?\d+)/, function (m) { return m.replace(/\B(?=(\d{3})+(?!\d))/g, ","); });
    return /^-0(\.0+)?$/.test(s) ? "0" : s;
  }

  var spec = document.querySelector("[data-vars]");
  var outs = spec ? JSON.parse(spec.getAttribute("data-vars")) : [];
  var NS = "http://www.w3.org/2000/svg";
  var digits = {};
  function inputs() {
    var env = {};
    all("[data-in]").forEach(function (i) {
      env[i.getAttribute("data-in")] = Number(i.value);
      var f = String(i.step).split(".")[1];
      digits[i.getAttribute("data-in")] = f ? Math.min(2, f.length) : 0;
    });
    return env;
  }
  function solve(env) {
    outs.forEach(function (o) { env[o[0]] = evaluate(o[2], env); digits[o[0]] = o[1]; });
    return env;
  }
  function el(tag, attrs, text) {
    var n = document.createElementNS(NS, tag);
    Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (text !== undefined) n.textContent = text;
    return n;
  }
  function drawPlot(box, base) {
    var p = JSON.parse(box.getAttribute("data-plot"));
    var W = Math.max(300, Math.round(box.clientWidth || 640)), H = W < 500 ? 240 : 280, L = 58, R = 12, T = 30 + 16 * p.marks.length, B = 40, N = 81;
    var rows = [];
    for (var k = 0; k < N; k++) {
      var env = {};
      Object.keys(base).forEach(function (key) { env[key] = base[key]; });
      env[p.x] = p.min + (p.max - p.min) * k / (N - 1);
      rows.push(solve(env));
    }
    var lo = 0, hi = 0;
    rows.forEach(function (r) { p.ys.forEach(function (y) { lo = Math.min(lo, r[y[0]]); hi = Math.max(hi, r[y[0]]); }); });
    if (hi === lo) hi = lo + 1;
    var sx = function (v) { return L + (v - p.min) / (p.max - p.min) * (W - L - R); };
    var sy = function (v) { return T + (hi - v) / (hi - lo) * (H - T - B); };
    var svg = el("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": p.xl + "에 따른 변화" });
    svg.appendChild(el("line", { x1: L, y1: sy(0), x2: W - R, y2: sy(0), "class": "axis" }));
    svg.appendChild(el("line", { x1: L, y1: T, x2: L, y2: H - B, "class": "axis" }));
    svg.appendChild(el("text", { x: L - 6, y: sy(hi) + 4, "text-anchor": "end", "class": "tick" }, fmt(hi, 0)));
    svg.appendChild(el("text", { x: L - 6, y: sy(lo) + 4, "text-anchor": "end", "class": "tick" }, fmt(lo, 0)));
    svg.appendChild(el("text", { x: L, y: H - B + 18, "text-anchor": "start", "class": "tick" }, fmt(p.min, digits[p.x] || 0) + p.xu));
    svg.appendChild(el("text", { x: W - R, y: H - B + 18, "text-anchor": "end", "class": "tick" }, fmt(p.max, digits[p.x] || 0) + p.xu));
    svg.appendChild(el("text", { x: (L + W - R) / 2, y: H - 6, "text-anchor": "middle", "class": "tick" }, p.xl));
    p.marks.forEach(function (m, mi) {
      for (var k = 1; k < N; k++) {
        var a = !!evaluate(m[0], rows[k - 1]), b = !!evaluate(m[0], rows[k]);
        if (a !== b) {
          var lo2 = rows[k - 1][p.x], hi2 = rows[k][p.x];
          for (var it = 0; it < 30; it++) {
            var mid = (lo2 + hi2) / 2, envm = Object.assign({}, base);
            envm[p.x] = mid;
            if (!!evaluate(m[0], solve(envm)) === a) lo2 = mid; else hi2 = mid;
          }
          var xv = hi2, xm = sx(xv);
          var ly = 14 + 16 * mi, right = xm > W * 0.6;
          svg.appendChild(el("line", { x1: xm, y1: ly + 4, x2: xm, y2: H - B, "class": "mark" }));
          svg.appendChild(el("text", { x: right ? xm - 4 : xm + 4, y: ly, "text-anchor": right ? "end" : "start", "class": "mark-label", "data-mark": "" }, m[1] + " · 약 " + fmt(xv, digits[p.x] || 0) + p.xu));
        }
      }
    });
    p.ys.forEach(function (y, i) {
      var pts = rows.map(function (r) { return sx(r[p.x]).toFixed(1) + "," + sy(r[y[0]]).toFixed(1); }).join(" ");
      svg.appendChild(el("polyline", { points: pts, "class": "line s" + i, "data-y": y[0] }));
    });
    var cx = sx(base[p.x]);
    svg.appendChild(el("line", { x1: cx, y1: T, x2: cx, y2: H - B, "class": "now" }));
    var cur = solve(Object.assign({}, base));
    p.ys.forEach(function (y, i) { svg.appendChild(el("circle", { cx: cx, cy: sy(cur[y[0]]), r: 4, "class": "dot s" + i })); });
    box.textContent = "";
    box.appendChild(svg);
    var legend = document.createElement("ul");
    legend.className = "legend";
    p.ys.forEach(function (y, i) {
      var li = document.createElement("li");
      var sw = document.createElement("span");
      sw.className = "sw s" + i;
      li.appendChild(sw);
      li.appendChild(document.createTextNode(y[1] + " " + fmt(cur[y[0]], y[3]) + y[2]));
      legend.appendChild(li);
    });
    box.appendChild(legend);
  }
  function recompute() {
    var base = inputs();
    var env = solve(Object.assign({}, base));
    all("[data-out]").forEach(function (s) {
      var k = s.getAttribute("data-out");
      if (k in env) s.textContent = fmt(env[k], digits[k] || 0);
    });
    all("[data-plot]").forEach(function (b) { drawPlot(b, base); });
  }
  all("[data-in]").forEach(function (i) { i.addEventListener("input", recompute); });
  window.addEventListener("resize", function () { var base = inputs(); all("[data-plot]").forEach(function (b) { drawPlot(b, base); }); });
  recompute();

  all("[data-switch]").forEach(function (r) {
    r.addEventListener("change", function () {
      var out = document.querySelector('[data-outcome="' + r.getAttribute("data-switch") + '"]');
      all("[data-option]", out).forEach(function (o) { o.hidden = o.getAttribute("data-option") !== r.value; });
    });
  });
})();
