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

  all("[data-sim]").forEach(function (sim) {
    var inputs = all("[data-in]", sim);
    function update() {
      var env = {};
      inputs.forEach(function (i) {
        env[i.getAttribute("data-in")] = Number(i.value);
        var show = sim.querySelector('[data-show="' + i.getAttribute("data-in") + '"]');
        show.textContent = fmt(Number(i.value), Number(i.step) % 1 === 0 ? 0 : 2);
      });
      all("[data-out]", sim).forEach(function (o) {
        var v = evaluate(JSON.parse(o.getAttribute("data-rpn")), env);
        env[o.getAttribute("data-out")] = v;
        o.textContent = fmt(v, Number(o.getAttribute("data-digits")));
      });
      var segs = all("[data-part]", sim);
      var total = segs.reduce(function (s, g) { return s + Math.max(0, env[g.getAttribute("data-part")]); }, 0) || 1;
      segs.forEach(function (g) { g.style.width = (Math.max(0, env[g.getAttribute("data-part")]) / total * 100).toFixed(1) + "%"; });
      all("[data-when]", sim).forEach(function (n) { n.hidden = !evaluate(JSON.parse(n.getAttribute("data-when")), env); });
    }
    inputs.forEach(function (i) { i.addEventListener("input", update); });
  });

  all("[data-switch]").forEach(function (r) {
    r.addEventListener("change", function () {
      var out = document.querySelector('[data-outcome="' + r.getAttribute("data-switch") + '"]');
      all("[data-option]", out).forEach(function (o) { o.hidden = o.getAttribute("data-option") !== r.value; });
    });
  });
})();
