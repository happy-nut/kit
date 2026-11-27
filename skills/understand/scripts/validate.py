"""UNDERSTAND 출력 JSON 을 검사한다.

스키마(references/output-schema.json)를 그대로 읽어 모양을 보고, 스키마로 못 잡는 규칙
(내부 분석 노출, 금지 표현, 반복, 참조 깨짐, 분량 상한)을 본다.
오류가 하나라도 있으면 종료 코드 1. 경고는 렌더를 막지 않는다.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.join(HERE, "..", "references", "output-schema.json")

BANNED = [
    "축에서 만", "바로 그 갈래", "핵심은 바로", "이 지점에서 중요한",
    "패러다임", "시너지", "퍼즐", "관통하는", "여정", "흥미로운", "놀라운", "진정한 의미", "한 단계 더 나아가",
    "가능성을 열", "맞닿아", "혁신", "게임 체인저", "살펴보겠", "알아보겠", "결론적으로", "요약하면", "한마디로",
    "다시 말해", "좋은 질문", "훌륭한", "물론입니다", "중요합니다", "주목할 만한", "눈여겨볼",
]
INTERNAL = [
    "소비재형", "도구형 정보", "자본재형", "자본재 가치", "메타형", "레버리지", "복리 가치", "복리효과",
    "사고도구", "사고 도구", "분석 절차", "정보 자산", "이해도", "이해 수준", "선행성", "압축성", "생성성", "전이성",
    "정신 모델 업데이트", "사용자 성향", "추상화 사다리", "피라미드 원칙", "MECE", "이슈 트리", "반사실",
]
BANNED_RE = re.compile(r"단순(히|한)[^.]{0,30}(을|를) 넘어")
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
    kinds = {"object": dict, "array": list, "string": str, "boolean": bool}
    if t and not isinstance(value, kinds[t]):
        out.append(f"{path}: {t} 여야 한다")
        return
    if isinstance(value, str):
        if len(value) < node.get("minLength", 0):
            out.append(f"{path}: 비었거나 너무 짧다")
        if len(value) > node.get("maxLength", 10**9):
            out.append(f"{path}: {node['maxLength']}자를 넘는다 ({len(value)}자). 나누거나 줄인다")
        if "pattern" in node and not re.search(node["pattern"], value):
            out.append(f"{path}: 형식 {node['pattern']} 에 맞지 않는다 ({value!r})")
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
            if k not in ("id", "parent", "from", "to", "sources", "url", "kind", "level", "depth", "status", "type", "schema", "relation"):
                yield from strings(v, f"{path}.{k}")


def sentences(text):
    return [s for s in re.split(r"(?<=[.?!])\s+", text.strip()) if s]


def norm(text):
    return re.sub(r"[\s.,·「」'\"()]", "", text)


def semantics(data):
    errors, warns = [], []
    for path, text in strings(data):
        for w in BANNED + ([BANNED_RE.search(text).group(0)] if BANNED_RE.search(text) else []):
            if w in text and w not in data.get("title", ""):
                errors.append(f"{path}: 금지 표현 「{w}」. references/language-rules.md 의 교정 예시대로 사실 문장으로 바꾼다")
        for w in INTERNAL:
            if w in text and w not in data.get("title", ""):
                errors.append(f"{path}: 내부 분석 낱말 「{w}」 이 화면에 나간다. 분류는 배치와 깊이로만 반영한다")
        if EMOJI.search(text):
            errors.append(f"{path}: 이모지")
        if "—" in text:
            errors.append(f"{path}: 긴 대시(—). 문장을 나눈다")
        if SCORE.search(text):
            errors.append(f"{path}: 점수·신뢰도 숫자처럼 보인다. 근거 없는 점수는 쓰지 않는다")
        if len(text) > 120 and len(sentences(text)) == 1 and text.count(",") >= 3:
            warns.append(f"{path}: 쉼표가 많은 긴 한 문장. 나눌 수 있는지 본다")

    if len(sentences(data["essence"]["definition"])) > 1:
        errors.append("$.essence.definition: 정의는 한 문장이다")

    seen = {}
    for path, text in strings(data):
        if path.startswith("$.sources") or len(text) < 25:
            continue
        key = norm(text)
        section = path.split(".")[1].split("[")[0]
        if key in seen and seen[key][1] != section:
            errors.append(f"{path}: {seen[key][0]} 와 같은 문장이다. 섹션끼리 반복하지 않는다")
        seen.setdefault(key, (path, section))

    source_ids = [s["id"] for s in data.get("sources", [])]
    if len(set(source_ids)) != len(source_ids):
        errors.append("$.sources: 같은 id 가 둘")
    used = set()

    def refs(obj, path):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "sources" and path != "$":
                    for r in v:
                        used.add(r)
                        if r not in source_ids:
                            errors.append(f"{path}.sources: 없는 출처 {r}")
                else:
                    refs(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                refs(v, f"{path}[{i}]")
    refs(data, "$")
    for s in source_ids:
        if s not in used:
            warns.append(f"$.sources: {s} 를 가리키는 설명이 없다. 설명 옆에 붙이거나 지운다")

    st = data["structure"]
    if "nodes" in st:
        ids = [n["id"] for n in st["nodes"]]
        if len(set(ids)) != len(ids):
            errors.append("$.structure.nodes: 같은 id 가 둘")
        byid = {n["id"]: n for n in st["nodes"]}
        tops = [n for n in st["nodes"] if n["level"] == 1]
        if len(tops) != 1:
            errors.append("$.structure.nodes: level 1 은 하나다(본질)")
        for n in st["nodes"]:
            p = n.get("parent")
            if n["level"] == 1 and p:
                errors.append(f"$.structure {n['id']}: level 1 은 parent 가 없다")
            if n["level"] > 1:
                if p not in byid:
                    errors.append(f"$.structure {n['id']}: parent {p!r} 가 없다")
                elif byid[p]["level"] != n["level"] - 1:
                    errors.append(f"$.structure {n['id']}: parent 는 바로 위 수준이어야 한다")
        for e in st.get("edges", []):
            for end in (e["from"], e["to"]):
                if byid.get(end, {}).get("level") != 2:
                    errors.append(f"$.structure.edges: {end} 는 level 2 노드가 아니다")
        if not any(n["level"] == 2 for n in st["nodes"]):
            errors.append("$.structure: level 2 항목이 없다. 구조가 없으면 {\"na\": 이유} 로 쓴다")
    mech = data["mechanism"]
    for i, b in enumerate(mech.get("blocks", [])):
        if b["type"] == "diagram":
            nid = {n["id"] for n in b["nodes"]}
            for e in b["edges"]:
                if e["from"] not in nid or e["to"] not in nid:
                    errors.append(f"$.mechanism.blocks[{i}]: 관계도 선이 없는 노드를 가리킨다 ({e['from']}→{e['to']})")
        if b["type"] == "compare":
            for r in b["rows"]:
                if len(r["cells"]) != len(b["columns"]):
                    errors.append(f"$.mechanism.blocks[{i}]: 「{r['label']}」 칸 수가 열 수와 다르다")
    if data["principles"]["kind"] == "principle":
        for i, p in enumerate(data["principles"]["items"]):
            for k in ("condition", "example"):
                if k not in p:
                    errors.append(f"$.principles.items[{i}]: 원리에는 {k} 가 있어야 한다. 옮길 원리가 아니면 kind 를 fact 로")
    visible = lambda x: x.get("depth", "overview") == "overview"
    if not any(visible(p) for p in data["principles"]["items"]):
        errors.append("$.principles: 개요에 보이는 항목이 하나는 있어야 한다")
    if "nodes" in st and not any(n["level"] == 2 and visible(n) for n in st["nodes"]):
        errors.append("$.structure: 개요에 보이는 level 2 항목이 하나는 있어야 한다")
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
