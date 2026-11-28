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
    var s = v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
    return /^-0(\.0+)?$/.test(s) ? "0" : s;
  }

  var spec = document.querySelector("[data-vars]");
  var env = {};
  function recompute() {
    all("[data-in]").forEach(function (i) { env[i.getAttribute("data-in")] = Number(i.value); });
    var digits = {};
    all("[data-in]").forEach(function (i) { var f = String(i.step).split(".")[1]; digits[i.getAttribute("data-in")] = f ? Math.min(2, f.length) : 0; });
    if (spec) JSON.parse(spec.getAttribute("data-vars")).forEach(function (o) {
      env[o[0]] = evaluate(o[2], env);
      digits[o[0]] = o[1];
    });
    all("[data-out]").forEach(function (s) {
      var k = s.getAttribute("data-out");
      if (k in env) s.textContent = fmt(env[k], digits[k] || 0);
    });
    all("[data-when]").forEach(function (n) { n.hidden = !evaluate(JSON.parse(n.getAttribute("data-when")), env); });
  }
  all("[data-in]").forEach(function (i) { i.addEventListener("input", recompute); });

  all("[data-story]").forEach(function (story) {
    var steps = all("[data-step]", story);
    var shows = steps.map(function (s) { return JSON.parse(s.getAttribute("data-show")); });
    var els = all("[data-el]", story);
    story.setAttribute("data-js", "");
    var current = -1;
    function show(k) {
      if (k === current) return;
      current = k;
      var on = {};
      for (var i = 0; i <= k; i++) shows[i].forEach(function (id) { on[id] = true; });
      var focus = {};
      shows[k].forEach(function (id) { focus[id] = true; });
      els.forEach(function (el) {
        var id = el.getAttribute("data-el");
        el.classList.toggle("on", !!on[id]);
        el.classList.toggle("focus", !!focus[id]);
      });
      steps.forEach(function (s, i) { s.classList.toggle("active", i === k); });
      var wrap = story.querySelector(".svg-wrap");
      var hits = all("[data-el].focus", story);
      if (wrap && hits.length && (wrap.scrollWidth > wrap.clientWidth || wrap.scrollHeight > wrap.clientHeight)) {
        var w = wrap.getBoundingClientRect(), box = null;
        hits.forEach(function (h) {
          var r = h.getBoundingClientRect();
          box = box ? { l: Math.min(box.l, r.left), t: Math.min(box.t, r.top), r: Math.max(box.r, r.right), b: Math.max(box.b, r.bottom) } : { l: r.left, t: r.top, r: r.right, b: r.bottom };
        });
        wrap.scrollLeft += (box.l + box.r) / 2 - (w.left + w.right) / 2;
        wrap.scrollTop += (box.t + box.b) / 2 - (w.top + w.bottom) / 2;
      }
      story.setAttribute("data-at", String(k));
    }
    function pick() {
      var mid = window.innerHeight * 0.5, best = 0;
      steps.forEach(function (s, i) { if (s.getBoundingClientRect().top < mid) best = i; });
      show(best);
    }
    window.addEventListener("scroll", pick, { passive: true });
    window.addEventListener("resize", pick);
    pick();
  });

  all("[data-switch]").forEach(function (r) {
    r.addEventListener("change", function () {
      var out = document.querySelector('[data-outcome="' + r.getAttribute("data-switch") + '"]');
      all("[data-option]", out).forEach(function (o) { o.hidden = o.getAttribute("data-option") !== r.value; });
    });
  });
})();
