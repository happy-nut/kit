"""UNDERSTAND 설명 JSON 을 검사한다.

스키마(references/output-schema.json)로 모양을 보고, 스키마로 못 잡는 규칙을 본다.
내부 분석·조작 안내 노출, 금지 표현, 반복, 깨진 참조, 관계도의 고립 마디, 시뮬레이터 식.
오류가 하나라도 있으면 종료 코드 1. 경고는 렌더를 막지 않는다.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.join(HERE, "..", "references", "output-schema.json")
sys.path.insert(0, HERE)

BANNED = [
    "축에서 만", "바로 그 갈래", "본질을 관통", "관통하는", "가능성을 열", "패러다임", "시너지", "누가 아픈지",
    "치르는 값", "보는 눈도 함께", "사슬의 맨 끝", "먹고산다", "핵심은 바로", "이 지점에서 중요한", "퍼즐", "여정",
    "흥미로운", "놀라운", "진정한 의미", "한 단계 더 나아가", "맞닿아", "게임 체인저", "살펴보겠", "알아보겠",
    "결론적으로", "요약하면", "한마디로", "다시 말해", "좋은 질문", "훌륭한", "물론입니다", "중요합니다",
    "주목할 만한", "눈여겨볼",
]
BANNED_RE = re.compile(r"단순(히|한)[^.]{0,30}(을|를) 넘어")
INTERNAL = [
    "소비재", "자본재", "도구형", "메타 정보", "메타형", "정보 가치", "장기적 가치", "선행성", "압축성", "생성성",
    "전이성", "지속성", "개인 적합성", "습득 비용", "정보 자산", "이해도", "이해 수준", "사고도구", "사고 도구",
    "분석 절차", "내부 판단", "MECE", "이슈 트리", "피라미드 원칙", "추상화 사다리",
]
UI_TALK = re.compile(r"눌러|클릭|탭하|펼쳐 보|접어 두|더 보기|다음 단계로 넘어|아래에서 고르|선택해 보|가장 구체적인 수준|갈래로 더|\bL[1-5]\b|모르면")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⭕️]")
SCORE = re.compile(r"\b\d+\s*(점|/\s*10|/\s*100)\b|신뢰도\s*\d")
SECTIONS = ["structure", "mechanism", "relations", "application", "principles"]


def load_schema():
    return json.load(open(SCHEMA, encoding="utf-8"))


def resolve(root, node):
    while "$ref" in node:
        node = root["$defs"][node["$ref"].split("/")[-1]]
    return node


def shape(root, node, value, path, out):
    node = resolve(root, node)
    if "oneOf" in node:
        best = None
        for branch in node["oneOf"]:
            errs = []
            shape(root, branch, value, path, errs)
            if not errs:
                return
            if best is None or len(errs) < len(best):
                best = errs
        out.extend(best)
        return
    if "const" in node and value != node["const"]:
        out.append(f"{path}: {node['const']!r} 이어야 한다")
        return
    if "enum" in node and value not in node["enum"]:
        out.append(f"{path}: {node['enum']} 중 하나여야 한다 ({value!r})")
        return
    t = node.get("type")
    kinds = {"object": dict, "array": list, "string": str, "boolean": bool, "number": (int, float)}
    if t and (not isinstance(value, kinds[t]) or (t == "number" and isinstance(value, bool))):
        out.append(f"{path}: {t} 여야 한다")
        return
    if isinstance(value, str):
        if len(value) < node.get("minLength", 0):
            out.append(f"{path}: 비었거나 너무 짧다")
        if len(value) > node.get("maxLength", 10**9):
            out.append(f"{path}: {node['maxLength']}자를 넘는다 ({len(value)}자). 나누거나 줄인다")
        if "pattern" in node and not re.search(node["pattern"], value):
            out.append(f"{path}: 형식 {node['pattern']} 에 맞지 않는다 ({value!r})")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value < node.get("minimum", -10**18) or value > node.get("maximum", 10**18):
            out.append(f"{path}: 범위를 벗어난다 ({value})")
    if isinstance(value, list):
        if len(value) < node.get("minItems", 0):
            out.append(f"{path}: 항목이 {node['minItems']}개 이상이어야 한다")
        if len(value) > node.get("maxItems", 10**9):
            out.append(f"{path}: 항목이 {node['maxItems']}개를 넘는다 ({len(value)}개)")
        for i, v in enumerate(value):
            shape(root, node.get("items", {}), v, f"{path}[{i}]", out)
    if isinstance(value, dict):
        for k in node.get("required", []):
            if k not in value:
                out.append(f"{path}: {k} 가 없다")
        props = node.get("properties", {})
        for k, v in value.items():
            if k in props:
                shape(root, props[k], v, f"{path}.{k}", out)
            elif node.get("additionalProperties") is False:
                out.append(f"{path}: 스키마에 없는 키 {k}")


def strings(value, path="$"):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from strings(v, f"{path}[{i}]")
    elif isinstance(value, dict):
        for k, v in value.items():
            if k not in ("id", "from", "to", "src", "url", "kind", "type", "schema", "expr", "when", "parts", "sources"):
                yield from strings(v, f"{path}.{k}")


def sentences(text):
    return [s for s in re.split(r"(?<=[.?!])\s+", text.strip()) if s]


def norm(text):
    return re.sub(r"[\s.,·「」'\"()]", "", text)


def check_figure(fig, path, errors):
    if fig["type"] == "graph":
        ids = [n["id"] for n in fig["nodes"]]
        if len(set(ids)) != len(ids):
            errors.append(f"{path}: 같은 id 의 마디가 둘")
        used = set()
        for e in fig["edges"]:
            for end in (e["from"], e["to"]):
                if end not in ids:
                    errors.append(f"{path}: 선이 없는 마디 {end} 를 가리킨다")
                used.add(end)
            if e["from"] == e["to"]:
                errors.append(f"{path}: 자기 자신으로 가는 선 ({e['from']})")
        for i in ids:
            if i not in used:
                errors.append(f"{path}: 마디 {i} 에 이어진 선이 없다. 관계가 없으면 그림에서 뺀다")
        if all(e["from"] in ids and e["to"] in ids for e in fig["edges"]):
            from layout import layout, overlap, NODE_H
            pos, _, _, paths = layout(fig["nodes"], fig["edges"])
            boxes = [(x, y, x + w, y + NODE_H) for x, y, w in pos.values()]
            rects = [(p["lx"] - p["lw"] / 2, p["ly"] - 10, p["lx"] + p["lw"] / 2, p["ly"] + 10) for p in paths]
            for k, r in enumerate(rects):
                if any(overlap(r, b, 0) for b in boxes) or any(overlap(r, q, 0) for q in rects[:k]):
                    errors.append(f"{path}: 선 이름 「{paths[k]['label']}」 이 마디나 다른 선 이름과 겹친다. 마디나 선을 줄인다")
    elif fig["type"] == "sequence":
        ids = [a["id"] for a in fig["actors"]]
        for m in fig["messages"]:
            if m["from"] not in ids or m["to"] not in ids:
                errors.append(f"{path}: 없는 참여자를 가리킨다 ({m['from']}→{m['to']})")
            if m["from"] == m["to"]:
                errors.append(f"{path}: 자기 자신에게 보내는 메시지 ({m['from']})")
    elif fig["type"] == "table":
        for r in fig["rows"]:
            if len(r["cells"]) != len(fig["columns"]):
                errors.append(f"{path}: 「{r['label']}」 칸 수가 열 수와 다르다")


def check_sim(sim, path, errors):
    from expr import compile_expr, run_sim, ExprError
    names = set()
    for i in sim["inputs"]:
        if not i["min"] <= i["value"] <= i["max"] or i["min"] >= i["max"]:
            errors.append(f"{path}.inputs {i['id']}: min < max 이고 value 는 그 안이어야 한다")
        names.add(i["id"])
    for o in sim["outputs"]:
        if o["id"] in names:
            errors.append(f"{path}.outputs {o['id']}: 이름이 겹친다")
        try:
            compile_expr(o["expr"], names)
        except ExprError as x:
            errors.append(f"{path}.outputs {o['id']}: 식 오류 ({x})")
            return
        names.add(o["id"])
    for n in sim.get("notes", []):
        try:
            compile_expr(n["when"], names)
        except ExprError as x:
            errors.append(f"{path}.notes: 식 오류 ({x})")
            return
    outs = {o["id"] for o in sim["outputs"]}
    for p in sim.get("share", {}).get("parts", []):
        if p not in outs:
            errors.append(f"{path}.share: 없는 출력 {p}")
    for corner in ("min", "value", "max"):
        vals = {i["id"]: float(i[corner]) for i in sim["inputs"]}
        res, _ = run_sim(sim, vals)
        bad = [k for k, v in res.items() if v != v or abs(v) == float("inf")]
        if bad:
            errors.append(f"{path}: 입력이 모두 {corner} 일 때 {bad} 를 계산할 수 없다")
        if sim.get("share") and any(res[p] < 0 for p in sim["share"]["parts"] if p in res):
            errors.append(f"{path}.share: 입력이 모두 {corner} 일 때 음수인 몫이 있다")


def semantics(data):
    errors, warns = [], []
    for path, text in strings(data):
        if path.startswith("$.sources"):
            continue
        for w in BANNED + ([BANNED_RE.search(text).group(0)] if BANNED_RE.search(text) else []):
            if w in text and w not in data["title"]:
                errors.append(f"{path}: 금지 표현 「{w}」. 사실·관계·원인·결과·조건을 바로 쓴다")
        for w in INTERNAL:
            if w in text and w not in data["title"]:
                errors.append(f"{path}: 내부 분석 낱말 「{w}」 이 화면에 나간다")
        m = UI_TALK.search(text)
        if m:
            errors.append(f"{path}: 화면 조작이나 계층을 말하는 글 「{m.group(0)}」. 대상만 설명한다")
        if EMOJI.search(text):
            errors.append(f"{path}: 이모지")
        if "—" in text:
            errors.append(f"{path}: 긴 대시(—). 문장을 나눈다")
        if SCORE.search(text):
            errors.append(f"{path}: 점수처럼 보인다. 근거 없는 점수는 쓰지 않는다")
        if len(text) > 110 and len(sentences(text)) == 1 and text.count(",") >= 3:
            warns.append(f"{path}: 쉼표가 많은 긴 한 문장. 명제 하나씩 나눈다")

    if len(sentences(data["thesis"])) > 1:
        errors.append("$.thesis: 핵심 명제는 한 문장이다")
    if not any(k in data for k in SECTIONS[:4]):
        errors.append("$: 01~04 중 적어도 한 영역은 있어야 한다")

    seen = {}
    for path, text in strings(data):
        if path.startswith("$.sources") or len(text) < 25:
            continue
        key = norm(text)
        if key in seen and seen[key] != path:
            errors.append(f"{path}: {seen[key]} 와 같은 문장이다. 되풀이하지 않는다")
        seen.setdefault(key, path)

    ids = [s["id"] for s in data["sources"]]
    if len(set(ids)) != len(ids):
        errors.append("$.sources: 같은 id 가 둘")
    used = set()

    def refs(obj, path):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "src":
                    for r in v:
                        used.add(r)
                        if r not in ids:
                            errors.append(f"{path}.src: 없는 출처 {r}")
                else:
                    refs(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                refs(v, f"{path}[{i}]")
    refs(data, "$")
    for s in ids:
        if s not in used:
            warns.append(f"$.sources: {s} 를 근거로 삼은 설명이 없다(src). 근거 추적이 끊긴다")

    for key in ("structure", "mechanism", "relations"):
        if key in data and "figure" in data[key]:
            check_figure(data[key]["figure"], f"$.{key}.figure", errors)
    app = data.get("application")
    if app is not None:
        if not any(app.get(k) for k in ("judgments", "sim", "switch", "limits")):
            errors.append("$.application: 비었다. 내용이 없으면 키를 뺀다")
        if "sim" in app:
            check_sim(app["sim"], "$.application.sim", errors)
    if "principles" in data and not data["principles"]:
        errors.append("$.principles: 비었다. 재사용할 원리가 없으면 키를 뺀다")
    for i, m in enumerate(data.get("relations", {}).get("models", [])):
        if m["name"] in m["claim"] and len(m["claim"]) < len(m["name"]) + 12:
            warns.append(f"$.relations.models[{i}]: 모델 이름만 되풀이한다. 이 대상에서 무엇을 설명하는지 쓴다")
    return errors, warns


def validate(data):
    errors = []
    shape(load_schema(), load_schema(), data, "$", errors)
    if errors:
        return errors, []
    e, w = semantics(data)
    return errors + e, w


def main(argv):
    if not argv:
        sys.exit("쓰는 법: validate.py <분석.json>")
    data = json.load(open(argv[0], encoding="utf-8"))
    errors, warns = validate(data)
    for w in warns:
        print("경고", w)
    for e in errors:
        print("오류", e)
    if errors:
        return 1
    print(f"OK {argv[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
