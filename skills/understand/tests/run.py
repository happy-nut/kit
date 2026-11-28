"""UNDERSTAND 테스트.

쓰는 법:
  python3 -I tests/run.py              사례 검사·렌더·HTML 불변식·나쁜 입력 거절
  python3 -I tests/run.py --browser    위 + 헤드리스 Chrome 으로 사례마다 화면 검사(스크린샷은 tests/out/)
  python3 -I tests/run.py --examples   사례를 examples/<이름>.html 로 다시 렌더
"""
import copy, glob, html, json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from validate import validate, INTERNAL  # noqa: E402
from render import render, SECTIONS  # noqa: E402
from expr import run_sim, fmt  # noqa: E402

KINDS = {"opportunity-cost": "일반 지식", "transaction-isolation": "기술 개념", "cso-industry": "비즈니스 도메인", "platform-integration-plan": "남의 작업물"}
fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f" → {detail}"))
    if not ok:
        fails.append(name)


def visible_text(page):
    body = page.split("<main>", 1)[1].split("<script>", 1)[0]
    return html.unescape(re.sub(r"<[^>]+>", " ", body))


def html_invariants(case, data, page):
    want = [name for key, _, name in SECTIONS if data.get(key)]
    got = re.findall(r'<h2 id="[a-z]+-h"><span class="num">\d\d</span>([^<]+)</h2>', page)
    check(f"{case}: 있는 영역만 고정 순서로", got == want, (got, want))
    check(f"{case}: 스크립트 하나, 데이터 JSON 없음", page.count("<script") == 1 and "application/json" not in page)
    check(f"{case}: CSP 로 바깥 요청 막음", "default-src 'none'" in page and "script-src 'sha256-" in page)
    check(f"{case}: 버튼·접기·목차·출처 마크업 없음", not re.search(r"<(button|details|nav|sup)\b|data-(depth|fold|more|reset)|id=\"src-", page))
    text = visible_text(page)
    leaked = [s["label"] for s in data["sources"] if s["label"] in text] + [s["url"] for s in data["sources"] if s.get("url") and s["url"] in page]
    check(f"{case}: 출처가 화면에 나가지 않음", not leaked, leaked)
    inner = [w for w in INTERNAL if w in text and w not in data["title"]]
    check(f"{case}: 내부 분석 낱말 없음", not inner, inner)
    return len(text)


def sim_expect(data, path):
    sim = data.get("application", {}).get("sim")
    if not sim:
        return None
    vals = {i["id"]: i["min"] + (i["max"] - i["min"]) * 0.7 // i["step"] * i["step"] for i in sim["inputs"]}
    outs, notes = run_sim(sim, vals)
    exp = {"inputs": vals, "outputs": [fmt(outs[o["id"]], o.get("digits", 0)) for o in sim["outputs"]], "notes": notes}
    json.dump(exp, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    return path


def bad_inputs(base):
    def rejects(label, mutate, needle):
        d = copy.deepcopy(base)
        mutate(d)
        errors, _ = validate(d)
        check(f"나쁜 입력 거절: {label}", any(needle in e for e in errors), errors[:3])

    rejects("금지 표현", lambda d: d["primer"].append("이것은 단순한 비용 계산을 넘어 새로운 패러다임이다."), "금지 표현")
    rejects("명세가 든 금지 표현", lambda d: d["primer"].append("업계를 누가 아픈지로 나눈다."), "금지 표현")
    rejects("내부 분석 노출", lambda d: d["primer"].append("이 정보는 자본재에 속한다."), "내부 분석")
    rejects("조작 안내 글", lambda d: d["primer"].append("모르는 용어는 눌러서 확인한다."), "화면 조작")
    rejects("계층 표시", lambda d: d["primer"].append("L2 에서 갈래가 나뉜다."), "화면 조작")
    rejects("이모지", lambda d: d.update(thesis="기회비용은 포기한 가치다 \U0001F600"), "이모지")
    rejects("점수", lambda d: d["primer"].append("이 설명의 신뢰도 90 이다."), "점수")
    rejects("두 문장 명제", lambda d: d.update(thesis="기회비용은 포기한 가치다. 모든 선택에 있다."), "한 문장")
    rejects("없는 키", lambda d: d.update(quiz=[]), "스키마에 없는 키")
    rejects("고립된 그림 마디", lambda d: d["structure"]["figure"]["nodes"].append({"id": "alone", "label": "외톨이"}), "이어진 선이 없다")
    rejects("이름 없는 선", lambda d: d["structure"]["figure"]["edges"][0].pop("label"), "label")
    rejects("깨진 식", lambda d: d["application"]["sim"]["outputs"][0].update(expr="book * nope"), "식 오류")
    rejects("0 으로 나누는 식", lambda d: d["application"]["sim"]["outputs"].append({"id": "bad", "label": "x", "unit": "", "expr": "book / (hours - hours)"}), "계산할 수 없다")
    rejects("없는 출처", lambda d: d["mechanism"]["steps"][0].update(src=["ghost"]), "없는 출처")
    rejects("영역 사이 반복", lambda d: d["application"]["limits"].append({"kind": "condition", "text": d["mechanism"]["steps"][0]["body"][0]}), "같은 문장")
    rejects("빈 영역", lambda d: d.update(principles=[]), "비었다")
    rejects("한 현상만 설명하는 모델", lambda d: d["relations"]["models"][0].update(explains=d["relations"]["models"][0]["explains"][:1]), "2개 이상")

    d = copy.deepcopy(base)
    for k in ("relations", "principles"):
        d.pop(k)
    errors, _ = validate(d)
    page = render(d)
    check("빠진 영역은 렌더하지 않고 「해당 없음」도 없음", not errors and "핵심 관계" not in page and "재사용할 원리" not in page and "해당 없음" not in page, errors)

    d = copy.deepcopy(base)
    d["primer"] = ['<script>alert(1)</script><img src=x onerror=alert(2)> 를 그대로 보인다.']
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
                exp = sim_expect(data, os.path.join(t, "expect.json"))
                r = subprocess.run(["node", os.path.join(ROOT, "scripts", "browser_check.mjs"), f, os.path.join(out, case)] + ([exp] if exp else []), capture_output=True, text=True)
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
