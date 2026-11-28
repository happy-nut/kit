"""UNDERSTAND 뼈대 JSON 을 고정 디자인의 HTML 한 장으로 만든다.

쓰는 법: render.py <뼈대.json> <출력.html>
검사(validate.py)를 먼저 돌리고 오류가 있으면 쓰지 않는다.
뼈대 그림은 한 장이고 화면 옆(휴대폰은 위)에 붙어 있다. 글 덩어리마다 그 덩어리를 읽을 때의 그림 상태
(보이는 부분, 보이는 연결, 짚는 것)를 data- 속성으로 달고, 스크립트는 읽는 자리의 덩어리 상태를 그림에 옮기기만 한다.
모든 글은 이스케이프해 넣는다. sources·src 는 화면에 내보내지 않는다.
"""
import base64, hashlib, html, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate import validate, build_states, path_links  # noqa: E402
from layout import layout, NODE_H  # noqa: E402

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
SECTIONS = [("bridge", "01", "출발점"), ("build", "02", "뼈대"), ("phenomena", "03", "설명되는 현상"),
            ("inferences", "04", "새로운 추론"), ("limits", "05", "적용 한계")]
LIMIT_KINDS = [("condition", "성립 조건"), ("counterexample", "반례"), ("tradeoff", "트레이드오프"),
               ("assumption", "확인되지 않은 전제"), ("unknown", "아직 모르는 것")]

e = lambda s: html.escape(str(s), quote=True)
paras = lambda xs: "".join(f"<p>{e(x)}</p>" for x in xs)
key = lambda l: f"{l['from']}>{l['to']}"


