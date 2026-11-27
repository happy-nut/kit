"""관계도 배치. 위에서 아래로 층을 쌓는다.

층은 앞으로 가는 선만 보고 가장 긴 길이로 정한다. 되돌아가는 선(되먹임)과 같은 층끼리의 선은
옆으로 휘어 그린다. 글자 폭은 한글 14px, 그 밖 8px 로 어림한다(글꼴 14px 기준).
"""

NODE_H, ROW_GAP, COL_GAP, PAD = 36, 64, 24, 16


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
    return rank, back


def layout(nodes, edges):
    rank, back = ranks(nodes, edges)
    rows = {}
    for n in nodes:
        rows.setdefault(rank[n["id"]], []).append(n)
    width = {n["id"]: max(72, text_w(n["label"]) + 28) for n in nodes}
    row_w = {r: sum(width[n["id"]] for n in ns) + COL_GAP * (len(ns) - 1) for r, ns in rows.items()}
    side = 80 if back or any(rank[x["from"]] == rank[x["to"]] for x in edges) else 0
    total_w = max(row_w.values()) + 2 * PAD + 2 * side
    pos = {}
    for r, ns in rows.items():
        x = (total_w - row_w[r]) / 2
        y = PAD + r * (NODE_H + ROW_GAP)
        for n in ns:
            pos[n["id"]] = (x, y, width[n["id"]])
            x += width[n["id"]] + COL_GAP
    total_h = PAD * 2 + (max(rows) + 1) * NODE_H + max(rows) * ROW_GAP
    paths = []
    for ed in edges:
        ax, ay, aw = pos[ed["from"]]
        bx, by, bw = pos[ed["to"]]
        lw = text_w(ed["label"]) * 12 / 14 + 12
        if rank[ed["to"]] > rank[ed["from"]]:
            x1, y1, x2, y2 = ax + aw / 2, ay + NODE_H, bx + bw / 2, by
            my = (y1 + y2) / 2
            d = f"M{x1:.1f},{y1:.1f} C{x1:.1f},{my:.1f} {x2:.1f},{my:.1f} {x2:.1f},{y2 - 2:.1f}"
            lx, ly = (x1 + x2) / 2, my
        else:
            right = ax + aw / 2 >= total_w / 2
            x1 = ax + aw if right else ax
            x2 = bx + bw if right else bx
            y1, y2 = ay + NODE_H / 2, by + NODE_H / 2
            cx = (max(x1, x2) + side * 0.9) if right else (min(x1, x2) - side * 0.9)
            if y1 == y2:
                y1, y2 = ay + NODE_H * 0.3, by + NODE_H * 0.7
            d = f"M{x1:.1f},{y1:.1f} C{cx:.1f},{y1:.1f} {cx:.1f},{y2:.1f} {x2 + (3 if right else -3):.1f},{y2:.1f}"
            lx, ly = cx - (lw / 2 - 6 if right else -(lw / 2 - 6)), (y1 + y2) / 2
            lx = min(max(lx, lw / 2 + 2), total_w - lw / 2 - 2)
        paths.append({"d": d, "label": ed["label"], "lx": lx, "ly": ly, "lw": lw})
    placed = []
    for p in paths:
        base, k = p["ly"], 0
        while any(abs(p["lx"] - q["lx"]) < (p["lw"] + q["lw"]) / 2 + 4 and abs(p["ly"] - q["ly"]) < 22 for q in placed):
            k += 1
            p["ly"] = base + (11 * ((k + 1) // 2)) * (1 if k % 2 else -1) * 2
            if k > 12:
                p["lx"] += p["lw"] / 2 + 6
                k, base = 0, p["ly"]
        placed.append(p)
    return pos, round(total_w), round(total_h), paths
