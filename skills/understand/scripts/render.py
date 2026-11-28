"""UNDERSTAND 설명 JSON 을 고정 디자인의 HTML 한 장으로 만든다.

쓰는 법: render.py <설명.json> <출력.html>
검사(validate.py)를 먼저 돌리고 오류가 있으면 쓰지 않는다.
모든 글은 이스케이프해 넣는다. sources·src 는 화면에 내보내지 않는다.
페이지의 스크립트는 템플릿의 것 하나뿐이고 CSP 해시로 묶는다. 시뮬레이터 식은 미리 RPN 으로 옮겨 넣는다.
"""
import base64, hashlib, html, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate import validate  # noqa: E402
from expr import compile_expr, run_sim, fmt  # noqa: E402
from layout import layout, text_w  # noqa: E402

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
SECTIONS = [("structure", "01", "전체 구조"), ("mechanism", "02", "작동 원리"), ("relations", "03", "핵심 관계"),
            ("application", "04", "적용과 한계"), ("principles", "05", "재사용할 원리")]
LIMIT_KINDS = [("condition", "성립 조건"), ("counterexample", "반례"), ("tradeoff", "트레이드오프"),
               ("assumption", "확인되지 않은 전제"), ("unknown", "아직 모르는 것")]

e = lambda s: html.escape(str(s), quote=True)
paras = lambda xs: "".join(f"<p>{e(x)}</p>" for x in xs)


