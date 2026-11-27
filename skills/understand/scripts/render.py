"""UNDERSTAND 분석 JSON 을 고정 템플릿에 넣어 단일 HTML 파일을 만든다.

쓰는 법: render.py <분석.json> <출력.html>
검사(validate.py)를 먼저 돌리고, 오류가 있으면 쓰지 않는다.
모든 글은 서버 쪽에서 이스케이프해 HTML 로 넣는다. 페이지에는 데이터 JSON 도, eval 도 없다.
스크립트는 CSP 해시로 묶어 템플릿의 스크립트 하나만 돈다.
"""
import base64, hashlib, html, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate import validate  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")

SECTIONS = [("s1", "01", "본질"), ("s2", "02", "전체 구조"), ("s3", "03", "작동 원리"), ("s4", "04", "조건과 한계"), ("s5", "05", "기억할 원리")]
DEFAULT_DEPTH = {"essence": "overview", "structure": "overview", "structure-l3": "standard", "mechanism": "standard", "limits": "standard", "principles": "overview", "checks": "overview"}
STATUS = {"inference": "추론", "assumption": "가정", "example": "예시", "unknown": "미확인"}
LIMIT_KINDS = [("condition", "성립 조건"), ("premise", "핵심 전제"), ("change", "조건이 바뀌면"), ("counterexample", "반례"), ("exception", "예외"), ("tradeoff", "트레이드오프"), ("boundary", "적용 한계"), ("unknown", "확인되지 않은 것")]

e = lambda s: html.escape(str(s), quote=True)


def t_has_own_marks(b):
    return b["type"] in ("diagram", "compare", "steps")


