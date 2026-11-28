"""UNDERSTAND 설명 JSON 을 고정 디자인의 HTML 한 장으로 만든다.

쓰는 법: render.py <설명.json> <출력.html>
검사(validate.py)를 먼저 돌리고 오류가 있으면 쓰지 않는다.
모든 글은 이스케이프해 넣는다. sources·src 는 화면에 내보내지 않는다.
페이지의 스크립트는 템플릿의 것 하나뿐이고 CSP 해시로 묶는다. 시뮬레이터 식은 미리 RPN 으로 옮겨 넣는다.
"""
import base64, hashlib, html, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate import validate, edge_id, PLACEHOLDER  # noqa: E402
from expr import compile_expr, run_sim, fmt  # noqa: E402
from layout import layout, text_w  # noqa: E402

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
SECTIONS = [("story", "01", "작동 원리"), ("relations", "02", "핵심 관계"), ("application", "03", "적용과 한계")]
LIMIT_KINDS = [("condition", "성립 조건"), ("counterexample", "반례"), ("tradeoff", "트레이드오프"),
               ("assumption", "확인되지 않은 전제"), ("unknown", "아직 모르는 것")]

e = lambda s: html.escape(str(s), quote=True)
paras = lambda xs: "".join(f"<p>{e(x)}</p>" for x in xs)


def step_digits(step):
    s = repr(float(step))
    return 0 if float(step).is_integer() else min(2, len(s.split(".")[1]))


