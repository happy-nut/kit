"""UNDERSTAND 테스트.

쓰는 법:
  python3 -I tests/run.py              사례 검사·렌더·HTML 불변식·나쁜 입력 거절
  python3 -I tests/run.py --browser    위 + 헤드리스 Chrome 으로 사례마다 상호작용 검사(스크린샷은 tests/out/)
  python3 -I tests/run.py --examples   사례를 examples/<이름>.html 로 다시 렌더
"""
import copy, glob, html, json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from validate import validate, INTERNAL  # noqa: E402
from render import render  # noqa: E402

NAMES = ["본질", "전체 구조", "작동 원리", "조건과 한계", "기억할 원리"]
fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f" → {detail}"))
    if not ok:
        fails.append(name)


def visible_text(page):
    body = page.split("<main>", 1)[1].split("<script>", 1)[0]
    return html.unescape(re.sub(r"<[^>]+>", " ", body))


def html_invariants(case, page):
    names = re.findall(r'<h2 id="s\d-h">([^<]+)</h2>', page)
    check(f"{case}: 다섯 섹션 이름·순서", names == NAMES, names)
    check(f"{case}: 스크립트는 하나, 데이터 JSON 없음", page.count("<script") == 1 and "application/json" not in page)
    check(f"{case}: CSP 로 바깥 요청 막음", "default-src 'none'" in page and "script-src 'sha256-" in page)
    check(f"{case}: 바깥 주소를 불러오지 않음", not re.search(r'<(script|link|img|iframe)[^>]*(src|href)="https?:', page))
    text = visible_text(page)
    leaked = [w for w in INTERNAL if w in text and w not in json.load(open(os.path.join(HERE, "cases", case + ".json")))["title"]]
    check(f"{case}: 내부 분석 낱말이 화면에 없음", not leaked, leaked)
    check(f"{case}: 근거 없는 백분율 이해도 없음", not re.search(r"이해도|진행률", text))
    return len(text)


def bad_inputs(base):
    def rejects(label, mutate, needle):
        d = copy.deepcopy(base)
        mutate(d)
        errors, _ = validate(d)
        check(f"나쁜 입력 거절: {label}", any(needle in e for e in errors), errors[:3])

    rejects("금지 표현", lambda d: d["essence"]["support"].append("이것은 단순한 개념을 넘어 새로운 패러다임이다."), "금지 표현")
    rejects("내부 분류 노출", lambda d: d["essence"]["support"].append("이 정보는 자본재형 정보다."), "내부 분석")
    rejects("이모지", lambda d: d["essence"].update(definition="기회비용은 포기한 가치다 \U0001F600"), "이모지")
    rejects("원리 넷", lambda d: d["principles"]["items"].extend(d["principles"]["items"] * 3), "3개를 넘는다")
    rejects("정의 두 문장", lambda d: d["essence"].update(definition="기회비용은 포기한 가치다. 모든 선택에 있다."), "한 문장")
    rejects("섹션 추가", lambda d: d.update(extra={"x": 1}), "스키마에 없는 키")
    rejects("없는 부모", lambda d: d["structure"]["nodes"][1].update(parent="nope"), "parent")
    rejects("없는 출처", lambda d: d["essence"].update(sources=["ghost"]), "없는 출처")
    rejects("섹션 사이 반복", lambda d: d["limits"]["items"].append({"kind": "condition", "text": d["essence"]["support"][0]}), "같은 문장")
    rejects("점수", lambda d: d["essence"]["support"].append("이 설명의 신뢰도 90 이다."), "점수")

    d = copy.deepcopy(base)
    d["mechanism"] = {"na": "이 대상은 작동 과정이 없는 정의다."}
    errors, _ = validate(d)
    page = render(d)
    check("해당 없음 섹션은 제목과 접힌 표시만", not errors and '<details class="na"' in page and len(re.findall(r"<h2 id=\"s[0-9]-h\">", page)) == 5, errors)

    d = copy.deepcopy(base)
    d["essence"]["support"] = ['<script>alert(1)</script><img src=x onerror=alert(2)> 를 그대로 보인다.']
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
        check(f"{case}: 검증 통과", not errors, errors[:5])
        if errors:
            continue
        page = render(data)
        sizes[case] = html_invariants(case, page)
        if "--examples" in argv:
            open(os.path.join(ROOT, "examples", case + ".html"), "w", encoding="utf-8").write(page)
        if "--browser" in argv:
            with tempfile.TemporaryDirectory() as t:
                f = os.path.join(t, case + ".html")
                open(f, "w", encoding="utf-8").write(page)
                r = subprocess.run(["node", os.path.join(ROOT, "scripts", "browser_check.mjs"), f, os.path.join(out, case)], capture_output=True, text=True)
                check(f"{case}: 브라우저 상호작용", r.returncode in (0, 3), r.stdout[-800:] + r.stderr[-400:])
                print("     " + r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
    if "opportunity-cost" in sizes and "transaction-isolation" in sizes:
        a, b = sizes["opportunity-cost"], sizes["transaction-isolation"]
        check("단순 개념이 복잡한 기술보다 짧다", a * 1.5 < b, (a, b))
    if "opportunity-cost" in sizes:
        bad_inputs(json.load(open(os.path.join(HERE, "cases", "opportunity-cost.json"), encoding="utf-8")))
    print(f"{'실패 ' + str(len(fails)) if fails else '모두 통과'} (사례 {len(cases)})")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
