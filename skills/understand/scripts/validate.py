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
UI_TALK = re.compile(r"눌러|클릭|탭하|펼쳐 보|접어 두|더 보기|다음 단계로 넘어|아래에서 고르|선택해 보|스크롤|슬라이더|가장 구체적인 수준|갈래로 더|\bL[1-5]\b|모르면")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⭕️]")
SCORE = re.compile(r"\b\d+\s*(점|/\s*10|/\s*100)\b|신뢰도\s*\d")
PLACEHOLDER = re.compile(r"\{([a-z][a-z0-9]*)\}")


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
            if k not in ("id", "from", "to", "src", "url", "kind", "type", "schema", "expr", "when", "via", "x", "ys", "sign", "sources"):
                yield from strings(v, f"{path}.{k}")


def sentences(text):
    return [s for s in re.split(r"(?<=[.?!])\s+", text.strip()) if s]


def norm(text):
    return re.sub(r"[\s.,·「」'\"()]", "", text)


def node_label(calc, concepts, i):
    for x in calc["inputs"] + calc["outputs"]:
        if x["id"] == i:
            return f"{x['label']} 000,000{x['unit']}"
    return next(c["label"] for c in concepts if c["id"] == i)


def sweep(calc, x, n=41, base=None):
    """x 입력을 범위 전체로 움직이며 모든 출력과 환경을 돌려준다. 다른 입력은 base(없으면 기본값)."""
    from expr import run_sim
    inp = next(i for i in calc["inputs"] if i["id"] == x)
    rows = []
    for k in range(n):
        xv = inp["min"] + (inp["max"] - inp["min"]) * k / (n - 1)
        vals = {i["id"]: float((base or {}).get(i["id"], i["value"])) for i in calc["inputs"]}
        vals[x] = xv
        outs, _ = run_sim(calc, vals)
        rows.append({**vals, **outs})
    return rows


def plot_shape(calc, plot, base=None, n=41):
    """그래프가 보여 주는 것: 표시선이 바뀌는 곳, 곡선의 꺾임, 두 선의 교차."""
    from expr import compile_expr, evaluate
    rows = sweep(calc, plot["x"], n, base)
    names = set(rows[0])
    flips = 0
    for m in plot.get("marks", []):
        rpn = compile_expr(m["when"], names)
        vals = [bool(evaluate(rpn, r)) for r in rows]
        flips += sum(1 for a, b in zip(vals, vals[1:]) if a != b)
    bent = False
    for y in plot["ys"]:
        v = [r[y] for r in rows]
        scale = max(abs(t) for t in v) or 1
        if any(abs(v[k + 1] - 2 * v[k] + v[k - 1]) > 1e-6 * scale for k in range(1, len(v) - 1)):
            bent = True
    cross = False
    ys = plot["ys"]
    for i in range(len(ys)):
        for j in range(i + 1, len(ys)):
            d = [r[ys[i]] - r[ys[j]] for r in rows]
            if any(a * b < 0 for a, b in zip(d, d[1:])):
                cross = True
    return flips, bent, cross


