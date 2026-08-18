#!/usr/bin/env python3
"""適用前検証ゲート (validate-before-apply)

新規の銅 (routes.json: {routes:[seg...], vias:[via...]}) を、盤上の全既存物 +
新規同士の相互干渉まで実ルールで監査する。**違反が1件でもあれば適用しない**。

  seg = {net, layer, x1, y1, x2, y2, w}
  via = {net, x, y, d?, hole?}   (省略時はプロファイル既定径)

使い方:
  python3 validate.py routes.json                # designプロファイル
  python3 validate.py routes.json --profile jlc  # JLC製造規準(3.5mil)
終了コード 0=合格 / 1=違反あり。
ライブラリとして: validate.check(routes, vias, profile="design") -> [違反文字列]
"""
import sys, math, argparse
import geom as G

MARGIN = 0.05  # 数値誤差の許容


def check(routes, vias, profile="design", pads=None, tracks=None, board_vias=None):
    R = G.PROFILES[profile]
    if pads is None:
        pads, tracks, board_vias = G.load()
    bad = []

    for s in routes:
        seg = (s["x1"], s["y1"], s["x2"], s["y2"])
        half = (s.get("w") or 6) / 2
        L = s["layer"]
        for p in pads:
            if p["net"] == s["net"]:
                continue
            if not ((p["layer"] in (L, 12)) or G.hole_dia(p)):
                continue
            hw, hh = G.pad_rect(p)
            d = G.seg_rect_dist(seg, p["x"], p["y"], hw, hh)
            if d < half + R.clr_tp - MARGIN:
                bad.append(f"seg {s['net']} L{L} vs pad {p['net']}:{p['num']} d={d:.2f}")
        for t in tracks:
            if t["net"] == s["net"] or t["layer"] != L:
                continue
            d = G.seg_seg_dist(seg, (t["x1"], t["y1"], t["x2"], t["y2"]))
            if d < half + (t.get("w") or 6) / 2 + R.clr_tt - MARGIN:
                bad.append(f"seg {s['net']} L{L} vs trk {t['net']} d={d:.2f}")
        for v in board_vias:
            if v["net"] == s["net"]:
                continue
            d = G.seg_pt_dist(*seg, v["x"], v["y"])
            if d < half + (v.get("d") or R.via_d) / 2 + R.clr_via - MARGIN:
                bad.append(f"seg {s['net']} L{L} vs via {v['net']} d={d:.2f}")
        # 基板縁
        for (x, y) in ((s["x1"], s["y1"]), (s["x2"], s["y2"])):
            if (x < G.BOARD[0] + R.edge + half - MARGIN or x > G.BOARD[1] - R.edge - half + MARGIN or
                    y > G.BOARD[3] - R.edge - half + MARGIN or y < G.BOARD[2] + R.edge + half - MARGIN):
                bad.append(f"seg {s['net']} near board edge ({x:.0f},{y:.0f})")
        # キープアウト
        for (kx0, kx1, ky0, ky1, kls) in G.KEEPOUTS:
            if L not in kls:
                continue
            for t01 in (0.0, 0.25, 0.5, 0.75, 1.0):
                x = s["x1"] + (s["x2"] - s["x1"]) * t01
                y = s["y1"] + (s["y2"] - s["y1"]) * t01
                if kx0 - half < x < kx1 + half and ky0 - half < y < ky1 + half:
                    bad.append(f"seg {s['net']} in keepout ({x:.0f},{y:.0f})")
                    break

    for nv in vias:
        r = (nv.get("d") or R.via_d) / 2
        for p in pads:
            hw, hh = G.pad_rect(p)
            if p["net"] != nv["net"]:
                dx = max(abs(nv["x"] - p["x"]) - hw, 0)
                dy = max(abs(nv["y"] - p["y"]) - hh, 0)
                if math.hypot(dx, dy) < r + R.clr_via - MARGIN:
                    bad.append(f"via {nv['net']} vs pad {p['net']}:{p['num']}")
            hd = G.hole_dia(p)
            if hd and p["net"] != nv["net"]:
                if math.hypot(nv["x"] - p["x"], nv["y"] - p["y"]) < hd / 2 + R.clr_hole + r - MARGIN:
                    bad.append(f"via {nv['net']} vs HOLE {p['net']}:{p['num']}")
        for t in tracks:
            if t["net"] == nv["net"]:
                continue
            d = G.seg_pt_dist(t["x1"], t["y1"], t["x2"], t["y2"], nv["x"], nv["y"])
            if d < r + (t.get("w") or 6) / 2 + R.clr_via - MARGIN:
                bad.append(f"via {nv['net']} vs trk {t['net']} d={d:.2f}")
        for v in board_vias:
            if v["net"] == nv["net"]:
                continue
            d = math.hypot(nv["x"] - v["x"], nv["y"] - v["y"])
            if d < r + (v.get("d") or R.via_d) / 2 + R.clr_via - MARGIN:
                bad.append(f"via {nv['net']} vs via {v['net']} d={d:.2f}")
        for (kx0, kx1, ky0, ky1, _kls) in G.KEEPOUTS:  # ビアは全層貫通なので層無関係
            if kx0 - r < nv["x"] < kx1 + r and ky0 - r < nv["y"] < ky1 + r:
                bad.append(f"via {nv['net']} in keepout")

    # 新規同士 (異ネット)
    for i, a in enumerate(routes):
        for b in routes[i + 1:]:
            if a["net"] == b["net"] or a["layer"] != b["layer"]:
                continue
            d = G.seg_seg_dist((a["x1"], a["y1"], a["x2"], a["y2"]),
                               (b["x1"], b["y1"], b["x2"], b["y2"]))
            if d < (a.get("w", 6) + b.get("w", 6)) / 2 + R.clr_tt - MARGIN:
                bad.append(f"newseg {a['net']} vs newseg {b['net']} d={d:.2f}")
    for i, a in enumerate(vias):
        ra = (a.get("d") or R.via_d) / 2
        for b in vias[i + 1:]:
            rb = (b.get("d") or R.via_d) / 2
            d = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
            need = (ra + rb) if a["net"] == b["net"] else (ra + rb + R.clr_via)
            if 0 < d < need - MARGIN:
                bad.append(f"newvia {a['net']} vs newvia {b['net']} d={d:.2f}")
        for s in routes:
            if a["net"] == s["net"]:
                continue
            d = G.seg_pt_dist(s["x1"], s["y1"], s["x2"], s["y2"], a["x"], a["y"])
            if d < ra + (s.get("w") or 6) / 2 + R.clr_via - MARGIN:
                bad.append(f"newvia {a['net']} vs newseg {s['net']} d={d:.2f}")
    return bad


if __name__ == "__main__":
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument("routes_json")
    ap.add_argument("--profile", choices=list(G.PROFILES), default="design")
    args = ap.parse_args()
    r = json.load(open(args.routes_json))
    bad = check(r.get("routes", []), r.get("vias", []), profile=args.profile)
    for b in bad[:30]:
        print("VIOLATION:", b)
    print(f"violations: {len(bad)} | segs: {len(r.get('routes', []))} vias: {len(r.get('vias', []))}")
    sys.exit(1 if bad else 0)
