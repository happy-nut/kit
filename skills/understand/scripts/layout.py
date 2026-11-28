"""관계도 배치. 위에서 아래로 층을 쌓는다.

층은 되돌아가지 않는 선만 보고 가장 긴 길이로 정한다. 바로 아래 층으로 가는 선은 곡선으로 잇는다.
층을 건너뛰는 선, 되돌아가는 선(되먹임), 같은 층끼리의 선은 마디 옆의 빈 길(레인)로 돌려 마디를 가로지르지 않게 한다.
선 이름은 마디나 다른 선 이름과 겹치지 않게 민다. 글자 폭은 마디 글자(15.5px) 기준 한글 15.5px, 그 밖 9px 로 어림한다.
"""

NODE_H, ROW_GAP, WIDE_GAP, COL_GAP, PAD, LANE = 40, 46, 84, 28, 12, 30


def text_w(s):
    return sum(15.5 if ord(c) > 0x2E80 else 9 for c in s)


def ranks(nodes, edges):
    ids = [n["id"] for n in nodes]
    out = {i: [] for i in ids}
    for ed in edges:
        out[ed["from"]].append(ed["to"])
    state, back = {}, set()

    def dfs(u):
        state[u] = 1
        for v in out[u]:
            if state.get(v) == 1:
                back.add((u, v))
            elif v not in state:
                dfs(v)
        state[u] = 2
    for i in ids:
        if i not in state:
            dfs(i)
    rank = {i: 0 for i in ids}
    for _ in ids:
        for ed in edges:
            a, b = ed["from"], ed["to"]
            if (a, b) not in back and a != b and rank[b] < rank[a] + 1:
                rank[b] = rank[a] + 1
    # 들어오는 선만 있는 뿌리는 가장 가까운 자식 바로 위로 내린다(정부 같은 마디가 맨 위에 홀로 뜨지 않게).
    for i in ids:
        kids = [rank[b] for a, b in ((e["from"], e["to"]) for e in edges) if a == i and (a, b) not in back]
        if kids and not any(e["to"] == i for e in edges):
            rank[i] = max(rank[i], min(kids) - 1)
    return rank, back


def overlap(a, b, gap=4):
    return a[0] < b[2] + gap and b[0] < a[2] + gap and a[1] < b[3] + gap and b[1] < a[3] + gap