class Page:
    def __init__(self, data):
        self.d = data
        self.sk = data["skeleton"]
        self.names = {p["id"]: p["name"] for p in self.sk["parts"]}
        self.all_parts = [p["id"] for p in self.sk["parts"]]
        self.all_links = [key(l) for l in self.sk["links"]]
        self.n = 0

    def block(self, inner, show, links, focus, cls="blk", at=(), mode=""):
        self.n += 1
        attrs = (f' id="b{self.n}" data-show="{e(" ".join(show))}" data-links="{e(" ".join(links))}"'
                 f' data-focus="{e(" ".join(focus))}"')
        if at:
            attrs += f' data-at="{e(" ".join(at))}"'
        if mode:
            attrs += f' data-mode="{mode}"'
        return f'<div class="{cls}"{attrs}>{inner}</div>'

    def whole(self, inner, focus=(), cls="blk"):
        return self.block(inner, self.all_parts, self.all_links, focus, cls)

    def route(self, path):
        return '<p class="route">' + ' <span class="arr">→</span> '.join(e(self.names[i]) for i in path) + "</p>"

    def figure(self):
        known = (self.d.get("bridge") or {}).get("map", {})
        nodes = [{"id": i, "label": max(self.names[i], known.get(i, ""), key=len)} for i in self.all_parts]
        edges = [{"from": l["from"], "to": l["to"], "label": l["label"]} for l in self.sk["links"]]
        pos, w, h, paths = layout(nodes, edges)
        out = (f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid meet" role="img" aria-labelledby="skt" data-mon="mk-on" data-moff="mk">'
               f'<title id="skt">{e(self.d["title"])}의 뼈대</title><defs>'
               '<marker id="mk" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="arrow"/></marker>'
               '<marker id="mk-on" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="arrow-on"/></marker></defs>')
        # 선을 모두 그린 뒤 이름을 그려, 이름 바탕이 늘 그 아래 선을 가린다.
        for l, p in zip(self.sk["links"], paths):
            out += f'<g class="link" data-link="{e(key(l))}"><path d="{p["d"]}" class="edge" marker-end="url(#mk)"/></g>'
        for l, p in zip(self.sk["links"], paths):
            lw = p["lw"]
            out += (f'<g class="link name" data-link="{e(key(l))}"><rect class="lab" x="{p["lx"] - lw / 2:.1f}" y="{p["ly"] - 10:.1f}" width="{lw:.1f}" height="20" rx="3"/>'
                    f'<text x="{p["lx"]:.1f}" y="{p["ly"] + 4.5:.1f}" text-anchor="middle">{e(l["label"])}</text></g>')
        for i in self.all_parts:
            x, y, nw = pos[i]
            tx, ty = x + nw / 2, y + NODE_H / 2 + 5.5
            out += (f'<g class="node" data-part="{e(i)}"><rect x="{x:.1f}" y="{y:.1f}" width="{nw:.1f}" height="{NODE_H}" rx="6"/>'
                    f'<text class="nm" x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle">{e(self.names[i])}</text>'
                    f'<text class="kn" x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle">{e(known.get(i, self.names[i]))}</text></g>')
        rel = "".join(f'<li>{e(self.names[l["from"]])} → {e(self.names[l["to"]])}: {e(l["label"])}</li>' for l in self.sk["links"])
        return f'<figure class="stage" aria-label="뼈대 그림">{out}</svg><ul class="sr">{rel}</ul></figure>'

    # ---- 영역 ----
    def bridge(self, b):
        show = [i for i in self.all_parts if i in b["map"] or i in b["at"]]
        links = [key(l) for l in self.sk["links"] if l["from"] in show and l["to"] in show]
        pairs = "".join(f'<li><span class="mine">{e(self.names[i])}</span> <span class="arr">≈</span> {e(v)}</li>'
                        for i, v in b["map"].items())
        inner = (f'<p class="known">{e(b["known"])}</p><ul class="pairs">{pairs}</ul>'
                 f'<p class="k">결과를 바꾸는 차이</p><ul class="differs">' + "".join(f"<li>{e(x)}</li>" for x in b["differs"]) + "</ul>")
        return self.block(inner, show, links, [], "blk bridge", at=b["at"], mode="known")

    def build(self, steps):
        out = ""
        for k, (st, s) in enumerate(zip(steps, build_states(self.d))):
            inner = f'<h3><span class="n">{k + 1}</span>{e(st["title"])}</h3>{paras(st["body"])}'
            out += self.block(inner, s["show"], s["links"], s["focus"], "blk step")
        return out

    def phenomena(self, ps):
        return "".join(self.whole(f'<p>{e(p["text"])}</p>{self.route(p["path"])}', p["path"] + path_links(self.d, p["path"]), "blk phen") for p in ps)

    def inferences(self, xs):
        return "".join(self.whole(f'<p class="q">{e(x["question"])}</p><p class="res">{e(x["answer"])}</p><p class="why">{e(x["reason"])}</p>{self.route(x["path"])}',
                                  x["path"] + path_links(self.d, x["path"]), "blk infer") for x in xs)

    def limits(self, lim):
        out = ""
        for kind, name in LIMIT_KINDS:
            xs = [x for x in lim if x["kind"] == kind]
            if xs:
                out += f'<div class="limits"><h3>{name}</h3><ul>' + "".join(f"<li>{e(x['text'])}</li>" for x in xs) + "</ul></div>"
        return self.whole(out)

    def html(self):
        tpl = open(os.path.join(ASSETS, "template.html"), encoding="utf-8").read()
        css = open(os.path.join(ASSETS, "styles.css"), encoding="utf-8").read()
        js = open(os.path.join(ASSETS, "interactions.js"), encoding="utf-8").read()
        digest = base64.b64encode(hashlib.sha256(("\n" + js + "\n").encode("utf-8")).digest()).decode()
        body = ""
        for k, num, name in SECTIONS:
            if self.d.get(k):
                body += (f'<section class="sec" id="{k}" aria-labelledby="{k}-h"><h2 id="{k}-h"><span class="num">{num}</span>{name}</h2>'
                         f'{getattr(self, k)(self.d[k])}</section>')
        tpl = tpl.replace("__STYLES__", css).replace("__CSP_HASH__", digest)
        top, tail = tpl.split("__SCRIPT__")
        for k, v in {"__TITLE__": e(self.d["title"]), "__THESIS__": e(self.d["thesis"]),
                     "__FIGURE__": self.figure(), "__SECTIONS__": body}.items():
            top = top.replace(k, v)
        return top + js + tail


def render(data):
    return Page(data).html()


def main(argv):
    if len(argv) != 2:
        sys.exit("쓰는 법: render.py <뼈대.json> <출력.html>")
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
