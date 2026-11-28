"""UNDERSTAND 테스트.

쓰는 법:
  python3 -I tests/run.py              사례 검사·렌더·HTML 불변식·나쁜 입력 거절
  python3 -I tests/run.py --browser    위 + 헤드리스 Chrome 으로 사례마다 화면 검사(뼈대 그림이 읽는 자리를 따라가는지, 스크린샷은 tests/out/)
  python3 -I tests/run.py --examples   사례를 examples/<이름>.html 로 다시 렌더
"""
import copy, glob, html, json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from validate import validate, build_states, INTERNAL  # noqa: E402
from render import render, SECTIONS  # noqa: E402

KINDS = {"opportunity-cost": "일반 지식", "transaction-isolation": "기술 개념", "cso-industry": "비즈니스 도메인", "platform-integration-plan": "남의 작업물"}
fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f" → {detail}"))
    if not ok:
        fails.append(name)


def visible_text(page):
    body = page.split("<main", 1)[1].split("<script>", 1)[0]
    return html.unescape(re.sub(r"<[^>]+>", " ", body))


def html_invariants(case, data, page):
    want = [name for key, _, name in SECTIONS if data.get(key)]
    got = re.findall(r'<h2 id="[a-z]+-h"><span class="num">\d\d</span>([^<]+)</h2>', page)
    check(f"{case}: 있는 영역만 고정 순서로", got == want, (got, want))
    check(f"{case}: 스크립트 하나, 데이터 JSON 없음", page.count("<script") == 1 and "application/json" not in page)
    check(f"{case}: CSP 로 바깥 요청 막음", "default-src 'none'" in page and "script-src 'sha256-" in page)
    check(f"{case}: 조절 장치·버튼·접기·목차·출처 마크업 없음", not re.search(r"<(input|button|select|details|nav|sup)\b|data-(plot|in|vars)=|id=\"src-", page))
    check(f"{case}: 뼈대 그림은 하나", page.count('<figure class="stage"') == 1)
    states = build_states(data)
    show = [s["show"] for s in states]
    check(f"{case}: 뼈대가 단계마다 자라 마지막에 다 선다", all(set(a) <= set(b) for a, b in zip(show, show[1:])) and set(show[-1]) == {p["id"] for p in data["skeleton"]["parts"]}, show)
    text = visible_text(page)
    leaked = [s["label"] for s in data["sources"] if s["label"] in text] + [s["url"] for s in data["sources"] if s.get("url") and s["url"] in page]
    check(f"{case}: 출처가 화면에 나가지 않음", not leaked, leaked)
    inner = [w for w in INTERNAL if w in text and w not in data["title"]]
    check(f"{case}: 내부 분석 낱말 없음", not inner, inner)
    return len(text)


