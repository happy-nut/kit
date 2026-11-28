"""시뮬레이터 식을 RPN 으로 옮기고 계산한다.

식은 여기서 한 번만 파싱한다. 페이지의 스크립트는 이 RPN 만 계산하므로 문자열을 코드로 실행하지 않는다.
쓸 수 있는 것: 숫자, 이름(입력·앞 출력 id), + - * / ( ) , < <= > >= == != && ||, 단항 -, min max round abs.
"""
import math, re

TOKEN = re.compile(r"\s*(?:(\d+(?:\.\d+)?)|([a-z][a-z0-9]*)|(<=|>=|==|!=|&&|\|\||[-+*/(),<>]))")
PREC = {"||": 1, "&&": 2, "==": 3, "!=": 3, "<": 4, "<=": 4, ">": 4, ">=": 4, "+": 5, "-": 5, "*": 6, "/": 6, "neg": 7}
FUNCS = {"min": 2, "max": 2, "round": 1, "abs": 1}


class ExprError(ValueError):
    pass


def tokens(src):
    pos, out = 0, []
    while pos < len(src):
        if src[pos:].strip() == "":
            break
        m = TOKEN.match(src, pos)
        if not m:
            raise ExprError(f"읽을 수 없는 글자: {src[pos:pos + 10]!r}")
        num, name, op = m.groups()
        out.append(("n", float(num)) if num else ("v", name) if name else ("o", op))
        pos = m.end()
    return out


def compile_expr(src, names):
    """식을 RPN 목록으로. names 는 쓸 수 있는 이름 집합."""
    out, stack, prev = [], [], None
    for kind, val in tokens(src):
        if kind == "n":
            out.append(["n", val])
        elif kind == "v":
            if val in FUNCS:
                stack.append(["f", val])
            elif val in names:
                out.append(["v", val])
            else:
                raise ExprError(f"모르는 이름 {val}")
        elif val == "(":
            stack.append(["("])
        elif val == ",":
            while stack and stack[-1][0] != "(":
                out.append(stack.pop())
        elif val == ")":
            while stack and stack[-1][0] != "(":
                out.append(stack.pop())
            if not stack:
                raise ExprError("괄호가 맞지 않는다")
            stack.pop()
            if stack and stack[-1][0] == "f":
                out.append(stack.pop())
        else:
            op = "neg" if val == "-" and (prev is None or (prev[0] == "o" and prev[1] != ")")) else val
            while stack and stack[-1][0] == "o" and PREC[stack[-1][1]] >= PREC[op] and op != "neg":
                out.append(stack.pop())
            stack.append(["o", op])
        prev = (kind, val)
    while stack:
        top = stack.pop()
        if top[0] == "(":
            raise ExprError("괄호가 맞지 않는다")
        out.append(top)
    evaluate(out, {n: 1.0 for n in names})
    return out


def evaluate(rpn, env):
    st = []
    for t in rpn:
        if t[0] == "n":
            st.append(t[1])
        elif t[0] == "v":
            st.append(env[t[1]])
        elif t[0] == "f":
            k = FUNCS[t[1]]
            if len(st) < k:
                raise ExprError(f"{t[1]} 의 인자가 모자란다")
            args = [st.pop() for _ in range(k)][::-1]
            st.append({"min": min, "max": max, "round": lambda x: math.floor(x + 0.5), "abs": abs}[t[1]](*args))
        elif t[1] == "neg":
            if not st:
                raise ExprError("식이 끝나지 않았다")
            st.append(-st.pop())
        else:
            if len(st) < 2:
                raise ExprError("식이 끝나지 않았다")
            b, a = st.pop(), st.pop()
            op = t[1]
            if op == "/":
                st.append(a / b if b else float("nan"))
            else:
                st.append({"+": a + b, "-": a - b, "*": a * b, "<": float(a < b), "<=": float(a <= b), ">": float(a > b),
                           ">=": float(a >= b), "==": float(a == b), "!=": float(a != b), "&&": float(bool(a) and bool(b)),
                           "||": float(bool(a) or bool(b))}[op])
    if len(st) != 1:
        raise ExprError("식이 하나의 값으로 끝나지 않는다")
    return st[0]


def run_sim(sim, values=None):
    """입력값(없으면 기본값)으로 출력과 참인 notes 를 계산한다."""
    env = {i["id"]: float(i["value"]) for i in sim["inputs"]}
    env.update(values or {})
    names = set(env)
    outs = {}
    for o in sim["outputs"]:
        env[o["id"]] = outs[o["id"]] = evaluate(compile_expr(o["expr"], names), env)
        names.add(o["id"])
    notes = [n["text"] for n in sim.get("notes", []) if evaluate(compile_expr(n["when"], names), env)]
    return outs, notes


def fmt(value, digits=0):
    if value != value or value in (float("inf"), float("-inf")):
        return "계산 불가"
    s = f"{value:,.{int(digits)}f}"
    return "0" if s in ("-0", "-0.0", "-0.00") else s
