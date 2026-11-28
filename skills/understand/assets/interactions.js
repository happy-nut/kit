(function () {
  "use strict";
  var svg = document.querySelector(".stage svg");
  if (!svg) return;
  var all = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };
  var nodes = all("[data-part]", svg), links = all("[data-link]", svg), blocks = all("[data-show]");
  var stage = svg.parentNode;
  var set = function (s) { var o = {}; (s || "").split(" ").forEach(function (x) { if (x) o[x] = true; }); return o; };
  var current;

  // 읽는 자리에 걸린 글 덩어리의 상태(보이는 부분, 보이는 연결, 짚는 것)를 그림에 옮긴다. 덩어리 위면 뼈대 전체를 보인다.
  function apply(b) {
    if (b === current) return;
    current = b;
    var show = b ? set(b.getAttribute("data-show")) : null, ls = b ? set(b.getAttribute("data-links")) : null;
    var focus = b ? set(b.getAttribute("data-focus")) : {}, at = b ? set(b.getAttribute("data-at")) : {};
    svg.classList.toggle("known", !!b && b.getAttribute("data-mode") === "known");
    svg.classList.toggle("has-focus", Object.keys(focus).length > 0);
    nodes.forEach(function (n) {
      var id = n.getAttribute("data-part");
      n.classList.toggle("off", !!show && !show[id]);
      n.classList.toggle("on", !!focus[id]);
      n.classList.toggle("diff", !!at[id]);
    });
    links.forEach(function (l) {
      var id = l.getAttribute("data-link"), on = !!focus[id];
      l.classList.toggle("off", !!ls && !ls[id]);
      l.classList.toggle("on", on);
      var edge = l.querySelector(".edge");
      if (edge) edge.setAttribute("marker-end", "url(#" + svg.getAttribute(on ? "data-mon" : "data-moff") + ")");
    });
    blocks.forEach(function (x) { x.classList.toggle("now", x === b); });
    svg.setAttribute("data-block", b ? b.id : "");
  }
  function line() {
    var r = stage.getBoundingClientRect();
    return r.width > innerWidth * 0.8 ? r.bottom + 40 : innerHeight * 0.5;
  }
  function update() {
    var y = line(), hit = null;
    blocks.forEach(function (b) { if (b.getBoundingClientRect().top <= y) hit = b; });
    apply(hit);
  }
  var queued = false;
  addEventListener("scroll", function () {
    if (queued) return;
    queued = true;
    requestAnimationFrame(function () { queued = false; update(); });
  }, { passive: true });
  addEventListener("resize", update);
  update();
})();
