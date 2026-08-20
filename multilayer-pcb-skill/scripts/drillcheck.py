#!/usr/bin/env python3
"""Excellonドリル総当たりチェッカ: 出力済みGerberの穴同士の重なりを検出する。

なぜ必要か(実戦の教訓):
  NPTH穴(コネクタ位置決めペグ等)は EasyEDA Pro では pcb_PrimitiveHole であり、
  パッドベースのジオメトリエクスポートに**一切乗らない**。つまり設計データ側の
  検証パイプライン(strict/validate/audit)からは不可視。実際にNPTHペグと
  レギュレータFBネットのビアが重なったままJLCPCBに発注され、DFM指摘で発覚した
  (製造されていたらFB開放=3.3V暴走で全損リスク)。
  最終防衛線として、**発注に使うGerber zipそのもの**のドリルファイルを解析し、
  全穴ペアの総当たり距離判定を行う。設計データではなく製造データを見るので、
  エクスポート漏れ・古いGerber・座標ズレも同時に検出できる。

対象ファイル(EasyEDA Pro命名):
  Drill_NPTH_Through.DRL      非メッキ穴(ペグ・ネジ穴)
  Drill_PTH_Through.DRL       メッキ貫通穴(THTピン・スロット)
  Drill_PTH_Through_Via.DRL   ビア

判定:
  異クラスペア(NPTH×PTH, NPTH×VIA, PTH×VIA)で
  中心距離 < r1 + r2 + margin を違反として報告。
  スロット(X..Y..G85X..Y..)は線分カプセルとして扱う。
  margin既定0 = 「物理的重なり」のみ。JLCの穴間隙規準で見るなら --margin 0.5 等。

注意(EasyEDA Proの罠): ビアは Drill_PTH_Through.DRL と
  Drill_PTH_Through_Via.DRL の**両方に重複出力**される。素朴にPTH×VIAを
  突き合わせると全ビアが偽陽性になるため、同座標・同径の穴はPTH側から
  除去してから判定する。

使い方:
  python3 drillcheck.py Gerber.zip              # zipを直接
  python3 drillcheck.py gerber_dir/             # 展開済みディレクトリ
  python3 drillcheck.py Gerber.zip --margin 0.5 # 穴縁間0.5mm未満も警告
終了コード: 違反0=0, 違反あり=1
"""
import io
import math
import re
import sys
import zipfile
from pathlib import Path

FILES = {
    "NPTH": "Drill_NPTH_Through.DRL",
    "PTH": "Drill_PTH_Through.DRL",
    "VIA": "Drill_PTH_Through_Via.DRL",
}
NUM = r"-?\d+\.?\d*"


def parse_excellon(text):
    """[(x1,y1,x2,y2,dia_mm)] を返す。丸穴は x1==x2, y1==y2。単位mm前提(METRIC)。"""
    tools, holes = {}, []
    cur = None
    for line in text.splitlines():
        line = line.strip()
        m = re.match(rf"T(\d+)C({NUM})", line)
        if m:
            tools[m.group(1)] = float(m.group(2))
            continue
        m = re.match(r"T(\d+)$", line)
        if m and m.group(1) in tools:
            cur = tools[m.group(1)]
            continue
        m = re.match(rf"X({NUM})Y({NUM})G85X({NUM})Y({NUM})", line)
        if m and cur:  # スロット
            holes.append((float(m.group(1)), float(m.group(2)),
                          float(m.group(3)), float(m.group(4)), cur))
            continue
        m = re.match(rf"X({NUM})Y({NUM})$", line)
        if m and cur:
            x, y = float(m.group(1)), float(m.group(2))
            holes.append((x, y, x, y, cur))
    return holes


def seg_seg_dist(a, b):
    """線分間最短距離(点は退化線分として扱える)"""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b

    def seg_pt(x1, y1, x2, y2, px, py):
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        t = 0 if L2 == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L2))
        return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

    # 交差判定は距離0扱いに含まれるので端点-線分4通りの最小で十分(凸カプセル)
    d = min(seg_pt(ax1, ay1, ax2, ay2, bx1, by1),
            seg_pt(ax1, ay1, ax2, ay2, bx2, by2),
            seg_pt(bx1, by1, bx2, by2, ax1, ay1),
            seg_pt(bx1, by1, bx2, by2, ax2, ay2))
    # 真の交差(端点最短では拾えない)を捕捉
    def ccw(ax, ay, bx, by, cx, cy):
        return (cy - ay) * (bx - ax) > (by - ay) * (cx - ax)
    if (ccw(ax1, ay1, bx1, by1, bx2, by2) != ccw(ax2, ay2, bx1, by1, bx2, by2) and
            ccw(ax1, ay1, ax2, ay2, bx1, by1) != ccw(ax1, ay1, ax2, ay2, bx2, by2)):
        return 0.0
    return d


def load(src):
    """srcはzipパス or 展開済みディレクトリ。{class: [holes]}を返す"""
    out = {}
    p = Path(src)
    if p.is_file() and p.suffix.lower() == ".zip":
        with zipfile.ZipFile(p) as z:
            names = {Path(n).name: n for n in z.namelist()}
            for cls, fn in FILES.items():
                if fn in names:
                    out[cls] = parse_excellon(
                        io.TextIOWrapper(z.open(names[fn]), "utf-8", errors="replace").read())
    else:
        for cls, fn in FILES.items():
            f = p / fn
            if f.exists():
                out[cls] = parse_excellon(f.read_text(errors="replace"))
    return out


def main():
    args = [a for a in sys.argv[1:]]
    margin = 0.0
    if "--margin" in args:
        i = args.index("--margin")
        margin = float(args[i + 1])
        del args[i:i + 2]
    if not args:
        print(__doc__)
        return 2
    data = load(args[0])
    if not data:
        print(f"ドリルファイルが見つからない: {args[0]}")
        return 2
    # EasyEDA ProはビアをPTHファイルにも重複出力する → 同座標・同径はPTHから除去
    if "PTH" in data and "VIA" in data:
        vset = {(round(v[0], 3), round(v[1], 3), round(v[4], 2)) for v in data["VIA"]}
        n0 = len(data["PTH"])
        data["PTH"] = [h for h in data["PTH"]
                       if (round(h[0], 3), round(h[1], 3), round(h[4], 2)) not in vset
                       or (h[0], h[1]) != (h[2], h[3])]
        dup = n0 - len(data["PTH"])
        if dup:
            print(f"(PTHファイル内のビア重複出力 {dup}穴 を除外)")
    for cls, holes in data.items():
        slots = sum(1 for h in holes if (h[0], h[1]) != (h[2], h[3]))
        print(f"{cls}: {len(holes)}穴 (うちスロット{slots})")

    pairs = [("NPTH", "PTH"), ("NPTH", "VIA"), ("PTH", "VIA")]
    bad = 0
    for ca, cb in pairs:
        if ca not in data or cb not in data:
            continue
        for a in data[ca]:
            for b in data[cb]:
                d = seg_seg_dist(a[:4], b[:4])
                gap = d - a[4] / 2 - b[4] / 2
                if gap < margin:
                    bad += 1
                    tag = "重なり" if gap < 0 else f"近接{gap:.3f}mm"
                    print(f"  NG {ca}({a[0]:.3f},{a[1]:.3f} d{a[4]:.2f}) × "
                          f"{cb}({b[0]:.3f},{b[1]:.3f} d{b[4]:.2f}) → {tag}")
    print(f"\n{'FAIL' if bad else 'CLEAN'}: 違反 {bad}件 (margin={margin}mm)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
