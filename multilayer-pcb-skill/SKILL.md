---
name: multilayer-pcb-skill
description: >-
  Multilayer (4/6/8-layer) HDI PCB development skill for EasyEDA Pro + JLCPCB. Use when routing
  dense boards (fine-pitch QFN/BGA, 0.35mm pitch, stacked connectors), converting 2-4 layer
  designs to 6/8 layers, planning layer stacks and GND planes, escaping fine-pitch pad columns
  (fanout), using micro vias / HDI rules, integrating external autorouters (KiCadRoutingTools),
  rebuilding copper pours, GND stitching, or recovering EasyEDA cloud projects from data loss.
  Trigger on: "多層基板", "8層", "6層", "multilayer", "HDI", "マイクロビア", "micro via", "fanout", "ファンアウト",
  "層スタック", "layer stack", "GNDプレーン", "内層", "inner layer", "escape routing".
---

# 多層基板開発スキル (EasyEDA Pro + JLCPCB)

30×30mm・8層・ESP32-P4(0.35mmピッチQFN 114ピン)+30ピンスタックコネクタ基板を
全60ネット手動/半自動で結線完了した実戦から抽出した方法論。

## 0. 大原則

1. **オートルータに丸投げしない**。密集基板の勝敗はアルゴリズムではなく
   「配置 → ファンアウト → 配線可能領域 → 層数」の順で決まる。
   電源・GND・クロック・差動・USBは人間(または決定論スクリプト)が先に引く。
2. **検証は自前のオフラインパイプラインが真実源**。アプリのDRCは再起動直後以外
   ステイルになる(EasyEDA Pro)。ジオメトリをJSONにエクスポートし、
   接続性(カプセル重なり)とクリアランスを自前で監査する。
3. **適用前検証ゲート(validate-before-apply)を絶対に飛ばさない**。
   未検証の手動セグ1本が数時間の手戻りになる(実績あり)。
4. **編集のたびに保存し、重要マイルストーンでは保存→再起動→再検証**。
   クラウドEDAは「保存成功の返値」と「実際に永続化された内容」がズレることがある。

## 1. 層スタック設計

| 層数 | 推奨構成 | JLCPCB仕様 |
|---|---|---|
| 4層 | S-G-P-S | standard: 3.5/3.5mil, via 0.3/0.45 |
| 6層 | S-G-S-S-P-S | standard 4-layer+ rules |
| 8層 | **S-G-S-S-S-S-G-S** | advanced HDI: 3/3mil, via 0.25/0.15, μvia可 |

- 8層のプレーンは **In1(L15)とIn6(L20)** に置き、L1/L2(外層)+In2-In5(L16-19)の6層を配線に使う。
- 外層ベタ(L1/L2 GND)は最後に張る。配線中は**ベタを一旦削除**して自由度を確保し、
  完了後に復元+ソリッド指定+再構築(EasyEDA: Shift+B)。
- EasyEDA Proの層番号: L1=Top, L2=Bottom, L15-20=Inner1-6, L11=外形, L12=マルチレイヤ。
  層数変更は `pcb_Layer.setTheNumberOfCopperLayers(8)`。

## 2. ファインピッチQFNの脱出(エスケープファースト)

0.35mmピッチ(13.78mil)ではパッド間をビアは通れず、6milトラック1本だけが通る。
**「先にビアへ逃がし、内層で運ぶ」**が唯一の解:

1. **スタブ+ビア列**: パッド列に平行な「ビア列」を複数定義(例: 東列に対して
   W/A/B/E1/E2/E3の6列)し、各パッドから短いスタブでビアへ。
2. **候補生成→ペア互換行列→DFS割当**: 各パッド×各列×±ジョグの全候補を
   実ルールで事前検証し、候補間の相互干渉(セグ-セグ10mil, ビア-ビア30mil,
   ビア-セグ21mil)を行列化してからバックトラッキングDFSで一括割当。
   逐次貪欲では後半が必ず詰む。18パッド同時割当の実績あり。
3. **入れ子レーン(nested lanes)**: 一列のパッド群を側方へ運ぶときは
   「西端パッド=最浅レーン、東へ行くほど深いレーン、ダイブ列も同順」で
   交差ゼロの入れ子を組む。レーンピッチは10.05mil(6mil線+4.05間隙)。
4. **隠れチャネルを探す**: サーマルパッドとパッド列の間(実測18mil幅)のような
   「ビア1個がぎりぎり入る溝」が勝負を決める。パッド形状の実寸
   (hw/hh)をAPIから取得して機械的に窓を計算する。

## 3. 幾何トポロジの落とし穴(実戦で全部踏んだ)

- **コネクタのパッド層を確認せよ**: 底面SMDコネクタ(L2)のパッドはL1トラックを
  一切ブロックしない(逆も然り)。「壁」に見えるものの半分は別層で消える。
