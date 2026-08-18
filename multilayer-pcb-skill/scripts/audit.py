#!/usr/bin/env python3
"""全盤面クリアランス監査 — アプリDRCに依存しない真実源。

盤上の全トラック/ビア/パッドを相互チェック:
  TT: track-track / TP: track-pad / TV: track-via / VV: via-via / VP: via-pad
  HOLE-T, HOLE-V: ドリル縁→異ネット銅 / EDGE: 基板縁 / KEEPOUT: 禁止領域

使い方:
  python3 audit.py                  # designプロファイル
  python3 audit.py --profile jlc    # 製造規準
違反リストは audit_result.json にも保存。
"""
import json, math, argparse
from collections import Counter
import geom as G

EPS = 0.15  # 実質マージン


def run(profile="design"):
    R = G.PROFILES[profile]
    pads, tracks, vias = G.load()
    bad = []
    from collections import defaultdict
    byL = defaultdict(list)
    for t in tracks:
        byL[t["layer"]].append(t)

    for L, ts in byL.items():
        for i, a in enumerate(ts):
            sa = (a["x1"], a["y1"], a["x2"], a["y2"])
            wa = (a.get("w") or 6) / 2
            for b in ts[i + 1:]:
                if a["net"] == b["net"]:
                    continue
                d = G.seg_seg_dist(sa, (b["x1"], b["y1"], b["x2"], b["y2"]))
                need = wa + (b.get("w") or 6) / 2 + R.clr_tt
                if d < need - EPS:
                    bad.append(("TT", a["net"], b["net"], round(d, 1), round(need, 1), a.get("id"), b.get("id")))

    for t in tracks:
        seg = (t["x1"], t["y1"], t["x2"], t["y2"])
        w = (t.get("w") or 6) / 2
        for p in pads:
            if p["net"] == t["net"]:
                continue
            if not ((p["layer"] in (t["layer"], 12)) or G.hole_dia(p)):
                continue
            hw, hh = G.pad_rect(p)
            d = G.seg_rect_dist(seg, p["x"], p["y"], hw, hh)
            if d < w + R.clr_tp - EPS:
                bad.append(("TP", t["net"], f"{p['net']}:{p['num']}", round(d, 1),
                            round(w + R.clr_tp, 1), t.get("id"), ""))

    for v in vias:
        r = (v.get("d") or R.via_d) / 2
        for t in tracks:
            if t["net"] == v["net"]:
                continue
            d = G.seg_pt_dist(t["x1"], t["y1"], t["x2"], t["y2"], v["x"], v["y"])
            need = r + (t.get("w") or 6) / 2 + R.clr_via
            if d < need - EPS:
                bad.append(("TV", t["net"], v["net"], round(d, 1), round(need, 1), t.get("id"), v.get("id")))
        for p in pads:
            if p["net"] == v["net"]:
                continue
            hw, hh = G.pad_rect(p)
            d = math.hypot(max(abs(v["x"] - p["x"]) - hw, 0), max(abs(v["y"] - p["y"]) - hh, 0))
            if d < r + R.clr_via - EPS:
                bad.append(("VP", v["net"], f"{p['net']}:{p['num']}", round(d, 1),
                            round(r + R.clr_via, 1), v.get("id"), ""))
    for i, a in enumerate(vias):
        for b in vias[i + 1:]:
            if a["net"] == b["net"]:
                continue
            d = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
            need = (a.get("d") or R.via_d) / 2 + (b.get("d") or R.via_d) / 2 + R.clr_via
            if d < need - EPS:
                bad.append(("VV", a["net"], b["net"], round(d, 1), round(need, 1), a.get("id"), b.get("id")))

    for p in pads:
        hd = G.hole_dia(p)
        if not hd:
            continue
        for t in tracks:
            if t["net"] == p["net"]:
                continue
            d = G.seg_pt_dist(t["x1"], t["y1"], t["x2"], t["y2"], p["x"], p["y"])
            need = hd / 2 + R.clr_hole + (t.get("w") or 6) / 2
            if d < need - EPS:
                bad.append(("HOLE-T", t["net"], f"{p['net']}:{p['num']}", round(d, 1), round(need, 1), t.get("id"), ""))
        for v in vias:
            if v["net"] == p["net"]:
                continue
            d = math.hypot(v["x"] - p["x"], v["y"] - p["y"])
            need = hd / 2 + R.clr_hole + (v.get("d") or R.via_d) / 2
            if d < need - EPS:
                bad.append(("HOLE-V", v["net"], f"{p['net']}:{p['num']}", round(d, 1), round(need, 1), v.get("id"), ""))

    xmin, xmax, ymin, ymax = G.BOARD
    for t in tracks:
        w = (t.get("w") or 6) / 2
        for (x, y) in ((t["x1"], t["y1"]), (t["x2"], t["y2"])):
            if x < xmin + R.edge + w - EPS or x > xmax - R.edge - w + EPS or \
               y > ymax - R.edge - w + EPS or y < ymin + R.edge + w - EPS:
                bad.append(("EDGE", t["net"], "", 0, 0, t.get("id"), ""))
                break
    for v in vias:
        r = (v.get("d") or R.via_d) / 2
        if v["x"] < xmin + R.edge + r - EPS or v["x"] > xmax - R.edge - r + EPS or \
           v["y"] > ymax - R.edge - r + EPS or v["y"] < ymin + R.edge + r - EPS:
            bad.append(("EDGE-V", v["net"], "", 0, 0, v.get("id"), ""))

    for (kx0, kx1, ky0, ky1, kls) in G.KEEPOUTS:
        for t in tracks:
            if t["layer"] not in kls:
                continue
            for (x, y) in ((t["x1"], t["y1"]), (t["x2"], t["y2"]),
                           ((t["x1"] + t["x2"]) / 2, (t["y1"] + t["y2"]) / 2)):
                if kx0 < x < kx1 and ky0 < y < ky1:
                    bad.append(("KEEPOUT", t["net"], "", 0, 0, t.get("id"), ""))
                    break
        for v in vias:
            if kx0 < v["x"] < kx1 and ky0 < v["y"] < ky1:
                bad.append(("KEEPOUT-V", v["net"], "", 0, 0, v.get("id"), ""))
    return bad


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=list(G.PROFILES), default="design")
    args = ap.parse_args()
    bad = run(args.profile)
    print("TOTAL:", len(bad))
    print("by type:", dict(Counter(b[0] for b in bad)))
    cnet = Counter(b[1] for b in bad)
    for n, c in cnet.most_common(15):
        print(f"  {n}: {c}")
    json.dump([list(b) for b in bad], open("audit_result.json", "w"))
