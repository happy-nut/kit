"""관계도 배치. 위에서 아래로 층을 쌓는다.

층은 되돌아가지 않는 선만 보고 가장 긴 길이로 정한다. 바로 아래 층으로 가는 선은 곡선으로 잇는다.
층을 건너뛰는 선, 되돌아가는 선(되먹임), 같은 층끼리의 선은 마디 옆의 빈 길(레인)로 돌려 마디를 가로지르지 않게 한다.
선 이름은 마디나 다른 선 이름과 겹치지 않게 민다. 글자 폭은 한글 14px, 그 밖 8px 로 어림한다.
"""

NODE_H, ROW_GAP, COL_GAP, PAD, LANE = 36, 64, 28, 16, 30


def text_w(s):
    return sum(14 if ord(c) > 0x2E80 else 8 for c in s)


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
    pos = {}
    for r, ns in rows.items():
        x = (core_w - row_w[r]) / 2
        y = PAD + r * (NODE_H + ROW_GAP)
        for n in ns:
            pos[n["id"]] = (x, y, width[n["id"]])
            x += width[n["id"]] + COL_GAP
    boxes = [(x, y, x + w, y + NODE_H) for x, y, w in pos.values()]
    lanes = {"r": [], "l": []}
    paths = []
    for ed in edges:
        ax, ay, aw = pos[ed["from"]]
        bx, by, bw = pos[ed["to"]]
        ra, rb = rank[ed["from"]], rank[ed["to"]]
        lw = text_w(ed["label"]) * 12.5 / 14 + 12
        if rb == ra + 1:
            x1, y1, x2, y2 = ax + aw / 2, ay + NODE_H, bx + bw / 2, by
            paths.append({"g": ("curve", x1, y1, x2, y2), "label": ed["label"], "lx": (x1 + x2) / 2, "ly": (y1 + y2) / 2, "lw": lw, "band": (y1 + 11, y2 - 11)})
            continue
        lo, hi = min(ra, rb), max(ra, rb)
        span = [b for b, (x, y, w) in zip(boxes, pos.values()) if PAD + lo * (NODE_H + ROW_GAP) <= y <= PAD + hi * (NODE_H + ROW_GAP)]
        side = "r" if (ax + aw / 2 + bx + bw / 2) / 2 >= core_w / 2 else "l"
        busy = [ln for ln in lanes[side] if not (ln[1] < lo or ln[0] > hi)]
        if side == "r":
            lx = max(b[2] for b in span) + LANE * (len(busy) + 1)
            x1, x2 = ax + aw, bx + bw
        else:
            lx = min(b[0] for b in span) - LANE * (len(busy) + 1)
            x1, x2 = ax, bx
        lanes[side].append((lo, hi))
        y1, y2 = ay + NODE_H / 2, by + NODE_H / 2
        s = 1 if side == "r" else -1
        dy = 1 if y2 > y1 else -1
        paths.append({"g": ("lane", x1, y1, x2, y2, lx, s, dy), "label": ed["label"], "lx": lx, "ly": (y1 + y2) / 2, "lw": lw})
    placed = []
    for p in paths:
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
    if g[0] == "curve":
        _, x1, y1, x2, y2 = g
        x1, x2 = x1 + dx, x2 + dx
        my = (y1 + y2) / 2
        return f"M{x1:.1f},{y1:.1f} C{x1:.1f},{my:.1f} {x2:.1f},{my:.1f} {x2:.1f},{y2 - 2:.1f}"
    _, x1, y1, x2, y2, lx, s, dy = g
    x1, x2, lx = x1 + dx, x2 + dx, lx + dx
    return (f"M{x1:.1f},{y1:.1f} H{lx - 10 * s:.1f} Q{lx:.1f},{y1:.1f} {lx:.1f},{y1 + 10 * dy:.1f} "
            f"V{y2 - 10 * dy:.1f} Q{lx:.1f},{y2:.1f} {lx - 10 * s:.1f},{y2:.1f} H{x2 + 3 * s:.1f}")
