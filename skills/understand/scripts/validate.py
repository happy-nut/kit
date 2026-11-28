"""UNDERSTAND 설명 JSON 을 검사한다.

스키마(references/output-schema.json)로 모양을 보고, 스키마로 못 잡는 규칙을 본다.
내부 분석·조작 안내 노출, 금지 표현, 반복, 깨진 참조, 뼈대(이어짐, 소개 전 사용, 연결을 벗어난 설명, 쓰이지 않는 뼈).
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
UI_TALK = re.compile(r"눌러|클릭|탭하|펼쳐 보|접어 두|더 보기|다음 단계로 넘어|아래에서 고르|선택해 보|스크롤|슬라이더|조절해|값을 바꿔 보|가장 구체적인 수준|갈래로 더|\bL[1-5]\b|모르면")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⭕️]")
SCORE = re.compile(r"\b\d+\s*(점|/\s*10|/\s*100)\b|신뢰도\s*\d")


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
        if len(value) < node.get("minProperties", 0):
            out.append(f"{path}: 항목이 {node['minProperties']}개 이상이어야 한다")
        props = node.get("properties", {})
        extra = node.get("additionalProperties")
        for k, v in value.items():
            if k in props:
                shape(root, props[k], v, f"{path}.{k}", out)
            elif extra is False:
                out.append(f"{path}: 스키마에 없는 키 {k}")
            elif isinstance(extra, dict):
                shape(root, extra, v, f"{path}.{k}", out)


def strings(value, path="$"):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from strings(v, f"{path}[{i}]")
    elif isinstance(value, dict):
        for k, v in value.items():
            if k not in ("id", "from", "to", "src", "url", "kind", "type", "schema", "add", "focus", "path", "at", "sources"):
                yield from strings(v, f"{path}.{k}")


def sentences(text):
    return [s for s in re.split(r"(?<=[.?!])\s+", text.strip()) if s]


def norm(text):
    return re.sub(r"[\s.,·「」'\"()]", "", text)


def build_states(data):
    """단계마다 보이는 부분, 짚는 것, 그 단계에 생긴 연결을 계산한다. 렌더러와 검사기가 같이 쓴다."""
    links = data["skeleton"]["links"]
    key = lambda l: f"{l['from']}>{l['to']}"
    claimed = {}
    for k, st in enumerate(data["build"]):
        for f in st.get("focus", []):
            if ">" in f:
                claimed.setdefault(f, k)
    shown, linked, states = [], set(), []
    for k, st in enumerate(data["build"]):
        shown = shown + [a for a in st.get("add", []) if a not in shown]
        new = [key(l) for l in links if key(l) not in linked and l["from"] in shown and l["to"] in shown
               and claimed.get(key(l), k) <= k]
        linked |= set(new)
        focus = st.get("focus") or (st.get("add", []) + new)
        states.append({"show": list(shown), "links": sorted(linked), "focus": list(focus)})
    return states


def path_links(data, path):
    keys = {f"{l['from']}>{l['to']}" for l in data["skeleton"]["links"]}
    out = []
    for a, b in zip(path, path[1:]):
        out.append(f"{a}>{b}" if f"{a}>{b}" in keys else f"{b}>{a}" if f"{b}>{a}" in keys else None)
    return out


def check_skeleton(data, errors, warns):
    sk = data["skeleton"]
    ids = [p["id"] for p in sk["parts"]]
    names = {p["id"]: p["name"] for p in sk["parts"]}
    if len(set(ids)) != len(ids):
        errors.append("$.skeleton.parts: 같은 id 가 둘")
    keys = set()
    for k, l in enumerate(sk["links"]):
        for end in (l["from"], l["to"]):
            if end not in names:
                errors.append(f"$.skeleton.links[{k}]: 없는 부분 {end}")
        if l["from"] == l["to"]:
            errors.append(f"$.skeleton.links[{k}]: 자기 자신으로 가는 연결")
        if f"{l['from']}>{l['to']}" in keys or f"{l['to']}>{l['from']}" in keys:
            errors.append(f"$.skeleton.links[{k}]: 같은 두 부분을 잇는 연결이 둘")
        keys.add(f"{l['from']}>{l['to']}")
    if errors:
        return
    adj = {i: set() for i in ids}
    for l in sk["links"]:
        adj[l["from"]].add(l["to"])
        adj[l["to"]].add(l["from"])
    seen, todo = set(), [ids[0]]
    while todo:
        u = todo.pop()
        if u not in seen:
            seen.add(u)
            todo.extend(adj[u])
    if seen != set(ids):
        errors.append(f"$.skeleton: 뼈대가 하나로 이어지지 않는다. 떨어진 부분 {sorted(set(ids) - seen)}")

    from layout import layout, overlap, NODE_H
    known = (data.get("bridge") or {}).get("map", {})
    pos, _, _, paths = layout([{"id": i, "label": max(names[i], known.get(i, ""), key=len)} for i in ids],
                              [{"from": l["from"], "to": l["to"], "label": l["label"]} for l in sk["links"]])
    boxes = [(x, y, x + w, y + NODE_H) for x, y, w in pos.values()]
    rects = [(p["lx"] - p["lw"] / 2, p["ly"] - 10, p["lx"] + p["lw"] / 2, p["ly"] + 10) for p in paths]
    for j, r in enumerate(rects):
        if any(overlap(r, b, 0) for b in boxes) or any(overlap(r, q, 0) for q in rects[:j]):
            errors.append(f"$.skeleton: 연결 이름 「{paths[j]['label']}」 이 부분 상자나 다른 이름과 겹친다")

    b = data.get("bridge")
    if b:
        for i in list(b["map"]) + b["at"]:
            if i not in names:
                errors.append(f"$.bridge: 없는 부분 {i}")

    added = []
    for k, st in enumerate(data["build"]):
        path = f"$.build[{k}]"
        for a in st.get("add", []):
            if a not in names:
                errors.append(f"{path}.add: 없는 부분 {a}")
            elif a in added:
                errors.append(f"{path}.add: {a} 는 앞 단계에서 이미 세웠다")
            else:
                added.append(a)
        if not st.get("add") and not st.get("focus"):
            errors.append(f"{path}: 새로 세우는 부분도 짚는 것도 없다")
        if k == 0 and not st.get("add"):
            errors.append(f"{path}: 첫 단계는 부분을 세운다")
        later = [names[i] for i in ids if i not in added]
        text = " ".join([st["title"]] + st["body"])
        for nm in later:
            if nm in text and not any(nm in names[a] and nm != names[a] for a in added):
                errors.append(f"{path}: 아직 세우지 않은 「{nm}」 을 쓴다. 개념은 소개한 뒤에 쓴다")
        for f in st.get("focus", []):
            ends = f.split(">")
            if any(e not in added for e in ends):
                errors.append(f"{path}.focus: {f} 는 아직 세우지 않은 부분을 가리킨다")
            if ">" in f and f not in keys:
                errors.append(f"{path}.focus: {f} 라는 연결이 없다")
    missing = [i for i in ids if i not in added]
    if missing:
        errors.append(f"$.build: 세우지 않은 부분 {missing}")
    if errors:
        return

    used = set()
    for where in ("phenomena", "inferences"):
        for k, x in enumerate(data[where]):
            bad = [i for i in x["path"] if i not in names]
            if bad:
                errors.append(f"$.{where}[{k}].path: 없는 부분 {bad}")
                continue
            for (a, c), lk in zip(zip(x["path"], x["path"][1:]), path_links(data, x["path"])):
                if lk is None:
                    errors.append(f"$.{where}[{k}].path: {names[a]} 와 {names[c]} 는 연결돼 있지 않다. 현상은 뼈대의 연결을 따라 설명한다")
            used |= set(x["path"])
    for i in ids:
        if i not in used:
            errors.append(f"$.skeleton: 「{names[i]}」 이 어느 현상이나 추론에도 쓰이지 않는다. 설명에 쓰이지 않는 뼈는 뺀다")


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

    check_skeleton(data, errors, warns)
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