- **USB-Cのピン交互配置(B6 A7 A6 B7)**: A7-B7橋とB6-A6橋は同一層で必ず交差する。
  解は (a)コネクタ直下を通す (b)層ホップ (c)マイクロビア。
- **サーマルパッドは異ネットビア全面禁止**(295mil角ならその全域)。
  ただし同ネット(GND)のサーマルビアアレイは標準作法。内層に配線が走っていると
  そこもビア不可になるので、サーマルビアは**内層が埋まる前に**打つ。
- **丸パッド/角丸パッドを矩形近似するな**: パッド角へ斜め進入する配線は
  実銅に0.3〜10mil届いていないことがある(130箇所の実績)。配線は必ず
  **パッド中心で終端**させる。接続判定は内接円(min(hw,hh))で行う。
- **THT円形パッドも同じ**: リング半径を超えた矩形角進入は未接続。
- **NPTH穴(コネクタ位置決めペグ・ネジ穴)は検証網から不可視**:
  EasyEDA Proでは `pcb_PrimitiveHole` プリミティブで、パッドベースの
  ジオメトリエクスポートに**乗らない**。ビアがペグ穴に重なったまま
  発注に至った実績あり(JLCのDFMで発覚。FBネットのビアだったら製造されて
  いれば全損級)。対策は2つ: ①エクスポート時にholeプリミティブも別途取得して
  障害物に加える ②発注直前にGerberドリルを解析する([`drillcheck.py`](scripts/drillcheck.py))。
- **キープアウトは「トラック禁止」と「ビア禁止」を別々に定義せよ**:
  L1トラックだけ塞いだキープアウトはビアを素通しにする。ソルバ/ファンアウト
  スクリプトの障害物モデルには、コネクタ下のNPTH・シェルスロット・THTリングを
  **全層ビア禁止**として明示的に入れる。

## 4. オフライン検証パイプライン(必須装備)

実装は [`scripts/`](scripts/) に同梱(使い方・JSONスキーマは [`scripts/README.md`](scripts/README.md))。
ジオメトリをJSON化([`scripts/export_geometry.js`](scripts/export_geometry.js))して以下を回す:

- **[`strict.py`](scripts/strict.py)**: カプセル重なり接続判定でネットごとの島を数える。
  0島差=結線完了。パッド接触は角丸近似(シュリンク矩形)で判定 —
  丸パッドの矩形近似による「角進入の隠れ未接続」を検出する。
- **[`validate.py`](scripts/validate.py)**: 新規銅の適用前監査。設計規準(4.05/6mil)と
  製造規準(JLC 3.5mil)の2プロファイル(`--profile jlc`)を持ち、最後の数ネットだけ
  製造規準に落として通す(局所的な規準緩和は発注仕様に明記)。
- **[`audit.py`](scripts/audit.py)**: 全盤面クリアランス監査+穴間隙+基板縁+キープアウト。
- **[`spots.py`](scripts/spots.py)**: 1mil格子でビア可能座標を全列挙(スラック付き、
  `--via micro`対応)。「ビアをどこに置けるか」を人間の目視でなく機械で決める。
- **[`drillcheck.py`](scripts/drillcheck.py)**: **発注に使うGerber zipそのもの**の
  Excellonドリル(NPTH/PTH/Via)を解析し、穴同士の重なり・近接を総当たり判定。
  設計データでなく製造データを見る最終防衛線 — NPTH穴のエクスポート漏れ、
  古いGerberの取り違えもここで捕まる。発注前の必須ステップ。
- 基板固有設定(外形・キープアウト・配線層)は [`scripts/geom.py`](scripts/geom.py) 冒頭で定義。
  ビア径は可変で扱う: 標準24/12mil、マイクロ9.84/5.91mil(0.25/0.15mm)。

## 5. 外部オートルータ連携

- **Freerouting(DSN/SES往復)はEasyEDA Proと相性が悪い**: DSN出力の配線パスが
  数値層IDでレイヤ定義と不整合になり、既存配線を認識できず fanout暴走する。
- **KiCadRoutingTools(drandyhaas)が実用解**:
  1. ジオメトリJSONから .kicad_pcb を自作生成(単一ダミーfootprint+絶対座標パッド、
     既存銅は `(locked yes)` で不可侵、プレーン層はkeepout zoneで保護)
  2. `route.py in.kicad_pcb out.kicad_pcb --nets 残ネット... --keep-input-copper`
  3. 差分(新規segment/via)を抽出し、**自前validateゲートを通してから**EDAに適用
- 勝ち筋は「ターミナルエスカレーション」= 幅3mil化+0.25/0.15mmマイクロビアの
  パッド内打ち。交互配置・位相封鎖など手動で詰んだトポロジをこれが解く。