def check_model(data, errors, warns):
    m = data["model"]
    calc = m["calc"]
    names = check_vars(calc, errors)
    inputs = {i["id"] for i in calc["inputs"]}
    outputs = {o["id"] for o in calc["outputs"]}
    concepts = {c["id"] for c in m.get("concepts", [])}
    if concepts & names:
        errors.append("$.model.concepts: 계산 변수와 이름이 겹친다")
    every = names | concepts
    linked = set()
    for k, mm in enumerate(m["models"]):
        for l in mm["links"]:
            for end in (l["from"], l["to"]):
                if end not in every:
                    errors.append(f"$.model.models[{k}].links: 없는 변수 {end}")
                linked.add(end)
            if l["from"] == l["to"]:
                errors.append(f"$.model.models[{k}].links: 자기 자신으로 가는 선 ({l['from']})")
    for c in concepts:
        if c not in linked:
            errors.append(f"$.model.concepts: {c} 가 어느 관계에도 없다")
    if errors:
        return
    for k, mm in enumerate(m["models"]):
        from layout import layout, overlap, NODE_H
        ids = list(dict.fromkeys([x for l in mm["links"] for x in (l["from"], l["to"])]))
        nodes = [{"id": i, "label": node_label(calc, m.get("concepts", []), i)} for i in ids]
        edges = [{"from": l["from"], "to": l["to"], "label": f"{l['sign']} {l['label']}"} for l in mm["links"]]
        pos, _, _, paths = layout(nodes, edges)
        boxes = [(x, y, x + w, y + NODE_H) for x, y, w in pos.values()]
        rects = [(p["lx"] - p["lw"] / 2, p["ly"] - 10, p["lx"] + p["lw"] / 2, p["ly"] + 10) for p in paths]
        for j, r in enumerate(rects):
            if any(overlap(r, b, 0) for b in boxes) or any(overlap(r, q, 0) for q in rects[:j]):
                errors.append(f"$.model.models[{k}]: 관계 이름 「{paths[j]['label']}」 이 변수 상자나 다른 이름과 겹친다")
    from expr import compile_expr, ExprError
    for k, p in enumerate(m["plots"]):
        path = f"$.model.plots[{k}]"
        if p["x"] not in inputs:
            errors.append(f"{path}.x: {p['x']} 는 입력이 아니다")
            continue
        bad = [y for y in p["ys"] if y not in outputs]
        if bad:
            errors.append(f"{path}.ys: 출력이 아닌 {bad}")
            continue
        try:
            for mk in p.get("marks", []):
                compile_expr(mk["when"], names)
        except ExprError as x:
            errors.append(f"{path}.marks: 식 오류 ({x})")
            continue
        flips, bent, cross = plot_shape(calc, p)
        if not (flips or bent or cross):
            errors.append(f"{path}: 곧은 선만 있고 임계점도 교차도 없다. 단순 산술은 그래프로 주지 않는다. 변수 사이의 상호작용, 임계점, 트레이드오프, 비선형을 보이는 x 와 출력을 고른다")
        if p.get("marks") and not flips:
            warns.append(f"{path}.marks: 기본값에서 x 범위 안에 표시선이 생기지 않는다")
    for k, ph in enumerate(data["phenomena"]):
        for v in ph["via"]:
            if v not in linked:
                errors.append(f"$.phenomena[{k}].via: {v} 는 모델 관계에 없는 변수다. 현상은 모델로 설명돼야 한다")
    if ("bridge" in data) == ("case" in data):
        errors.append("$: 출발점은 bridge(아는 모델) 와 case(대표 사례) 가운데 하나만 쓴다")
    used_inputs = {p["x"] for p in m["plots"]} | {x for l in [mm["links"] for mm in m["models"]] for e in l for x in (e["from"], e["to"])}
    for i in inputs - used_inputs:
        warns.append(f"$.model.calc: 입력 {i} 가 관계에도 그래프 x 에도 없다")


def check_vars(v, errors, base="$.model.calc"):
    from expr import compile_expr, run_sim, ExprError
    names = set()
    for i in v["inputs"]:
        if not i["min"] <= i["value"] <= i["max"] or i["min"] >= i["max"]:
            errors.append(f"{base}.inputs {i['id']}: min < max 이고 value 는 그 안이어야 한다")
        names.add(i["id"])
    for o in v["outputs"]:
        if o["id"] in names:
            errors.append(f"{base}.outputs {o['id']}: 이름이 겹친다")
        try:
            compile_expr(o["expr"], names)
        except ExprError as x:
            errors.append(f"{base}.outputs {o['id']}: 식 오류 ({x})")
            return names
        names.add(o["id"])
    for corner in ("min", "value", "max"):
        res, _ = run_sim(v, {i["id"]: float(i[corner]) for i in v["inputs"]})
        bad = [k for k, x in res.items() if x != x or abs(x) == float("inf")]
        if bad:
            errors.append(f"{base}: 입력이 모두 {corner} 일 때 {bad} 를 계산할 수 없다")
    return names


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

    check_model(data, errors, warns)
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