class Page:
    def __init__(self, data):
        self.data = data
        self.src_no = {s["id"]: i + 1 for i, s in enumerate(data["sources"])}
        self.uid = 0

    def next_id(self, prefix):
        self.uid += 1
        return f"{prefix}-{self.uid}"

    def depth(self, obj, section):
        d = obj.get("depth") or DEFAULT_DEPTH[section]
        return "" if d == "overview" else f' data-depth="{d}"'

    def marks(self, obj):
        out = ""
        st = obj.get("status")
        if st in STATUS:
            out += f' <span class="tag tag-{st}">{STATUS[st]}</span>'
        for r in obj.get("sources", []):
            n = self.src_no[r]
            out += f'<sup class="ref"><a href="#src-{e(r)}" aria-label="출처 {n}">{n}</a></sup>'
        return out

    def essence(self):
        es = self.data["essence"]
        out = f'<p class="lead">{e(es["definition"])}{self.marks(es)}</p>'
        for s in es.get("support", []):
            out += f"<p>{e(s)}</p>"
        return out

    def structure(self):
        st = self.data["structure"]
        nodes = st["nodes"]
        top = next(n for n in nodes if n["level"] == 1)
        l2 = [n for n in nodes if n["level"] == 2]
        kids = lambda p: [n for n in nodes if n.get("parent") == p["id"]]
        out = '<div class="ladder">'
        out += f'<div class="rung rung-1"><span class="rung-name">L1</span><div><strong>{e(top["label"])}</strong>{self.marks(top)}<p>{e(top["summary"])}</p></div></div>'
        rel = f'<span class="rel">{e(st["relation"])}</span>' if st.get("relation") else ""
        out += f'<div class="rung rung-2"><span class="rung-name">L2</span><div>{rel}<div class="picks" role="group" aria-label="주요 구조">'
        for n in l2:
            out += f'<button type="button" class="pick" data-pick="{e(n["id"])}" aria-expanded="false" aria-controls="panel-{e(n["id"])}"{self.depth(n, "structure")}><span class="pick-label">{e(n["label"])}</span><span class="pick-sum">{e(n["summary"])}</span></button>'
        out += "</div>"
        if st.get("edges"):
            out += self.svg([{"id": n["id"], "label": n["label"], "depth": n.get("depth")} for n in l2], st["edges"], "structure")
        for n in l2:
            out += f'<div class="panel" id="panel-{e(n["id"])}" data-panel="{e(n["id"])}" hidden><p class="panel-title">{e(n["label"])}{self.marks(n)}</p>'
            for d in n.get("detail", []):
                out += f"<p>{e(d)}</p>"
            ch = kids(n)
            if ch:
                out += '<ul class="l3">'
                for c in ch:
                    out += f'<li{self.depth(c, "structure-l3")}><span class="rung-name">L3</span><div><strong>{e(c["label"])}</strong>{self.marks(c)} <span>{e(c["summary"])}</span>'
                    if c.get("detail"):
                        out += '<details class="more-detail"><summary>자세히</summary>' + "".join(f"<p>{e(d)}</p>" for d in c["detail"]) + "</details>"
                    out += "</div></li>"
                out += "</ul>"
            out += "</div>"
        out += "</div></div></div>"
        return out

    def svg(self, nodes, edges, section):
        from layout import layout
        pos, w, h, paths = layout(nodes, edges)
        sid = self.next_id("dg")
        out = f'<figure class="diagram"><svg viewBox="0 0 {w} {h}" width="{w}" style="min-width:{min(w, round(w * 0.8))}px" role="img" aria-labelledby="{sid}-t" preserveAspectRatio="xMidYMin meet"><title id="{sid}-t">{e(" · ".join(n["label"] for n in nodes))} 관계도</title>'
        out += '<defs><marker id="%s-a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="arrow"/></marker></defs>' % sid
        for p in paths:
            out += f'<path d="{p["d"]}" class="edge" marker-end="url(#{sid}-a)"/>'
        for p in paths:
            lw = p["lw"]
            out += f'<g class="edge-label"><rect x="{p["lx"] - lw / 2:.1f}" y="{p["ly"] - 10:.1f}" width="{lw:.1f}" height="20" rx="3"/><text x="{p["lx"]:.1f}" y="{p["ly"] + 4:.1f}" text-anchor="middle">{e(p["label"])}</text></g>'
        for n in nodes:
            x, y, nw = pos[n["id"]]
            out += f'<g class="node" tabindex="0" role="button" data-pick="{e(n["id"])}" aria-label="{e(n["label"])}"><rect x="{x:.1f}" y="{y:.1f}" width="{nw:.1f}" height="36" rx="4"/><text x="{x + nw / 2:.1f}" y="{y + 23:.1f}" text-anchor="middle">{e(n["label"])}</text></g>'
        out += "</svg></figure>"
        return out

    def block(self, b):
        attrs = self.depth(b, "mechanism")
        head = t_has_own_marks(b)
        title = f'<h3>{e(b["title"])}{self.marks({"sources": b.get("sources", [])}) if head else ""}</h3>' if b.get("title") else ""
        if head:
            b = {**b, "sources": []}
        t = b["type"]
        if t == "text":
            return f'<div class="block"{attrs}>{title}' + "".join(f"<p>{e(s)}</p>" for s in b["body"][:-1]) + f'<p>{e(b["body"][-1])}{self.marks(b)}</p></div>'
        if t == "steps":
            out = f'<div class="block"{attrs}>{title}<ol class="steps">'
            for s in b["steps"]:
                out += f'<li><strong>{e(s["label"])}</strong>{self.marks(s)}<span>{e(s["body"])}</span></li>'
            return out + f"</ol>{self.marks(b)}</div>"
        if t == "diagram":
            out = f'<div class="block"{attrs}>{title}' + self.svg(b["nodes"], b["edges"], "mechanism")
            for n in b["nodes"]:
                out += f'<div class="panel" data-panel="{e(n["id"])}" hidden><p class="panel-title">{e(n["label"])}{self.marks(n)}</p><p>{e(n["detail"])}</p></div>'
            return out + "</div>"
        if t == "compare":
            basis = f'<p class="basis">비교 기준: {e(b["basis"])}</p>' if b.get("basis") else ""
            out = f'<div class="block"{attrs}>{title}{basis}<div class="table-wrap" tabindex="0"><table><thead><tr><th scope="col"></th>'
            out += "".join(f'<th scope="col">{e(c)}</th>' for c in b["columns"]) + "</tr></thead><tbody>"
            for r in b["rows"]:
                out += f'<tr><th scope="row">{e(r["label"])}{self.marks(r)}</th>' + "".join(f"<td>{e(c)}</td>" for c in r["cells"]) + "</tr>"
            return out + f"</tbody></table></div>{self.marks(b)}</div>"
        if t == "example":
            tag = '<span class="tag tag-real">실제 사례</span>' if b.get("real") else '<span class="tag tag-example">지어낸 예시</span>'
            return f'<div class="block example"{attrs}><h3>{e(b["title"])} {tag}</h3>' + "".join(f"<p>{e(s)}</p>" for s in b["body"]) + f"{self.marks(b)}</div>"
        raise ValueError(t)

    def mechanism(self):
        return "".join(self.block(b) for b in self.data["mechanism"]["blocks"])

    def limits(self):
        lim = self.data["limits"]
        out = ""
        for kind, name in LIMIT_KINDS:
            items = [x for x in lim["items"] if x["kind"] == kind]
            if not items:
                continue
            shallow = min((x.get("depth") or DEFAULT_DEPTH["limits"] for x in items), key=["overview", "standard", "deep"].index)
            out += f'<div class="limit-group" data-kind="{kind}"{self.depth({"depth": shallow}, "limits")}><h3>{name}</h3><ul>'
            out += "".join(f'<li{self.depth(x, "limits")}>{e(x["text"])}{self.marks(x)}</li>' for x in items)
            out += "</ul></div>"
        sc = lim.get("scenario")
        if sc:
            name = self.next_id("sc")
            out += f'<fieldset class="scenario"{self.depth(sc, "limits")}><legend>{e(sc["question"])}</legend><div class="choices">'
            for i, o in enumerate(sc["options"]):
                out += f'<label class="choice"><input type="radio" name="{name}" value="{i}" data-scenario="{name}"><span>{e(o["label"])}</span></label>'
            out += f'</div><div class="outcome" aria-live="polite" data-outcome="{name}"><p class="hint">조건을 고르면 결과와 이유가 보인다.</p>'
            for i, o in enumerate(sc["options"]):
                out += f'<div data-option="{i}" hidden><p><strong>결과</strong> {e(o["result"])}{self.marks(o)}</p><p><strong>이유</strong> {e(o["reason"])}</p></div>'
            out += "</div></fieldset>"
        return out

    def principles(self):
        pr = self.data["principles"]
        out = "" if pr["kind"] == "principle" else '<p class="basis">다른 상황에 옮겨 쓸 원리가 없다. 이번에 기억할 사실만 둔다.</p>'
        out += '<ol class="principles">'
        for p in pr["items"]:
            out += f'<li{self.depth(p, "principles")}><p class="statement">{e(p["statement"])}{self.marks(p)}</p>'
            if p.get("condition"):
                out += f'<p><span class="k">성립 조건</span> {e(p["condition"])}</p>'
            if p.get("example"):
                out += f'<p><span class="k">적용 예</span> {e(p["example"])}</p>'
            out += "</li>"
        out += "</ol>"
        out += '<details class="checks" data-reset-close><summary>이해 확인</summary><p class="basis">먼저 답을 떠올린 뒤 연다.</p>'
        for i, c in enumerate(self.data["checks"]):
            d = c.get("depth") or ("overview" if i == 0 else "deep")
            attrs = "" if d == "overview" else f' data-depth="{d}"'
            aid = self.next_id("ans")
            out += f'<div class="check"{attrs}><p class="q">{e(c["question"])}</p><button type="button" class="btn" data-answer="{aid}" aria-expanded="false" aria-controls="{aid}">답 보기</button><div class="answer" id="{aid}" hidden><p><strong>답</strong> {e(c["answer"])}</p>'
            out += "".join(f"<p>{e(x)}</p>" for x in c["explanation"]) + "</div></div>"
        return out + "</details>"

    def section(self, key, sid, num, name, body_fn):
        value = self.data[key] if key in self.data else None
        if isinstance(value, dict) and "na" in value:
            body = f'<details class="na" data-reset-close><summary>해당 없음</summary><p>{e(value["na"])}</p></details>'
        else:
            body = body_fn()
        return (f'<section class="sec" id="{sid}" data-level="overview" aria-labelledby="{sid}-h">'
                f'<div class="sec-head"><span class="sec-num">{num}</span><h2 id="{sid}-h">{name}</h2>'
                f'<button type="button" class="btn more" data-more hidden>더 보기</button>'
                f'<button type="button" class="btn fold" data-fold aria-expanded="true" aria-controls="{sid}-b" aria-label="{name} 접기">접기</button></div>'
                f'<div class="sec-body" id="{sid}-b">{body}<p class="hint empty-hint" hidden>이 깊이에서 보이는 항목이 없다. 더 보기를 누르면 이 섹션만 펼친다.</p></div></section>')

    def sources(self):
        if not self.data["sources"]:
            return '<p class="basis">따로 든 출처가 없다. 일반적으로 알려진 내용으로 설명했다.</p>'
        out = '<ol class="sources">'
        for s in self.data["sources"]:
            label = f'<a href="{e(s["url"])}" rel="noopener noreferrer">{e(s["label"])}</a>' if s.get("url") else e(s["label"])
            note = f' <span class="muted">{e(s["note"])}</span>' if s.get("note") else ""
            out += f'<li id="src-{e(s["id"])}">{label}{note}</li>'
        return out + "</ol>"

    def html(self):
        tpl = open(os.path.join(ASSETS, "template.html"), encoding="utf-8").read()
        css = open(os.path.join(ASSETS, "styles.css"), encoding="utf-8").read()
        js = open(os.path.join(ASSETS, "interactions.js"), encoding="utf-8").read()
        digest = base64.b64encode(hashlib.sha256(("\n" + js + "\n").encode("utf-8")).digest()).decode()
        tpl = tpl.replace("__STYLES__", css).replace("__CSP_HASH__", digest)
        head, tail = tpl.split("__SCRIPT__")
        parts = [("essence", self.essence), ("structure", self.structure), ("mechanism", self.mechanism), ("limits", self.limits), ("principles", self.principles)]
        body = "".join(self.section(k, *SECTIONS[i], fn) for i, (k, fn) in enumerate(parts))
        nav = "".join(f'<li><a href="#{sid}"><span class="sec-num">{num}</span>{name}</a></li>' for sid, num, name in SECTIONS)
        for k, v in {"__TITLE__": e(self.data["title"]), "__NAV__": nav, "__SECTIONS__": body, "__SOURCES__": self.sources()}.items():
            head = head.replace(k, v)
        return head + js + tail


def render(data):
    return Page(data).html()


def main(argv):
    if len(argv) != 2:
        sys.exit("쓰는 법: render.py <분석.json> <출력.html>")
    data = json.load(open(argv[0], encoding="utf-8"))
    errors, warns = validate(data)
    for w in warns:
        print("경고", w)
    if errors:
        for x in errors:
            print("오류", x)
        print("검사를 통과하지 못해 HTML 을 쓰지 않았다")
        return 1
    open(argv[1], "w", encoding="utf-8").write(render(data))
    print(f"썼다 {argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