- Rustコアは `build_router.py` でプリビルト取得可(macOS arm64対応、Python≥3.9)。

## 6. ベタ(ポア)と GNDスティッチング

- ベタ復元時の作成APIはfillMethod指定が効かず90gridになる →
  作成後に `setState_PourFillMethod("solid")` + done() で必ずソリッド化。
- `preserveSilos=true`(孤島保持)は接続エラーを激増させる。孤島は除去し、
  届かないパッドは**ビア/リンクで能動的に繋ぐ**:
  - SMD GNDパッドはパッド内ビア(in-pad via)が第一選択。
  - ビアが入らない密集部は同層の短いリンクセグで最寄りGND銅へ。
  - サーマルパッドには3×3程度のビアアレイ(内層空きスポットをspots.pyで探す)。
- ベタの流し込み間隔(Copper Zone spacing)を0.254→0.152mmに絞ると
  密集部への到達が改善する(JLC許容内)。
- 再構築はShift+B。**DRCのConnection Errorはベタ再構築後に再実行**して読む。

## 7. EasyEDA Pro 多層固有の運用知見

- DRCルールの一括書換: `pcb_Drc.getCurrentRuleConfiguration()` で取得し、
  数値を書き換えて `overwriteCurrentRuleConfiguration(cfg.config)`
  (**config単体を渡す**。{name,config}丸ごとはfalse)。
- Spacing行列はmm単位。HDI移行時は 0.152/0.102→0.0889、線幅0.0762、
  ビア0.25/0.15 に更新してからDRCを回す。
- メニュー操作が必要なもの(ベタ再構築、履歴復元)はCDPの
  `Input.dispatchMouseEvent/KeyEvent`(信頼済み入力)で自動化できる。
  合成DOM clickは効かない。`Page.captureScreenshot`で画面確認。
- **データ喪失からの復旧**: File → Historical Records → 日時選択 → Restore。
  クラウド履歴は保存時点ごとに残っている。`getAll()`が突然0を返す
  「ウェッジ状態」になったら**保存せず即再起動**(ウェッジ中の保存が
  全銅箔消失を引き起こした実績あり)。

## 8. 発注前チェックリスト(多層固有)

- [ ] 全ネット結線: strict.py(内接円判定)とアプリDRCの両方で0
- [ ] クリアランス監査0(製造規準プロファイル)。ウェーバは座標と理由を文書化
- [ ] ベタ: ソリッド・再構築済み・GND未接続パッド0(または文書化)
- [ ] 層数・スタック・ビア仕様(標準/マイクロ)をJLC発注画面と一致させる
  (8層HDI+0.25/0.15mmビアは advanced/HDI プロセス指定が必要)
- [ ] インピーダンス管理が要る場合はJLC標準スタックの層厚で線幅を決めてから配線
- [ ] Gerber再出力は**最終編集後**に行う(古いGerber誤発注の実績あり)
- [ ] **出力したGerberのドリルを drillcheck.py で総当たり検査**(NPTH×PTH/Via重なり0)。
  設計側検証が全部通っていてもNPTH起因の重なりはここでしか捕まらない(実績あり)
- [ ] 出荷仕様書に: 最小線幅、最小間隙、最小ビア、層数、板厚、銅厚を明記

## 8.5 製造DFM指摘への対応(穴重なり編)

JLCから「non-plated hole overlaps plated hole, can we proceed?」が来たら:

1. **Gerberドリルから重なり座標と径を特定**(drillcheck.pyの出力そのまま)
2. **重なった側のメッキ穴のネットと回路上の役割を設計データで確認**:
   - GNDスティッチングビアの1本 → 冗長なので「proceed」で可
   - **単一経路の信号/帰還ビア(レギュレータFB、クロック等)→ Confirm絶対禁止**。
     NPTHドリルがビアバレルを切断=断線。FB開放なら出力暴走で下流全損
3. PCBA注文はファイル差し替え不可 → **cancel for refund → 修正 → 再発注**が正道
4. 再発注時はプロセス指定(8層advanced/HDI、最小ビア0.15/0.25mm等)を**再選択**する
   (新規注文では引き継がれない)

## 9. 反省から得た設計ルール(次の基板でやるべきこと)

- 0.35mmピッチ部品の隣に幅広パッド(MIPI等)を置くと、その間のピンは
  物理的に脱出不能になり得る。**配置段階でエスケープ幅を検算**する。
- 裏面デカップリングキャパ列をIC(サーマルパッド)の真下に置かない。
  ビア禁止シャドウと重なると接続手段が消える。
- スタックコネクタのGNDピンは、内層が埋まる前にビアを打っておく。
- 30mm角に60ネット+8層は成立するが、31-32mm角にするだけで
  工数が1/5になる。サイズ制約は本当に必要か最初に問う。
