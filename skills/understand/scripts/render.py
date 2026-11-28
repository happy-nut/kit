"""UNDERSTAND 정신 모델 JSON 을 고정 디자인의 HTML 한 장으로 만든다.

쓰는 법: render.py <모델.json> <출력.html>
검사(validate.py)를 먼저 돌리고 오류가 있으면 쓰지 않는다.
모든 글은 이스케이프해 넣는다. sources·src 는 화면에 내보내지 않는다.
페이지의 스크립트는 템플릿의 것 하나뿐이고 CSP 해시로 묶는다. 식은 미리 RPN 으로 옮겨 넣는다.
"""
import base64, hashlib, html, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate import validate  # noqa: E402
from expr import compile_expr, run_sim, fmt  # noqa: E402
from layout import layout  # noqa: E402

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
SECTIONS = [("start", "01", "출발점"), ("model", "02", "핵심 메커니즘"), ("phenomena", "03", "설명되는 현상"),
            ("inferences", "04", "새로운 추론"), ("limits", "05", "적용 한계")]
LIMIT_KINDS = [("condition", "성립 조건"), ("counterexample", "반례"), ("tradeoff", "트레이드오프"),
               ("assumption", "확인되지 않은 전제"), ("unknown", "아직 모르는 것")]

e = lambda s: html.escape(str(s), quote=True)
paras = lambda xs: "".join(f"<p>{e(x)}</p>" for x in xs)


def step_digits(step):
    return 0 if float(step).is_integer() else min(2, len(repr(float(step)).split(".")[1]))


