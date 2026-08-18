#!/usr/bin/env python3
"""ビア可能座標の全列挙 — 「ビアをどこに置けるか」を機械で決める。

指定bbox内を1mil格子でスキャンし、実ルール(トラック/パッド/穴/ビア/縁/キープアウト)
に対するスラック(余裕)を numpy でベクトル計算。合法点を余裕最大から
相互30mil間隔の貪欲選抜で提示する。

使い方:
  python3 spots.py x0 x1 y0 y1 [net] [--via micro] [--profile jlc]
    net を与えると同ネット銅は障害物から除外(同ネットビアは最小中心間隔のみ)。
    --via micro でマイクロビア径(9.84/5.91mil = 0.25/0.15mm)。
"""
import sys, math, argparse
import numpy as np
import geom as G

VIA_SIZES = {"std": (24.0, 12.0), "micro": (9.84, 5.91)}


def scan(x0, x1, y0, y1, net="__NEW__", via="std", profile="design", step=1.0, top=12, min_sep=30.0):
    R = G.PROFILES[profile]
    vd, _vh = VIA_SIZES[via]
    r = vd / 2
    pads, tracks, vias = G.load()
    xs = np.arange(x0, x1 + 1e-9, step)
    ys = np.arange(y0, y1 + 1e-9, step)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    bx0, bx1, by0, by1 = G.BOARD
    slack = np.minimum.reduce([X - (bx0 + R.edge + r), (bx1 - R.edge - r) - X,
                               (by1 - R.edge - r) - Y, Y - (by0 + R.edge + r)])
    for t in tracks:
        if t["net"] == net:
            continue
        ax, ay, bx, by = t["x1"], t["y1"], t["x2"], t["y2"]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        if L2 == 0:
            d = np.hypot(X - ax, Y - ay)
        else:
            tt = np.clip(((X - ax) * dx + (Y - ay) * dy) / L2, 0, 1)
            d = np.hypot(X - (ax + tt * dx), Y - (ay + tt * dy))
        slack = np.minimum(slack, d - (r + (t.get("w") or 6) / 2 + R.clr_via))
    for p in pads:
        hw, hh = G.pad_rect(p)
        if p["net"] != net:
            ddx = np.maximum(np.abs(X - p["x"]) - hw, 0)
            ddy = np.maximum(np.abs(Y - p["y"]) - hh, 0)
            slack = np.minimum(slack, np.hypot(ddx, ddy) - (r + R.clr_via))
        hd = G.hole_dia(p)
        if hd:
            slack = np.minimum(slack, np.hypot(X - p["x"], Y - p["y"]) - (hd / 2 + R.clr_hole + r))
    for v in vias:
        d = np.hypot(X - v["x"], Y - v["y"])
        rv = (v.get("d") or R.via_d) / 2
        need = (r + rv) if v["net"] == net else (r + rv + R.clr_via)
        slack = np.minimum(slack, d - need)
    for (kx0, kx1, ky0, ky1, _kls) in G.KEEPOUTS:  # ビアは全層貫通
        ko = (X > kx0 - r) & (X < kx1 + r) & (Y > ky0 - r) & (Y < ky1 + r)
        slack = np.where(ko, -1.0, slack)

    ok = slack > 0.15
    n = int(ok.sum())
    pts = np.column_stack([X[ok], Y[ok], slack[ok]])
    pts = pts[np.argsort(-pts[:, 2])]
    chosen = []
    for x, y, s in pts:
        if all(math.hypot(x - a, y - b) >= min_sep for a, b, _ in chosen):
            chosen.append((float(x), float(y), float(s)))
        if len(chosen) >= top:
            break
    return n, chosen


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("x0", type=float)
    ap.add_argument("x1", type=float)
    ap.add_argument("y0", type=float)
    ap.add_argument("y1", type=float)
    ap.add_argument("net", nargs="?", default="__NEW__")
    ap.add_argument("--via", choices=list(VIA_SIZES), default="std")
    ap.add_argument("--profile", choices=list(G.PROFILES), default="design")
    args = ap.parse_args()
    n, chosen = scan(args.x0, args.x1, args.y0, args.y1, args.net, args.via, args.profile)
    print(f"legal spots: {n} (via={args.via}, profile={args.profile})")
    for x, y, s in chosen:
        print(f"  ({x:.0f},{y:.0f}) slack={s:.1f}")