def layout(nodes, edges):
    rank, back = ranks(nodes, edges)
    rows = {}
    for n in nodes:
        rows.setdefault(rank[n["id"]], []).append(n)
    # 층 안 순서: 위 층 이웃의 평균 위치로 정렬해 교차를 줄인다.
    order = {}
    for r in sorted(rows):
        def key(n):
            ups = [order[e["from"]] for e in edges if e["to"] == n["id"] and e["from"] in order and rank[e["from"]] < r]
            return sum(ups) / len(ups) if ups else 0.5
        rows[r].sort(key=key)
        for k, n in enumerate(rows[r]):
            order[n["id"]] = (k + 0.5) / len(rows[r])
    width = {n["id"]: max(72, text_w(n["label"]) + 28) for n in nodes}
    row_w = {r: sum(width[n["id"]] for n in ns) + COL_GAP * (len(ns) - 1) for r, ns in rows.items()}
    core_w = max(row_w.values())
    # 곡선이 한 마디에서 갈라지거나 한 마디로 모이는 층 사이는 이름 둘이 위아래로 설 만큼 넓힌다.
    fan = {}
    for ed in edges:
        a, b = rank[ed["from"]], rank[ed["to"]]
        if b == a + 1:
            fan.setdefault(("out", ed["from"]), []).append(a)
            fan.setdefault(("in", ed["to"]), []).append(a)
    wide = {v[0] for v in fan.values() if len(v) >= 2}
    top = {0: PAD}
    for r in range(1, max(rows) + 1):
        top[r] = top[r - 1] + NODE_H + (WIDE_GAP if r - 1 in wide else ROW_GAP)
    pos = {}
    for r, ns in rows.items():
        x = (core_w - row_w[r]) / 2
        y = top[r]
        for n in ns:
            pos[n["id"]] = (x, y, width[n["id"]])
            x += width[n["id"]] + COL_GAP
    boxes = [(x, y, x + w, y + NODE_H) for x, y, w in pos.values()]
    lanes = {"r": [], "l": []}
    paths = []
    # 짧은 레인이 안쪽, 긴 레인이 바깥쪽에 서야 서로 가로지르지 않는다. 원래 순서는 나중에 되돌린다.
    span_of = lambda ed: abs(rank[ed["to"]] - rank[ed["from"]])
    order_idx = sorted(range(len(edges)), key=lambda i: (span_of(edges[i]) <= 1, span_of(edges[i])), reverse=False)
    order_idx = [i for i in order_idx if span_of(edges[i]) <= 1] + sorted([i for i in order_idx if span_of(edges[i]) > 1], key=lambda i: span_of(edges[i]))
    used_ports = {}

    def port(node, side):
        # 같은 마디의 같은 옆으로 레인이 여럿 붙으면 붙는 높이를 엇갈린다.
        k = used_ports.get((node, side), 0)
        used_ports[(node, side)] = k + 1
        return [0, -9, 9, -15, 15][min(k, 4)]
    for ed in [edges[i] for i in order_idx]:
        ax, ay, aw = pos[ed["from"]]
        bx, by, bw = pos[ed["to"]]
        ra, rb = rank[ed["from"]], rank[ed["to"]]
        lw = text_w(ed["label"]) * 13.5 / 15.5 + 12
        if rb == ra + 1:
            x1, y1, x2, y2 = ax + aw / 2, ay + NODE_H, bx + bw / 2, by
            paths.append({"g": ("curve", x1, y1, x2, y2), "label": ed["label"], "lx": (x1 + x2) / 2, "ly": (y1 + y2) / 2, "lw": lw, "band": (y1 + 11, y2 - 11)})
            continue
        lo, hi = min(ra, rb), max(ra, rb)
        span = [b for b, (x, y, w) in zip(boxes, pos.values()) if top[lo] <= y <= top[hi]]
        row_of = lambda y0: [b for b in boxes if abs(b[1] - y0) < 1]
        clear = {
            "r": not any(b[0] > ax + aw + 1 for b in row_of(ay)) and not any(b[0] > bx + bw + 1 for b in row_of(by)),
            "l": not any(b[2] < ax - 1 for b in row_of(ay)) and not any(b[2] < bx - 1 for b in row_of(by)),
        }
        pref = "r" if (ax + aw / 2 + bx + bw / 2) / 2 >= core_w / 2 else "l"
        side = pref if clear[pref] else ("l" if pref == "r" and clear["l"] else "r" if pref == "l" and clear["r"] else pref)
        busy = [ln for ln in lanes[side] if not (ln[1] < lo or ln[0] > hi)]
        if side == "r":
            lx = max(b[2] for b in span) + LANE * (len(busy) + 1)
        else:
            lx = min(b[0] for b in span) - LANE * (len(busy) + 1)
        lanes[side].append((lo, hi))
        s = 1 if side == "r" else -1
        if clear[side]:
            x1, x2 = (ax + aw, bx + bw) if side == "r" else (ax, bx)
            y1 = ay + NODE_H / 2 + port(ed["from"], side)
            y2 = by + NODE_H / 2 + port(ed["to"], side)
            dy = 1 if y2 > y1 else -1
            paths.append({"g": ("lane", x1, y1, x2, y2, lx, s, dy), "label": ed["label"], "lx": lx, "ly": (y1 + y2) / 2, "lw": lw, "side": s})
        else:
            # 같은 줄의 다른 마디를 가로지르지 않게, 마디 사이 빈 줄(층 사이 틈)로 나가 옆 레인을 탄다.
            down = rb >= ra
            sx, sy = ax + aw / 2 + 6 * s, (ay + NODE_H if down else ay)
            tx, ty = bx + bw / 2 - 6 * s, (by if down else by + NODE_H)
            g1 = sy + (ROW_GAP / 2 if down else -ROW_GAP / 2) + 6 * s
            g2 = ty + (-ROW_GAP / 2 if down else ROW_GAP / 2) - 6 * s
            pts = [(sx, sy), (sx, g1), (lx, g1), (lx, g2), (tx, g2), (tx, ty + (-2 if down else 2))]
            paths.append({"g": ("poly", pts), "label": ed["label"], "lx": lx, "ly": (g1 + g2) / 2, "lw": lw})
    # 레인 이름은 자기 레인 위에 둔다. 마디, 다른 레인의 가로 구간, 앞서 둔 이름을 피해 레인을 따라 위아래로 옮긴다.
    def lane_bars(q):
        _, x1, y1, x2, y2, lx, _, _ = q["g"]
        return [(min(x1, lx), y1 - 4, max(x1, lx), y1 + 4), (min(x2, lx), y2 - 4, max(x2, lx), y2 + 4)]
    lane_placed = []
    for p in paths:
        if "side" in p:
            _, x1, y1, x2, y2, lx, _, _ = p["g"]
            lo_y, hi_y = min(y1, y2) + 16, max(y1, y2) - 16
            bars = [b for q in paths if "side" in q and q is not p for b in lane_bars(q)]
            mid = (y1 + y2) / 2
            cands = sorted([lo_y + t * 4 for t in range(int((hi_y - lo_y) / 4) + 1)], key=lambda y: abs(y - mid))
            for y in cands:
                r = (lx - p["lw"] / 2, y - 10, lx + p["lw"] / 2, y + 10)
                if not any(overlap(r, b) for b in boxes + bars + lane_placed):
                    p["ly"] = y
                    break
            p["band"] = (p["ly"], p["ly"])
            lane_placed.append((lx - p["lw"] / 2, p["ly"] - 10, lx + p["lw"] / 2, p["ly"] + 10))
    paths = [paths[order_idx.index(i)] for i in range(len(edges))]
    placed = []

    def on_curve(g, t):
        _, x1, y1, x2, y2 = g
        my = (y1 + y2) / 2
        u = 1 - t
        return (u ** 3 * x1 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t ** 3 * x2,
                u ** 3 * y1 + 3 * u * u * t * my + 3 * u * t * t * my + t ** 3 * (y2 - 2))
    for p in paths:
        # 곡선 이름은 먼저 자기 곡선을 따라 자리를 찾는다. 두 곡선이 한 마디로 모이면 가운데가 겹치므로 덜 모인 쪽으로 옮긴다.
        if p["g"][0] == "curve":
            y1, y2 = p["g"][2], p["g"][4]
            mid = (y1 + y2) / 2
            ys = [y for y in (mid, mid - 22, mid + 22) if y1 + 14 <= y <= y2 - 14] or [mid]
            for y in ys:
                lo_t, hi_t = 0.0, 1.0
                for _ in range(30):  # 곡선의 y 는 t 에 대해 늘기만 하므로 이분법으로 t 를 찾는다
                    m = (lo_t + hi_t) / 2
                    lo_t, hi_t = (m, hi_t) if on_curve(p["g"], m)[1] < y else (lo_t, m)
                cx, cy = on_curve(p["g"], lo_t)
                p["lx"], p["ly"] = cx, cy
                r = (p["lx"] - p["lw"] / 2, p["ly"] - 10, p["lx"] + p["lw"] / 2, p["ly"] + 10)
                if not any(overlap(r, b) for b in boxes + placed):
                    break
            else:
                p["lx"], p["ly"] = on_curve(p["g"], 0.5)
            p["band"] = (p["g"][2] + 11, p["g"][4] - 11)
        base, k = p["ly"], 0
        rect = lambda: (p["lx"] - p["lw"] / 2, p["ly"] - 10, p["lx"] + p["lw"] / 2, p["ly"] + 10)
        bx0, lo_y, hi_y = p["lx"], *p.get("band", (-1e9, 1e9))
        while any(overlap(rect(), b) for b in boxes + placed) and k < 40:
            k += 1
            step = 12 * ((k + 1) // 2) * (1 if k % 2 else -1)
            if lo_y <= base + step <= hi_y:
                p["lx"], p["ly"] = bx0, base + step
            else:  # 층 사이 틈을 벗어나면 위아래 대신 옆으로 민다
                p["ly"] = base
                p["lx"] = bx0 + (p["lw"] / 2 + 10) * ((k + 1) // 2) * (1 if k % 2 else -1) / 2
        placed.append(rect())
    # 레인이 왼쪽으로 나가면 전체를 오른쪽으로 민다.
    min_x = min([b[0] for b in boxes] + [r[0] for r in placed]) - PAD
    max_x = max([b[2] for b in boxes] + [r[2] for r in placed]) + PAD
    max_y = max([b[3] for b in boxes] + [r[3] for r in placed]) + PAD
    shift = -min_x
    pos = {k: (x + shift, y, w) for k, (x, y, w) in pos.items()}
    for p in paths:
        p["d"] = path_d(p.pop("g"), shift)
        p["lx"] += shift
    return pos, round(max_x - min_x), round(max_y), paths


def path_d(g, dx):
    if g[0] == "poly":
        return "M" + " L".join(f"{x + dx:.1f},{y:.1f}" for x, y in g[1])
    if g[0] == "curve":
        _, x1, y1, x2, y2 = g
        x1, x2 = x1 + dx, x2 + dx
        my = (y1 + y2) / 2
        return f"M{x1:.1f},{y1:.1f} C{x1:.1f},{my:.1f} {x2:.1f},{my:.1f} {x2:.1f},{y2 - 2:.1f}"
    _, x1, y1, x2, y2, lx, s, dy = g
    x1, x2, lx = x1 + dx, x2 + dx, lx + dx
    return (f"M{x1:.1f},{y1:.1f} H{lx - 10 * s:.1f} Q{lx:.1f},{y1:.1f} {lx:.1f},{y1 + 10 * dy:.1f} "
            f"V{y2 - 10 * dy:.1f} Q{lx:.1f},{y2:.1f} {lx - 10 * s:.1f},{y2:.1f} H{x2 + 3 * s:.1f}")