def bad_inputs(base):
    def rejects(label, mutate, needle):
        d = copy.deepcopy(base)
        mutate(d)
        errors, _ = validate(d)
        check(f"나쁜 입력 거절: {label}", any(needle in e for e in errors), errors[:3])

    sk = lambda d: d["skeleton"]
    rejects("금지 표현", lambda d: d["phenomena"].append({"text": "이것은 단순한 비용 계산을 넘어 새로운 패러다임이다.", "path": ["best", "cost"]}), "금지 표현")
    rejects("명세가 든 금지 표현", lambda d: d["phenomena"].append({"text": "업계를 누가 아픈지로 나눈다.", "path": ["best", "cost"]}), "금지 표현")
    rejects("내부 분석 노출", lambda d: d["phenomena"].append({"text": "이 정보는 자본재에 속한다.", "path": ["best", "cost"]}), "내부 분석")
    rejects("조작 안내 글", lambda d: d["phenomena"].append({"text": "슬라이더를 움직여 본다.", "path": ["best", "cost"]}), "화면 조작")
    rejects("이모지", lambda d: d.update(thesis="기회비용은 포기한 가치다 \U0001F600"), "이모지")
    rejects("점수", lambda d: d["phenomena"].append({"text": "이 설명의 신뢰도 90 이다.", "path": ["best", "cost"]}), "점수")
    rejects("두 문장 명제", lambda d: d.update(thesis="기회비용은 포기한 가치다. 모든 선택에 있다."), "한 문장")
    rejects("옛 계산 모델(조절 장치)", lambda d: d.update(model={"calc": {}}), "스키마에 없는 키")
    rejects("부분 일곱(큰 뼈대가 아님)", lambda d: sk(d)["parts"].append({"id": "extra", "name": "덤"}), "6개를 넘는다")
    rejects("소개 전에 쓴 개념", lambda d: d["build"][0]["body"].append("그 시간은 가장 큰 대안이 된다."), "아직 세우지 않은")
    rejects("한 단계에 부분 셋", lambda d: d["build"][0]["add"].append("given"), "2개를 넘는다")
    rejects("두 번 세운 부분", lambda d: d["build"][1]["add"].append("time"), "이미 세웠다")
    rejects("세우지 않은 부분", lambda d: d["build"][4].update(add=[]), "세우지 않은 부분")
    rejects("아직 없는 부분을 짚음", lambda d: d["build"][0].update(focus=["cost"]), "아직 세우지 않은 부분을 가리킨다")
    rejects("연결을 벗어난 설명", lambda d: d["phenomena"][0].update(path=["time", "cost"]), "연결돼 있지 않다")
    rejects("설명에 쓰이지 않는 뼈", lambda d: [x.update(path=[p for p in x["path"] if p != "choice"] if len([p for p in x["path"] if p != "choice"]) >= 2 else ["best", "cost"]) for x in d["phenomena"] + d["inferences"]], "쓰이지 않는다")
    rejects("떨어진 뼈대", lambda d: sk(d).update(links=[l for l in sk(d)["links"] if l["to"] != "paid" and l["from"] != "paid"] + [{"from": "paid", "to": "paid", "label": "자기"}]), "자기 자신")
    rejects("없는 부분을 잇는 연결", lambda d: sk(d)["links"].append({"from": "ghost", "to": "cost", "sign": "+", "label": "유령"}), "스키마에 없는 키")
    rejects("출발점이 없는 부분에 짝", lambda d: d["bridge"]["map"].update(ghost="유령"), "없는 부분")
    rejects("없는 출처", lambda d: d["phenomena"][0].update(src=["ghost"]), "없는 출처")
    rejects("영역 사이 반복", lambda d: d["limits"].append({"kind": "condition", "text": d["phenomena"][0]["text"]}), "같은 문장")

    d = copy.deepcopy(base)
    d.pop("limits")
    d.pop("bridge")
    errors, _ = validate(d)
    page = render(d)
    check("빠진 영역은 렌더하지 않고 「해당 없음」도 없음", not errors and "적용 한계" not in page and "출발점" not in page and "해당 없음" not in page, errors)

    d = copy.deepcopy(base)
    d["phenomena"][0]["text"] = '<script>alert(1)</script><img src=x onerror=alert(2)> 를 그대로 보인다.'
    page = render(d)
    check("입력 속 HTML 은 글자로만 나감", "<script>alert" not in page and "<img src=x" not in page and "&lt;script&gt;" in page)


def main(argv):
    cases = sorted(glob.glob(os.path.join(HERE, "cases", "*.json")))
    sizes = {}
    out = os.path.join(HERE, "out")
    for path in cases:
        case = os.path.basename(path)[:-5]
        data = json.load(open(path, encoding="utf-8"))
        errors, warns = validate(data)
        check(f"{case}({KINDS.get(case, '?')}): 검사 통과", not errors, errors[:5])
        if errors:
            continue
        page = render(data)
        sizes[case] = html_invariants(case, data, page)
        if "--examples" in argv:
            open(os.path.join(ROOT, "examples", case + ".html"), "w", encoding="utf-8").write(page)
        if "--browser" in argv:
            with tempfile.TemporaryDirectory() as t:
                f = os.path.join(t, case + ".html")
                open(f, "w", encoding="utf-8").write(page)
                r = subprocess.run(["node", os.path.join(ROOT, "scripts", "browser_check.mjs"), f, os.path.join(out, case)], capture_output=True, text=True)
                check(f"{case}: 브라우저 화면 검사", r.returncode in (0, 3), r.stdout[-900:] + r.stderr[-400:])
                last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
                print("     " + last)
    check("사례 넷(일반 지식, 기술, 비즈니스, 남의 작업물)이 다 있다", set(KINDS) <= set(sizes), sorted(sizes))
    if "opportunity-cost" in sizes and "transaction-isolation" in sizes:
        check("단순 개념이 복잡한 기술보다 짧다", sizes["opportunity-cost"] < sizes["transaction-isolation"], sizes)
    if "opportunity-cost" in sizes:
        bad_inputs(json.load(open(os.path.join(HERE, "cases", "opportunity-cost.json"), encoding="utf-8")))
    print(f"{'실패 ' + str(len(fails)) if fails else '모두 통과'} (사례 {len(cases)})")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