class Page:
    def __init__(self, data):
        self.d = data
        self.n = 0
        v = data["story"].get("vars")
        self.env, self.digits = {}, {}
        if v:
            outs, _ = run_sim(v)
            self.env = {i["id"]: float(i["value"]) for i in v["inputs"]}
            self.env.update(outs)
            self.digits = {o["id"]: int(o.get("digits", 0)) for o in v["outputs"]}
            self.digits.update({i["id"]: step_digits(i["step"]) for i in v["inputs"]})

    def uid(self, p):
        self.n += 1
        return f"{p}{self.n}"

    # ---- 값 채우기 ----
    def fill(self, text):
        """{변수} 를 계산된 값을 담은 span 으로. 나머지는 이스케이프."""
        out, last = "", 0
        for m in PLACEHOLDER.finditer(text):
            out += e(text[last:m.start()]) + self.value_span(m.group(1))
            last = m.end()
        return out + e(text[last:])

    def value_span(self, name):
        dg = self.digits.get(name, 0)
        return f'<span class="val" data-out="{e(name)}">{e(fmt(self.env.get(name, 0), dg))}</span>'

    def tspan_fill(self, text):
        out, last = "", 0
        for m in PLACEHOLDER.finditer(text):
            out += e(text[last:m.start()]) + f'<tspan class="val" data-out="{e(m.group(1))}">{e(fmt(self.env.get(m.group(1), 0), self.digits.get(m.group(1), 0)))}</tspan>'
            last = m.end()
        return out + e(text[last:])

    # ---- 그림 ----
    def svg_open(self, w, h, title):
        sid = self.uid("g")
        return sid, (f'<div class="svg-wrap"><svg viewBox="0 0 {w} {h}" width="{w}" style="--minw:{min(w, round(w * 0.85))}px" '
                     f'role="img" aria-labelledby="{sid}t" preserveAspectRatio="xMidYMin meet"><title id="{sid}t">{e(title)}</title>'
                     f'<defs><marker id="{sid}a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="arrow"/></marker></defs>')

    def stage(self, f):
        if f["kind"] == "sequence":
            return self.stage_sequence(f)
        wide = lambda t: PLACEHOLDER.sub("000,000", t)
        pos, w, h, paths = layout([{"id": n["id"], "label": wide(n["label"])} for n in f["nodes"]],
                                  [{**x, "label": wide(x["label"])} for x in f["edges"]])
        sid, out = self.svg_open(w, h, f["title"])
        for x, p in zip(f["edges"], paths):
            lw = p["lw"]
            out += (f'<g class="edge-g" data-el="{e(edge_id(x))}"><path d="{p["d"]}" class="edge" marker-end="url(#{sid}a)"/>'
                    f'<rect class="lab" x="{p["lx"] - lw / 2:.1f}" y="{p["ly"] - 10:.1f}" width="{lw:.1f}" height="20" rx="3"/>'
                    f'<text x="{p["lx"]:.1f}" y="{p["ly"] + 4:.1f}" text-anchor="middle">{self.tspan_fill(x["label"])}</text></g>')
        for n in f["nodes"]:
            x, y, nw = pos[n["id"]]
            out += f'<g class="node" data-el="{e(n["id"])}"><rect x="{x:.1f}" y="{y:.1f}" width="{nw:.1f}" height="36" rx="4"/><text x="{x + nw / 2:.1f}" y="{y + 23:.1f}" text-anchor="middle">{self.tspan_fill(n["label"])}</text></g>'
        return out + "</svg></div>"

    def stage_sequence(self, f):
        wide = lambda t: PLACEHOLDER.sub("000,000", t)
        col = max(120, max(text_w(a["label"]) + 32 for a in f["nodes"]))
        gap = max(col, max(text_w(wide(m["label"])) * 12.5 / 14 + 40 for m in f["edges"]))
        xs = {a["id"]: 16 + col / 2 + i * gap for i, a in enumerate(f["nodes"])}
        w = round(32 + col + gap * (len(f["nodes"]) - 1))
        row = 46
        h = row * len(f["edges"]) + 16
        minw = f'style="--minw:{min(w, round(w * 0.85))}px"'
        sid = self.uid("g")
        head = f'<svg class="seq-head" viewBox="0 0 {w} 40" width="{w}" {minw} aria-hidden="true">'
        body = (f'<svg viewBox="0 0 {w} {h}" width="{w}" {minw} role="img" aria-labelledby="{sid}t" preserveAspectRatio="xMidYMin meet"><title id="{sid}t">{e(f["title"])}</title>'
                f'<defs><marker id="{sid}a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="arrow"/></marker></defs>')
        for a in f["nodes"]:
            x = xs[a["id"]]
            aw = text_w(a["label"]) + 24
            head += f'<g class="node" data-el="{e(a["id"])}"><rect x="{x - aw / 2:.1f}" y="4" width="{aw:.1f}" height="32" rx="4"/><text x="{x:.1f}" y="25" text-anchor="middle">{self.tspan_fill(a["label"])}</text></g>'
            body += f'<g class="node" data-el="{e(a["id"])}"><line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{h - 6}" class="life"/></g>'
        for i, m in enumerate(f["edges"]):
            y = row * i + 30
            x1, x2 = xs[m["from"]], xs[m["to"]]
            d = 1 if x2 > x1 else -1
            body += (f'<g class="edge-g" data-el="{e(edge_id(m))}"><line x1="{x1 + 3 * d:.1f}" y1="{y}" x2="{x2 - 3 * d:.1f}" y2="{y}" class="edge" marker-end="url(#{sid}a)"/>'
                     f'<text x="{(x1 + x2) / 2:.1f}" y="{y - 7}" text-anchor="middle">{i + 1}. {self.tspan_fill(m["label"])}</text></g>')
        return f'<div class="svg-wrap seq">{head}</svg>{body}</svg></div>'

    # ---- 영역 ----
    def story(self, st):
        out = '<div class="story" data-story>'
        out += f'<div class="stage"><figure class="fig"><figcaption>{e(st["figure"]["title"])}</figcaption>{self.stage(st["figure"])}</figure></div>'
        v = st.get("vars")
        if v:
            names = {i["id"] for i in v["inputs"]}
            spec = []
            for o in v["outputs"]:
                spec.append([o["id"], int(o.get("digits", 0)), compile_expr(o["expr"], names)])
                names.add(o["id"])
            out += f'<div data-vars="{e(json.dumps(spec))}" hidden></div>'
        out += '<ol class="steps">'
        inputs = {i["id"]: i for i in (v or {}).get("inputs", [])}
        for k, step in enumerate(st["steps"]):
            out += f'<li class="step" data-step="{k}" data-show="{e(json.dumps(step["show"]))}"><h3>{e(step["title"])}</h3>'
            out += "".join(f"<p>{self.fill(t)}</p>" for t in step["body"])
            for c in step.get("controls", []):
                i, iid = inputs[c], self.uid("in")
                out += (f'<label class="knob" for="{iid}"><span class="knob-label">{e(i["label"])}</span>'
                        f'<input type="range" id="{iid}" data-in="{e(c)}" min="{i["min"]}" max="{i["max"]}" step="{i["step"]}" value="{i["value"]}">'
                        f'<output for="{iid}">{self.value_span(c)}</output><span class="unit">{e(i["unit"])}</span></label>')
            for n in step.get("notes", []):
                names = set(self.env)
                rpn = compile_expr(n["when"], names)
                from expr import evaluate
                on = evaluate(rpn, self.env)
                out += f'<p class="note" data-when="{e(json.dumps(rpn))}"{"" if on else " hidden"}>{self.fill(n["text"])}</p>'
            out += "</li>"
        out += "</ol>"
        if v:
            out += f'<p class="assume">{e(v["assumption"])}</p>'
        return out + "</div>"

    def relations(self, r):
        out = ""
        for m in r["models"]:
            out += (f'<article class="model"><h3>{e(m["name"])}</h3><p><strong>{e(m["claim"])}</strong> {e(m["cause"])}</p>'
                    f'<p>{e(" ".join(m["explains"]))}</p><p class="boundary">{e(m["boundary"])}</p></article>')
        return out

    def application(self, a):
        out = ""
        for j in a.get("judgments", []):
            out += f'<div class="judge"><p class="sit">{e(j["situation"])}</p><p class="res">{e(j["result"])}</p><p class="why">{e(j["reason"])}</p></div>'
        if a.get("switch"):
            out += self.switch(a["switch"])
        lim = a.get("limits", [])
        for kind, name in LIMIT_KINDS:
            xs = [x for x in lim if x["kind"] == kind]
            if xs:
                out += f'<div class="limits"><h3>{name}</h3><ul>' + "".join(f"<li>{e(x['text'])}</li>" for x in xs) + "</ul></div>"
        return out

    def switch(self, w):
        name = self.uid("sw")
        out = f'<div class="switch"><p class="q" id="{name}q">{e(w["question"])}</p><div class="choices" role="radiogroup" aria-labelledby="{name}q">'
        for k, o in enumerate(w["options"]):
            out += f'<label class="choice"><input type="radio" name="{name}" value="{k}" data-switch="{name}"{" checked" if k == 0 else ""}><span>{e(o["label"])}</span></label>'
        out += f'</div><div class="outcome" aria-live="polite" data-outcome="{name}">'
        for k, o in enumerate(w["options"]):
            out += f'<div data-option="{k}"{"" if k == 0 else " hidden"}><p class="res">{e(o["result"])}</p><p class="why">{e(o["reason"])}</p></div>'
        return out + "</div></div>"

    def html(self):
        tpl = open(os.path.join(ASSETS, "template.html"), encoding="utf-8").read()
        css = open(os.path.join(ASSETS, "styles.css"), encoding="utf-8").read()
        js = open(os.path.join(ASSETS, "interactions.js"), encoding="utf-8").read()
        digest = base64.b64encode(hashlib.sha256(("\n" + js + "\n").encode("utf-8")).digest()).decode()
        head = f'<p class="thesis">{e(self.d["thesis"])}</p>'
        body = ""
        for key, num, name in SECTIONS:
            if self.d.get(key):
                body += (f'<section class="sec" id="{key}" aria-labelledby="{key}-h"><h2 id="{key}-h"><span class="num">{num}</span>{name}</h2>'
                         f'{getattr(self, key)(self.d[key])}</section>')
        tpl = tpl.replace("__STYLES__", css).replace("__CSP_HASH__", digest)
        top, tail = tpl.split("__SCRIPT__")
        for k, v in {"__TITLE__": e(self.d["title"]), "__HEAD__": head, "__SECTIONS__": body}.items():
            top = top.replace(k, v)
        return top + js + tail


def render(data):
    return Page(data).html()


def main(argv):
    if len(argv) != 2:
        sys.exit("쓰는 법: render.py <설명.json> <출력.html>")
    data = json.load(open(argv[0], encoding="utf-8"))
    errors, warns = validate(data)
    for w in warns:
        print("경고", w)
    if errors:
        for x in errors:
            print("오류", x)
        return 1
    open(argv[1], "w", encoding="utf-8").write(render(data))
    print("썼다", argv[1])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
