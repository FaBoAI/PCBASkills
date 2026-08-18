# PCBASkills

**EasyEDA Pro のための Claude Code SKILLS 集**

EasyEDA Pro + JLCPCB での基板開発(設計・配線・製造データ生成・発注・実機ブリングアップ)を
AIエージェントで自動化するためのスキル集です。実際の基板開発プロジェクトで蓄積した
実戦知見(API の罠、DFM 対応、復旧手順など)をスキルとして体系化しています。

## 収録スキル

| スキル | 内容 |
|---|---|
| [pcba-skill](pcba-skill/) | EasyEDA + JLCPCB PCBA 開発の汎用スキル。部品置換・在庫対応、EasyEDA Pro API 実戦ノート、配線前デザインレビュー、リップアップ&リルート、GND ベタ/スティッチングビア修復、BOM/PnP/Gerber 生成、DFM メール対応、実機ブリングアップ診断(LCD 色反転・I2S 無音)まで |
| [multilayer-pcb-skill](multilayer-pcb-skill/) | 多層(4/6/8層)HDI 基板開発スキル。層スタック設計、ファインピッチ QFN のエスケープファースト配線、マイクロビア/HDI ルール、外部オートルータ連携(KiCadRoutingTools)、ベタ運用と GND スティッチング、クラウドプロジェクトのデータ喪失復旧 |

## 使い方 (Claude Code)

スキルを `~/.claude/skills/` に配置すると、Claude Code が文脈に応じて自動で読み込みます:

```bash
git clone https://github.com/FaBoAI/PCBASkills.git
cp -R PCBASkills/pcba-skill PCBASkills/multilayer-pcb-skill ~/.claude/skills/
```

スラッシュコマンドとして明示的に呼び出すこともできます:

```
/pcba-skill 在庫切れのC25744を代替品に置換して
/multilayer-pcb-skill 6層化してQFNのファンアウトを設計して
```

## 各スキルの構成

```
pcba-skill/
├── SKILL.md              # スキル本体(トリガー条件 + ワークフロー + API知見)
└── references/           # 必要時に読み込むトピック別リファレンス
    ├── pcb-order-checklist.md
    ├── arduino-uno-layout.md
    ├── enclosure-3d-print.md
    └── display-fpc.md

multilayer-pcb-skill/
├── SKILL.md
└── scripts/              # オフライン検証パイプライン実装
    ├── README.md         # ワークフロー・JSONスキーマ
    ├── export_geometry.js
    ├── geom.py           # 共有ライブラリ + ルールプロファイル
    ├── strict.py         # 接続性(島数)チェッカ
    ├── validate.py       # 適用前検証ゲート
    ├── audit.py          # 全盤面クリアランス監査
    └── spots.py          # ビア可能座標の全列挙
```

## 前提環境

- [EasyEDA Pro](https://pro.easyeda.com/)(デスクトップ版)
- スキル内の API 操作は EasyEDA Pro の拡張 API / CDP(Chrome DevTools Protocol)経由で実行
- 製造・実装は [JLCPCB](https://jlcpcb.com/) を想定(Basic/Extended 部品、Standard/Advanced PCBA、HDI プロセス)

## License

MIT
