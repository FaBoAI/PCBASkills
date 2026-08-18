#!/usr/bin/env python3
"""共有ジオメトリライブラリ (多層基板検証パイプライン)

入力: EasyEDA Pro からエクスポートしたジオメトリJSON (export_geometry.js 参照)
  geom_pads.json   : [{id, num, layer, x, y, rot, pad:[shape,w,h,...], net, hole:[type,dia]|null}]
  geom_tracks.json : {tracks:[{id, layer, net, x1,y1,x2,y2, w}], vias:[{id, net, x, y, d, hole}]}
単位は mil、y は下向き負 (EasyEDA Pro 座標系)。

ルールは RuleProfile で切替:
  design : 設計規準 (track-track 4.05 / track-pad 6.0 / via系 6.0)
  jlc    : JLCPCB advanced 製造規準 (全 3.5, 穴→銅 6.93)
"""
import json, math, os
from dataclasses import dataclass


@dataclass
class RuleProfile:
    clr_tt: float      # track-track
    clr_tp: float      # track-pad
    clr_via: float     # via-track / via-pad / via-via
    clr_hole: float    # ドリル縁→異ネット銅
    edge: float        # 基板縁クリアランス
    via_d: float = 24.0
    via_hole: float = 12.0


PROFILES = {
    "design": RuleProfile(clr_tt=4.05, clr_tp=6.0, clr_via=6.0, clr_hole=6.93, edge=11.8),
    "jlc":    RuleProfile(clr_tt=3.5,  clr_tp=3.5, clr_via=3.5, clr_hole=6.93, edge=11.8),
}

# --- 基板固有設定 (プロジェクトごとにここを書き換える) -----------------------
BOARD = (0.0, 1181.1, -1181.1, 0.0)   # xmin, xmax, ymin, ymax [mil]
KEEPOUTS = [                           # (x0, x1, y0, y1, layers) 配線禁止領域
    # 例: USBコネクタ下 L1禁止: (455.0, 725.0, -200.0, -45.0, (1,))
]
LAYERS = [1, 2, 16, 17, 18, 19]        # 配線層 (プレーン層は含めない)
# ---------------------------------------------------------------------------


def load(dirpath="."):
    """ジオメトリJSONを読み込む。返値: (pads, tracks, vias)"""
    pads = json.load(open(os.path.join(dirpath, "geom_pads.json")))
    if isinstance(pads, dict):
        pads = pads["result"]
    tk = json.load(open(os.path.join(dirpath, "geom_tracks.json")))
    if "result" in tk:
        tk = tk["result"]
    return pads, tk["tracks"], tk["vias"]


def pad_rect(p):
    """回転考慮のパッド実効 half-w / half-h。POLYGONはbbox、ラジアン/度は自動判別"""
    shape = p["pad"][0] if p.get("pad") else "RECT"
    if shape == "POLYGON":
        xs = [v for v in p["pad"][1] if isinstance(v, (int, float))]
        px, py = xs[0::2], xs[1::2]
        return (max(px) - min(px)) / 2.0, (max(py) - min(py)) / 2.0
    w = p["pad"][1] if len(p["pad"]) > 1 else 10
    h = p["pad"][2] if len(p["pad"]) > 2 else w
    if not isinstance(h, (int, float)):
        h = w
    rot = p.get("rot") or 0
    if 0 < abs(rot) <= 6.3:            # CDP経由はラジアンで返ることがある
        rot = math.degrees(rot)
    rot = rot % 360
    if abs(rot - round(rot / 90) * 90) < 0.5:
        rot = (round(rot / 90) * 90) % 360
    if rot in (90, 270):
        w, h = h, w
    elif rot not in (0, 180):
        r = math.radians(rot)
        w, h = (abs(w * math.cos(r)) + abs(h * math.sin(r)),
                abs(w * math.sin(r)) + abs(h * math.cos(r)))
    return w / 2.0, h / 2.0


def pad_rin(p):
    """接続判定用の内接円半径。丸/角丸パッドを矩形近似しないための保守値"""
    hw, hh = pad_rect(p)
    return min(hw, hh)


def hole_dia(p):
    h = p.get("hole")
    return h[1] if isinstance(h, list) and len(h) > 1 else 0


def seg_pt_dist(x1, y1, x2, y2, px, py):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def seg_seg_dist(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    if _seg_intersect(a, b):
        return 0.0
    return min(seg_pt_dist(ax1, ay1, ax2, ay2, bx1, by1),
               seg_pt_dist(ax1, ay1, ax2, ay2, bx2, by2),
               seg_pt_dist(bx1, by1, bx2, by2, ax1, ay1),
               seg_pt_dist(bx1, by1, bx2, by2, ax2, ay2))


def _seg_intersect(a, b):
    def ccw(ax, ay, bx, by, cx, cy):
        return (cy - ay) * (bx - ax) - (by - ay) * (cx - ax)
    d1 = ccw(b[0], b[1], b[2], b[3], a[0], a[1])
    d2 = ccw(b[0], b[1], b[2], b[3], a[2], a[3])
    d3 = ccw(a[0], a[1], a[2], a[3], b[0], b[1])
    d4 = ccw(a[0], a[1], a[2], a[3], b[2], b[3])
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def seg_rect_dist(seg, cx, cy, hw, hh):
    """線分と軸平行矩形(中心cx,cy 半幅hw,hh)の距離。重なりは0"""
    x1, y1, x2, y2 = seg
    corners = [(cx - hw, cy - hh), (cx + hw, cy - hh), (cx + hw, cy + hh), (cx - hw, cy + hh)]
    edges = [(corners[i][0], corners[i][1], corners[(i + 1) % 4][0], corners[(i + 1) % 4][1])
             for i in range(4)]
    if _pt_in_rect(x1, y1, cx, cy, hw, hh) or _pt_in_rect(x2, y2, cx, cy, hw, hh):
        return 0.0
    for e in edges:
        if _seg_intersect(seg, e):
            return 0.0
    d = min(seg_pt_dist(*seg, px, py) for px, py in corners)
    for e in edges:
        d = min(d, seg_pt_dist(*e, x1, y1), seg_pt_dist(*e, x2, y2))
    return d


def _pt_in_rect(px, py, cx, cy, hw, hh):
    return abs(px - cx) <= hw and abs(py - cy) <= hh
