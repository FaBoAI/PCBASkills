# オフライン検証パイプライン スクリプト

SKILL.md §4 で説明している検証ツール群の実装。EasyEDA Pro からエクスポートした
ジオメトリJSONに対して、アプリのDRCに依存せず接続性とクリアランスを監査する。

## ワークフロー

```
EasyEDA Pro ──(export_geometry.js)──> geom_pads.json / geom_tracks.json
                                            │
        ┌───────────────┬──────────────┬────┴─────────┐
   strict.py        audit.py      validate.py      spots.py
   接続性(島数)     全盤面監査     適用前ゲート     ビア座標探索

発注用 Gerber zip ──> drillcheck.py   ドリル重なり検査(製造データの最終防衛線)
```

1. **エクスポート**: `export_geometry.js` をブリッジ/CDP でページ実行し、
   結果を `geom_pads.json` / `geom_tracks.json` に保存(64KB分割読みに注意)。
2. **設定**: `geom.py` 冒頭の `BOARD` / `KEEPOUTS` / `LAYERS` を基板に合わせる。
3. **検証**: 編集のたびに再エクスポート → 各ツールを実行。

## 各ツール

| スクリプト | 役割 | 使い方 |
|---|---|---|
| `geom.py` | 共有ライブラリ(JSON読込・パッド実寸・距離計算・ルールプロファイル) | import して使用 |
| `strict.py` | ネットごとの島数=接続性。**丸パッドは内接円で判定**(矩形近似の未接続見逃しを防ぐ) | `python3 strict.py [NET...]` |
| `validate.py` | 新規銅(routes.json)の適用前監査。既存全物+新規同士+縁+穴+キープアウト。違反1件でも適用禁止 | `python3 validate.py routes.json [--profile jlc]` |
| `audit.py` | 全盤面クリアランス監査(TT/TP/TV/VV/VP/穴/縁/キープアウト) | `python3 audit.py [--profile jlc]` |
| `spots.py` | bbox内のビア可能座標を1mil格子で全列挙(numpy、スラック付き) | `python3 spots.py x0 x1 y0 y1 [net] [--via micro]` |
| `drillcheck.py` | **Gerber zipのExcellonドリル**を解析し穴同士の重なりを総当たり判定。NPTH穴はジオメトリエクスポートに乗らないため、この検査だけが捕まえられる違反がある(発注前必須) | `python3 drillcheck.py Gerber.zip [--margin 0.5]` |

## ルールプロファイル (geom.py PROFILES)

- `design`: 設計規準 — track-track 4.05 / track-pad 6.0 / via系 6.0 mil
- `jlc`: JLCPCB advanced 製造規準 — 全 3.5 mil、穴→銅 6.93 mil

日常は `design` で回し、最後のどうしても通らない数ネットだけ `jlc` に落として
通す(緩和した箇所は発注仕様に明記する)。

## 入力JSONスキーマ

```jsonc
// geom_pads.json
[{"id":"...", "num":"1", "layer":1, "x":590.0, "y":-765.0, "rot":0,
  "pad":["RECT", 295.3, 295.3], "net":"GND", "hole":null}]
// layer 12 = マルチレイヤ(THT)。hole = ["ROUND", 直径] | null

// geom_tracks.json
{"tracks":[{"id":"...", "layer":1, "net":"SDA",
            "x1":0, "y1":0, "x2":10, "y2":0, "w":6}],
 "vias":  [{"id":"...", "net":"GND", "x":100, "y":-100, "d":24, "hole":12}]}
```

単位は mil、y は下向き負(EasyEDA Pro 座標系)。ビア径 `d` は実径を
エクスポートすること(標準24/マイクロ9.84が混在する基板で固定値を使うと
偽violationが出る)。

**注意**: NPTH穴(`pcb_PrimitiveHole` — コネクタ位置決めペグ、ネジ穴)は
このパッドエクスポートに**含まれない**。設計側で障害物に加えるか、最後に
`drillcheck.py` でGerberドリルを直接検査すること(こちらは単位mm、
EasyEDA ProがビアをPTHファイルにも重複出力する仕様への対処込み)。

## 依存

Python 3.9+ / numpy(spots.py のみ)
