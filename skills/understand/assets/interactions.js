(function () {
  "use strict";
  var LEVELS = ["overview", "standard", "deep"];
  var LABEL = { overview: "개요", standard: "표준", deep: "심층" };
  var body = document.body;
  var sections = Array.prototype.slice.call(document.querySelectorAll(".sec"));
  var global = 0;
  var local = {};
  var all = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };
  var idx = function (d) { return Math.max(0, LEVELS.indexOf(d)); };

  function anchor() {
    var top = document.querySelector(".top").getBoundingClientRect().bottom + 8;
    var candidates = all(".sec-head, .block, .rung, .limit-group, .principles > li, .lead");
    for (var i = 0; i < candidates.length; i++) {
      var r = candidates[i].getBoundingClientRect();
      if (r.bottom > top && r.height > 0) return { el: candidates[i], y: r.top };
    }
    return null;
  }

  function apply(keep) {
    var a = keep ? anchor() : null;
    body.setAttribute("data-zoom", LEVELS[global]);
    all(".seg").forEach(function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-zoom") === LEVELS[global])); });
    sections.forEach(function (sec) {
      var lv = Math.max(global, local[sec.id] || 0);
      sec.setAttribute("data-level", LEVELS[lv]);
      var hidden = all("[data-depth]", sec).filter(function (el) { return idx(el.getAttribute("data-depth")) > lv; });
      var more = sec.querySelector("[data-more]");
      var next = Math.min.apply(null, hidden.map(function (el) { return idx(el.getAttribute("data-depth")); }).concat([3]));
      more.hidden = next > 2;
      more.setAttribute("data-next", String(next));
      if (next <= 2) more.textContent = LABEL[LEVELS[next]] + "까지 더 보기";
      var b = sec.querySelector(".sec-body");
      var hint = b.querySelector(".empty-hint");
      var shown = all(":scope > *", b).filter(function (el) {
        return el !== hint && !(el.hasAttribute("data-depth") && idx(el.getAttribute("data-depth")) > lv);
      });
      hint.hidden = shown.length > 0;
    });
    if (a && a.el.getBoundingClientRect().height > 0) window.scrollBy({ top: a.el.getBoundingClientRect().top - a.y, behavior: "instant" });
  }

  all(".seg").forEach(function (b) {
    b.addEventListener("click", function () {
      global = idx(b.getAttribute("data-zoom"));
      local = {};
      apply(true);
    });
  });

  sections.forEach(function (sec) {
    sec.querySelector("[data-more]").addEventListener("click", function () {
      local[sec.id] = Number(sec.querySelector("[data-more]").getAttribute("data-next"));
      apply(false);
      var more = sec.querySelector("[data-more]");
      (more.hidden ? sec.querySelector("[data-fold]") : more).focus();
    });
    var fold = sec.querySelector("[data-fold]");
    var name = sec.querySelector("h2").textContent;
    fold.addEventListener("click", function () {
      var folded = sec.classList.toggle("folded");
      fold.setAttribute("aria-expanded", String(!folded));
      fold.textContent = folded ? "펼치기" : "접기";
      fold.setAttribute("aria-label", name + (folded ? " 펼치기" : " 접기"));
    });
  });

  function pick(trigger) {
    var scope = trigger.closest(".ladder, .block");
    var id = trigger.getAttribute("data-pick");
    var panel = scope.querySelector('[data-panel="' + id + '"]');
    var open = panel && panel.hidden;
    all("[data-panel]", scope).forEach(function (p) { p.hidden = true; });
    all("[data-pick]", scope).forEach(function (t) {
      var on = open && t.getAttribute("data-pick") === id;
      t.setAttribute(t.tagName === "BUTTON" ? "aria-expanded" : "aria-pressed", String(on));
    });
    if (panel) panel.hidden = !open;
    if (document.activeElement !== trigger) trigger.focus({ preventScroll: true });
  }
  all("[data-pick]").forEach(function (t) {
    t.addEventListener("click", function () { pick(t); });
    if (t.tagName !== "BUTTON") {
      t.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); pick(t); }
      });
    }
  });

  all("[data-answer]").forEach(function (b) {
    b.addEventListener("click", function () {
      var a = document.getElementById(b.getAttribute("data-answer"));
      a.hidden = !a.hidden;
      b.setAttribute("aria-expanded", String(!a.hidden));
      b.textContent = a.hidden ? "답 보기" : "답 숨기기";
    });
  });

  all("[data-scenario]").forEach(function (r) {
    r.addEventListener("change", function () {
      var out = document.querySelector('[data-outcome="' + r.getAttribute("data-scenario") + '"]');
      out.querySelector(".hint").hidden = true;
      all("[data-option]", out).forEach(function (o) { o.hidden = o.getAttribute("data-option") !== r.value; });
    });
  });

  var toc = document.querySelector(".toc");
  var tocBtn = toc.querySelector(".toc-toggle");
  function setToc(open) {
    toc.classList.toggle("open", open);
    tocBtn.setAttribute("aria-expanded", String(open));
  }
  tocBtn.addEventListener("click", function () { setToc(!toc.classList.contains("open")); });
  all(".toc a").forEach(function (a) {
    a.addEventListener("click", function () {
      var sec = document.querySelector(a.getAttribute("href"));
      if (sec && sec.classList.contains("folded")) sec.querySelector("[data-fold]").click();
      setToc(false);
    });
  });
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        all(".toc a").forEach(function (a) { a.setAttribute("aria-current", String(a.getAttribute("href") === "#" + en.target.id)); });
      });
    }, { rootMargin: "-30% 0px -60% 0px" });
    sections.forEach(function (s) { io.observe(s); });
  }

  document.querySelector("[data-reset]").addEventListener("click", function () {
    global = 0;
    local = {};
    all(".sec.folded [data-fold]").forEach(function (f) { f.click(); });
    all("[data-panel]").forEach(function (p) { p.hidden = true; });
    all("[data-pick]").forEach(function (t) { t.setAttribute(t.tagName === "BUTTON" ? "aria-expanded" : "aria-pressed", "false"); });
    all("[data-answer]").forEach(function (b) {
      document.getElementById(b.getAttribute("data-answer")).hidden = true;
      b.setAttribute("aria-expanded", "false");
      b.textContent = "답 보기";
    });
    all("[data-scenario]").forEach(function (r) { r.checked = false; });
    all("[data-outcome]").forEach(function (o) {
      o.querySelector(".hint").hidden = false;
      all("[data-option]", o).forEach(function (x) { x.hidden = true; });
    });
    all("details").forEach(function (d) { d.open = false; });
    setToc(false);
    apply(false);
    window.scrollTo({ top: 0, behavior: "instant" });
    document.querySelector('.seg[data-zoom="overview"]').focus({ preventScroll: true });
  });

  apply(false);
})();