class Page:
    def __init__(self, data):
        self.d = data
        self.n = 0
        c = data["model"]["calc"]
        outs, _ = run_sim(c)
        self.env = {i["id"]: float(i["value"]) for i in c["inputs"]}
        self.env.update(outs)
        self.meta = {i["id"]: (i["label"], i["unit"], step_digits(i["step"])) for i in c["inputs"]}
        self.meta.update({o["id"]: (o["label"], o["unit"], int(o.get("digits", 0))) for o in c["outputs"]})
        self.meta.update({k["id"]: (k["label"], "", 0) for k in data["model"].get("concepts", [])})

    def uid(self, p):
        self.n += 1
        return f"{p}{self.n}"

    def val(self, i, svg=False):
        label, unit, dg = self.meta[i]
        tag = "tspan" if svg else "span"
        return f'<{tag} class="val" data-out="{e(i)}">{e(fmt(self.env[i], dg))}</{tag}>{e(unit)}'

    def diagram(self, mm):
        ids = list(dict.fromkeys([x for l in mm["links"] for x in (l["from"], l["to"])]))
        wide = lambda i: f"{self.meta[i][0]} 000,000{self.meta[i][1]}" if i in self.env else self.meta[i][0]
        pos, w, h, paths = layout([{"id": i, "label": wide(i)} for i in ids],
                                  [{"from": l["from"], "to": l["to"], "label": f"{l['sign']} {l['label']}"} for l in mm["links"]])
        sid = self.uid("g")
        out = (f'<div class="svg-wrap"><svg viewBox="0 0 {w} {h}" width="{w}" style="--minw:{min(w, round(w * 0.85))}px" role="img" aria-labelledby="{sid}t">'
               f'<title id="{sid}t">{e(mm["name"])}: 변수 관계</title><defs>'
               f'<marker id="{sid}p" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="arrow-plus"/></marker>'
               f'<marker id="{sid}m" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="arrow-minus"/></marker></defs>')
        for l, p in zip(mm["links"], paths):
            kind = "plus" if l["sign"] == "+" else "minus"
            lw = p["lw"]
            out += (f'<g class="link {kind}"><path d="{p["d"]}" class="edge" marker-end="url(#{sid}{kind[0]})"/>'
                    f'<rect class="lab" x="{p["lx"] - lw / 2:.1f}" y="{p["ly"] - 10:.1f}" width="{lw:.1f}" height="20" rx="3"/>'
                    f'<text x="{p["lx"]:.1f}" y="{p["ly"] + 4:.1f}" text-anchor="middle"><tspan class="sign">{e(l["sign"])}</tspan> {e(l["label"])}</text></g>')
        for i in ids:
            x, y, nw = pos[i]
            inner = f'{e(self.meta[i][0])} {self.val(i, True)}' if i in self.env else e(self.meta[i][0])
            out += f'<g class="node{"" if i in self.env else " concept"}"><rect x="{x:.1f}" y="{y:.1f}" width="{nw:.1f}" height="36" rx="4"/><text x="{x + nw / 2:.1f}" y="{y + 23:.1f}" text-anchor="middle">{inner}</text></g>'
        rel = "".join(f'<li>{e(self.meta[l["from"]][0])} {"늘면" } {e(self.meta[l["to"]][0])} {"늘어난다" if l["sign"] == "+" else "줄어든다"}: {e(l["label"])}</li>' for l in mm["links"])
        return out + f'</svg></div><ul class="sr">{rel}</ul><p class="legend-line"><span class="sw plus"></span>함께 늘어난다 <span class="sw minus"></span>반대로 움직인다</p>'

    # ---- 영역 ----
    def start(self, _):
        if "bridge" in self.d:
            b = self.d["bridge"]
            return (f'<p class="known">{e(b["known"])}</p><div class="pair"><div><p class="k">그대로 통하는 것</p><ul>'
                    + "".join(f"<li>{e(x)}</li>" for x in b["same"]) + '</ul></div><div class="differs"><p class="k">결과를 바꾸는 차이</p><ul>'
                    + "".join(f"<li>{e(x)}</li>" for x in b["differs"]) + "</ul></div></div>")
        c = self.d["case"]
        return f'<div class="case"><h3>{e(c["title"])}</h3>{paras(c["body"])}</div>'

    def model(self, m):
        c = m["calc"]
        out = ""
        for mm in m["models"]:
            out += (f'<article class="model"><h3>{e(mm["name"])}</h3><p class="claim">{e(mm["claim"])}</p>'
                    f'<figure class="fig">{self.diagram(mm)}</figure><p class="boundary"><span class="k">이 모델이 설명하지 못하는 것</span>{e(mm["boundary"])}</p></article>')
        names = {i["id"] for i in c["inputs"]}
        spec = []
        for o in c["outputs"]:
            spec.append([o["id"], int(o.get("digits", 0)), compile_expr(o["expr"], names)])
            names.add(o["id"])
        out += f'<div class="lab-area"><div data-vars="{e(json.dumps(spec))}" hidden></div><div class="controls">'
        for i in c["inputs"]:
            iid = self.uid("in")
            out += (f'<label class="knob" for="{iid}"><span class="knob-label">{e(i["label"])}</span>'
                    f'<input type="range" id="{iid}" data-in="{e(i["id"])}" min="{i["min"]}" max="{i["max"]}" step="{i["step"]}" value="{i["value"]}">'
                    f'<output for="{iid}">{self.val(i["id"])}</output></label>')
        out += f'</div><p class="assume">{e(c["assumption"])}</p>'
        for p in m["plots"]:
            spec = {"x": p["x"], "xl": self.meta[p["x"]][0], "xu": self.meta[p["x"]][1],
                    "min": next(i["min"] for i in c["inputs"] if i["id"] == p["x"]), "max": next(i["max"] for i in c["inputs"] if i["id"] == p["x"]),
                    "ys": [[y, self.meta[y][0], self.meta[y][1], self.meta[y][2]] for y in p["ys"]],
                    "marks": [[compile_expr(mk["when"], names), mk["label"]] for mk in p.get("marks", [])]}
            out += (f'<figure class="fig plot"><figcaption>{e(p["title"])}</figcaption>'
                    f'<div class="plot-box" data-plot="{e(json.dumps(spec))}"></div>'
                    f'<p class="finding"><span class="k">그래프에서 읽히는 것</span>{e(p["finding"])}</p></figure>')
        return out + "</div>"

    def phenomena(self, ps):
        out = '<ul class="phen">'
        for p in ps:
            chips = "".join(f'<span class="chip">{e(self.meta[v][0])}</span>' for v in p["via"])
            out += f'<li><p>{e(p["text"])}</p><p class="via">{chips}</p></li>'
        return out + "</ul>"

    def inferences(self, xs):
        out = ""
        for x in xs:
            out += f'<div class="infer"><p class="q">{e(x["question"])}</p><p class="res">{e(x["answer"])}</p><p class="why">{e(x["reason"])}</p></div>'
        if self.d.get("switch"):
            out += self.switch(self.d["switch"])
        return out

    def limits(self, lim):
        out = ""
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
            value = True if key == "start" else self.d.get(key)
            if value:
                body += (f'<section class="sec" id="{key}" aria-labelledby="{key}-h"><h2 id="{key}-h"><span class="num">{num}</span>{name}</h2>'
                         f'{getattr(self, key)(self.d.get(key))}</section>')
        tpl = tpl.replace("__STYLES__", css).replace("__CSP_HASH__", digest)
        top, tail = tpl.split("__SCRIPT__")
        for k, v in {"__TITLE__": e(self.d["title"]), "__HEAD__": head, "__SECTIONS__": body}.items():
            top = top.replace(k, v)
        return top + js + tail


def render(data):
    return Page(data).html()


def main(argv):
    if len(argv) != 2:
        sys.exit("쓰는 법: render.py <모델.json> <출력.html>")
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
