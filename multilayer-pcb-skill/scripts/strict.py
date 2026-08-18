#!/usr/bin/env python3
"""接続性チェッカ: ネットごとに銅(パッド/トラック/ビア)の「島」を数える。

判定モデル:
- トラック同士: カプセル重なり (中心線距離 < w1/2 + w2/2)
- トラック-ビア: 中心線距離 < w/2 + via_d/2
- トラック-パッド: **角丸近似判定** — パッド矩形を min(hw,hh)×30% だけ
  シュリンクした内側矩形にトラックが w/2 以内で届いて初めて接続とみなす。
  丸/角丸パッドを素の矩形で近似すると「角に触れているつもりで実は未接続」を
  見逃す(実基板でヘッダ・フラッシュ・USB等130箇所の隠れ未接続を発見した教訓)。
  素の内接円判定だと細長パッド(コネクタ等)の長軸端進入を誤って落とすため、
  シュリンク矩形が実用上の最適近似。

シュリンク率(既定0.25)は --shrink で調整可能:
  0.0  = 素の矩形 (寛容。丸パッド角の未接続を見逃す)
  0.25 = 推奨。限界進入(数milで角丸を外れる)を警告として拾う
         → 検出されたら配線をパッド中心終端に直すのが本スキルの作法

使い方:
  python3 strict.py                       # 全ネットの島数 (2島以上=未結線)
  python3 strict.py NET1 NET2             # 指定ネットの島の内訳
  python3 strict.py --shrink 0.0          # 寛容モード
"""
import sys
import geom as G

SHRINK = 0.25


def check_net(net, pads=None, tracks=None, vias=None):
    """netの連結成分を返す: [{pads:[], tracks:[], vias:[]}...]"""
    if pads is None:
        pads, tracks, vias = G.load()
    P = [p for p in pads if p.get("net") == net]
    T = [t for t in tracks if t.get("net") == net]
    V = [v for v in vias if v.get("net") == net]
    items = ([("p", i) for i in range(len(P))] +
             [("t", i) for i in range(len(T))] +
             [("v", i) for i in range(len(V))])
    parent = {k: k for k in items}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    def track_layers(t):
        return (t["layer"],)

    def pad_layers(p):
        if p["layer"] == 12 or G.hole_dia(p):
            return tuple(G.LAYERS)
        return (p["layer"],)

    # track-track
    for i, a in enumerate(T):
        for j in range(i + 1, len(T)):
            b = T[j]
            if a["layer"] != b["layer"]:
                continue
            d = G.seg_seg_dist((a["x1"], a["y1"], a["x2"], a["y2"]),
                               (b["x1"], b["y1"], b["x2"], b["y2"]))
            if d < (a.get("w") or 6) / 2 + (b.get("w") or 6) / 2:
                union(("t", i), ("t", j))
    # track-via
    for i, t in enumerate(T):
        for j, v in enumerate(V):
            d = G.seg_pt_dist(t["x1"], t["y1"], t["x2"], t["y2"], v["x"], v["y"])
            if d < (t.get("w") or 6) / 2 + (v.get("d") or G.PROFILES["design"].via_d) / 2:
                union(("t", i), ("v", j))
    def shrunk(p):
        hw, hh = G.pad_rect(p)
        c = SHRINK * min(hw, hh)
        return max(hw - c, 0.1), max(hh - c, 0.1)

    # track-pad (角丸近似: 30%シュリンク矩形)
    for i, t in enumerate(T):
        for j, p in enumerate(P):
            if t["layer"] not in pad_layers(p):
                continue
            hw, hh = shrunk(p)
            d = G.seg_rect_dist((t["x1"], t["y1"], t["x2"], t["y2"]), p["x"], p["y"], hw, hh)
            if d < (t.get("w") or 6) / 2:
                union(("t", i), ("p", j))
    # via-pad
    import math
    for i, v in enumerate(V):
        for j, p in enumerate(P):
            hw, hh = shrunk(p)
            dx = max(abs(v["x"] - p["x"]) - hw, 0)
            dy = max(abs(v["y"] - p["y"]) - hh, 0)
            if math.hypot(dx, dy) < (v.get("d") or 24) / 2:
                union(("v", i), ("p", j))
    # via-via
    import math
    for i, a in enumerate(V):
        for j in range(i + 1, len(V)):
            b = V[j]
            if math.hypot(a["x"] - b["x"], a["y"] - b["y"]) < \
               ((a.get("d") or 24) + (b.get("d") or 24)) / 2:
                union(("v", i), ("v", j))

    groups = {}
    for k in items:
        groups.setdefault(find(k), []).append(k)
    out = []
    for members in groups.values():
        g = {"pads": [], "tracks": [], "vias": []}
        for kind, idx in members:
            if kind == "p":
                g["pads"].append(P[idx])
            elif kind == "t":
                g["tracks"].append(T[idx])
            else:
                g["vias"].append(V[idx])
        out.append(g)
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--shrink" in args:
        i = args.index("--shrink")
        SHRINK = float(args[i + 1])
        del args[i:i + 2]
    pads, tracks, vias = G.load()
    nets = args or sorted({p["net"] for p in pads if p.get("net") and p["net"] != "GND"})
    broken = 0
    for net in nets:
        isl = [g for g in check_net(net, pads, tracks, vias) if g["pads"]]
        if len(isl) > 1 or sys.argv[1:]:
            broken += (len(isl) > 1)
            print(f"{net}: {len(isl)} islands")
            for g in isl:
                ps = [(p["num"], round(p["x"]), round(p["y"]), p["layer"]) for p in g["pads"]]
                print(f"  {len(g['tracks'])}t {len(g['vias'])}v pads={ps[:6]}")
    print(f"\nbroken nets: {broken}/{len(nets)}")