class Page:
    def __init__(self, data):
        self.d = data
        self.n = 0

    def uid(self, p):
        self.n += 1
        return f"{p}{self.n}"

    # ---- 그림 ----
    def figure(self, f):
        body = getattr(self, "fig_" + f["type"])(f)
        return f'<figure class="fig fig-{f["type"]}"><figcaption>{e(f["title"])}</figcaption>{body}</figure>'

    def svg_open(self, w, h, title):
        sid = self.uid("g")
        return sid, (f'<div class="svg-wrap"><svg viewBox="0 0 {w} {h}" width="{w}" style="min-width:{min(w, round(w * 0.85))}px" '
                     f'role="img" aria-labelledby="{sid}t" preserveAspectRatio="xMidYMin meet"><title id="{sid}t">{e(title)}</title>'
                     f'<defs><marker id="{sid}a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="arrow"/></marker></defs>')

    def fig_graph(self, f):
        pos, w, h, paths = layout(f["nodes"], f["edges"])
        sid, out = self.svg_open(w, h, f["title"])
        for p in paths:
            out += f'<path d="{p["d"]}" class="edge" marker-end="url(#{sid}a)"/>'
        for p in paths:
            lw = p["lw"]
            out += f'<g class="edge-label"><rect x="{p["lx"] - lw / 2:.1f}" y="{p["ly"] - 10:.1f}" width="{lw:.1f}" height="20" rx="3"/><text x="{p["lx"]:.1f}" y="{p["ly"] + 4:.1f}" text-anchor="middle">{e(p["label"])}</text></g>'
        for n in f["nodes"]:
            x, y, nw = pos[n["id"]]
            out += f'<g class="node"><rect x="{x:.1f}" y="{y:.1f}" width="{nw:.1f}" height="36" rx="4"/><text x="{x + nw / 2:.1f}" y="{y + 23:.1f}" text-anchor="middle">{e(n["label"])}</text></g>'
        rels = "".join(f'<li>{e(self.label_of(f, x["from"]))} → {e(self.label_of(f, x["to"]))}: {e(x["label"])}</li>' for x in f["edges"])
        return out + f'</svg></div><ul class="sr">{rels}</ul>'

    @staticmethod
    def label_of(f, i):
        return next(n["label"] for n in f["nodes"] if n["id"] == i)

    def fig_sequence(self, f):
        col = max(120, max(text_w(a["label"]) + 32 for a in f["actors"]))
        gap = max(col, max(text_w(m["label"]) * 12 / 14 + 40 for m in f["messages"]) / 1)
        xs = {a["id"]: 16 + col / 2 + i * gap for i, a in enumerate(f["actors"])}
        w = round(32 + col + gap * (len(f["actors"]) - 1))
        top, row = 52, 46
        h = top + row * len(f["messages"]) + 16
        sid, out = self.svg_open(w, h, f["title"])
        for a in f["actors"]:
            x = xs[a["id"]]
            aw = text_w(a["label"]) + 24
            out += f'<line x1="{x:.1f}" y1="36" x2="{x:.1f}" y2="{h - 6}" class="life"/>'
            out += f'<g class="node"><rect x="{x - aw / 2:.1f}" y="4" width="{aw:.1f}" height="32" rx="4"/><text x="{x:.1f}" y="25" text-anchor="middle">{e(a["label"])}</text></g>'
        for i, m in enumerate(f["messages"]):
            y = top + row * i + 24
            x1, x2 = xs[m["from"]], xs[m["to"]]
            d = 1 if x2 > x1 else -1
            out += f'<line x1="{x1 + 3 * d:.1f}" y1="{y}" x2="{x2 - 3 * d:.1f}" y2="{y}" class="edge" marker-end="url(#{sid}a)"/>'
            out += f'<text x="{(x1 + x2) / 2:.1f}" y="{y - 7}" text-anchor="middle" class="msg">{i + 1}. {e(m["label"])}</text>'
        steps = "".join(f'<li>{e(next(a["label"] for a in f["actors"] if a["id"] == m["from"]))} → {e(next(a["label"] for a in f["actors"] if a["id"] == m["to"]))}: {e(m["label"])}</li>' for m in f["messages"])
        return out + f'</svg></div><ol class="sr">{steps}</ol>'

    def fig_bars(self, f):
        top = max(i["value"] for i in f["items"]) or 1
        out = '<div class="bars">'
        for i in f["items"]:
            pct = i["value"] / top * 100
            v = fmt(i["value"], 0 if float(i["value"]).is_integer() else 1)
            out += f'<div class="bar-row"><span class="bar-label">{e(i["label"])}</span><span class="bar-track"><span class="bar" style="width:{pct:.1f}%"></span></span><span class="bar-val">{e(v)}{e(f["unit"])}</span></div>'
        return out + f'</div><p class="basis">{e(f["basis"])}</p>'

    def fig_table(self, f):
        basis = f'<p class="basis">{e(f["basis"])}</p>' if f.get("basis") else ""
        out = f'{basis}<div class="table-wrap" tabindex="0"><table><thead><tr><th scope="col"></th>' + "".join(f'<th scope="col">{e(c)}</th>' for c in f["columns"]) + "</tr></thead><tbody>"
        for r in f["rows"]:
            out += f'<tr><th scope="row">{e(r["label"])}</th>' + "".join(f"<td>{e(c)}</td>" for c in r["cells"]) + "</tr>"
        return out + "</tbody></table></div>"

    # ---- 영역 ----
    def structure(self, s):
        return paras(s.get("text", [])) + self.figure(s["figure"])

    def mechanism(self, m):
        out = ""
        if m.get("case"):
            out += f'<div class="case"><p class="k">대표 사례</p><h3>{e(m["case"]["title"])}</h3>{paras(m["case"]["body"])}</div>'
        out += '<ol class="chain">'
        for s in m["steps"]:
            out += f'<li><h3>{e(s["title"])}</h3>{paras(s["body"])}</li>'
        out += "</ol>"
        if m.get("figure"):
            out += self.figure(m["figure"])
        return out

    def relations(self, r):
        out = ""
        for m in r["models"]:
            out += (f'<article class="model"><h3>{e(m["name"])}</h3><p class="claim">{e(m["claim"])}</p>'
                    f'<p><span class="k">작동</span>{e(m["cause"])}</p><p class="k">이 모델로 설명되는 현상</p><ul>'
                    + "".join(f"<li>{e(x)}</li>" for x in m["explains"])
                    + f'</ul><p class="boundary"><span class="k">설명하지 못하는 것</span>{e(m["boundary"])}</p></article>')
        if r.get("figure"):
            out += self.figure(r["figure"])
        return out

    def application(self, a):
        out = ""
        for j in a.get("judgments", []):
            out += f'<div class="judge"><p class="sit">{e(j["situation"])}</p><p class="res">{e(j["result"])}</p><p class="why">{e(j["reason"])}</p></div>'
        if a.get("sim"):
            out += self.sim(a["sim"])
        if a.get("switch"):
            out += self.switch(a["switch"])
        lim = a.get("limits", [])
        for kind, name in LIMIT_KINDS:
            xs = [x for x in lim if x["kind"] == kind]
            if xs:
                out += f'<div class="limits"><h3>{name}</h3><ul>' + "".join(f"<li>{e(x['text'])}</li>" for x in xs) + "</ul></div>"
        return out

    def sim(self, s):
        names = {i["id"] for i in s["inputs"]}
        outs, notes = run_sim(s)
        out = f'<div class="sim" data-sim><h3>{e(s["title"])}</h3><p class="assume">{e(s["assumption"])}</p><div class="sim-in">'
        for i in s["inputs"]:
            iid = self.uid("in")
            out += (f'<label class="knob" for="{iid}"><span class="knob-label">{e(i["label"])}</span>'
                    f'<input type="range" id="{iid}" data-in="{e(i["id"])}" min="{i["min"]}" max="{i["max"]}" step="{i["step"]}" value="{i["value"]}">'
                    f'<output data-show="{e(i["id"])}" for="{iid}">{e(fmt(i["value"], 0 if float(i["step"]).is_integer() else 2))}</output><span class="unit">{e(i["unit"])}</span></label>')
        out += '</div><dl class="sim-out" aria-live="polite">'
        for o in s["outputs"]:
            rpn = compile_expr(o["expr"], names)
            names.add(o["id"])
            dg = int(o.get("digits", 0))
            out += f'<div><dt>{e(o["label"])}</dt><dd><span data-out="{e(o["id"])}" data-digits="{dg}" data-rpn="{e(json.dumps(rpn))}">{e(fmt(outs[o["id"]], dg))}</span> {e(o["unit"])}</dd></div>'
        out += "</dl>"
        if s.get("share"):
            parts = s["share"]["parts"]
            total = sum(max(0, outs[p]) for p in parts) or 1
            label = {o["id"]: o["label"] for o in s["outputs"]}
            out += '<div class="share" aria-hidden="true">' + "".join(
                f'<span class="seg s{k}" data-part="{e(p)}" style="width:{max(0, outs[p]) / total * 100:.1f}%"></span>' for k, p in enumerate(parts)) + "</div>"
            out += '<ul class="legend">' + "".join(f'<li><span class="sw s{k}"></span>{e(label[p])}</li>' for k, p in enumerate(parts)) + "</ul>"
        for n in s.get("notes", []):
            rpn = compile_expr(n["when"], names)
            out += f'<p class="note" data-when="{e(json.dumps(rpn))}"{"" if n["text"] in notes else " hidden"}>{e(n["text"])}</p>'
        return out + "</div>"

    def switch(self, w):
        name = self.uid("sw")
        out = f'<div class="switch"><p class="q" id="{name}q">{e(w["question"])}</p><div class="choices" role="radiogroup" aria-labelledby="{name}q">'
        for k, o in enumerate(w["options"]):
            out += f'<label class="choice"><input type="radio" name="{name}" value="{k}" data-switch="{name}"{" checked" if k == 0 else ""}><span>{e(o["label"])}</span></label>'
        out += f'</div><div class="outcome" aria-live="polite" data-outcome="{name}">'
        for k, o in enumerate(w["options"]):
            out += f'<div data-option="{k}"{"" if k == 0 else " hidden"}><p class="res">{e(o["result"])}</p><p class="why">{e(o["reason"])}</p></div>'
        return out + "</div></div>"

    def principles(self, ps):
        out = ""
        for p in ps:
            out += (f'<article class="principle"><h3>{e(p["name"])}</h3><p>{e(p["how"])}</p>'
                    f'<p><span class="k">적용 조건</span>{e(p["when"])}</p><ul class="cases">'
                    + "".join(f'<li><span class="field">{e(x["field"])}</span>{e(x["text"])}</li>' for x in p["examples"]) + "</ul></article>")
        return out

    def html(self):
        tpl = open(os.path.join(ASSETS, "template.html"), encoding="utf-8").read()
        css = open(os.path.join(ASSETS, "styles.css"), encoding="utf-8").read()
        js = open(os.path.join(ASSETS, "interactions.js"), encoding="utf-8").read()
        digest = base64.b64encode(hashlib.sha256(("\n" + js + "\n").encode("utf-8")).digest()).decode()
        head = f'<p class="thesis">{e(self.d["thesis"])}</p>' + "".join(f'<p class="primer">{e(x)}</p>' for x in self.d.get("primer", []))
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
