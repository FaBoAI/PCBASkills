// EasyEDA Pro ジオメトリエクスポート (ページコンテキストで実行する async 関数本体)
//
// 実行方法: easyeda-api ブリッジ、または CDP 直結
//   (Runtime.evaluate で `(async () => { const eda = window.eda; <このコード> })()`)
// 出力: window.__geom に {pads, tracks, vias} を格納。
//   CDP応答は64KBで切れるため、window.__geom を JSON.stringify して
//   60KB程度ずつ slice で分割読み出しし、ホスト側で geom_pads.json /
//   geom_tracks.json に保存する。
//
// 大量プリミティブは 150-200件/呼び出しでチャンクすること(ブリッジ30sタイムアウト対策)。

const pads = [];
for (const id of await eda.pcb_PrimitivePad.getAllPrimitiveId()) {
  const p = await eda.pcb_PrimitivePad.get(id);
  if (!p) continue;
  pads.push({
    id,
    num: p.getState_PadNumber ? String(p.getState_PadNumber()) : "?",
    layer: p.getState_Layer(),
    x: p.getState_X(), y: p.getState_Y(),
    rot: p.getState_Rotation ? p.getState_Rotation() : 0,   // CDP経由はラジアンのことがある
    pad: p.getState_Pad ? p.getState_Pad() : null,          // [shape, w, h, ...]
    net: p.getState_Net(),
    hole: p.getState_Hole ? p.getState_Hole() : null,       // [type, dia] | null
  });
}

const tracks = [];
for (const id of await eda.pcb_PrimitiveLine.getAllPrimitiveId()) {
  const l = await eda.pcb_PrimitiveLine.get(id);
  if (!l) continue;
  tracks.push({
    id, layer: l.getState_Layer(), net: l.getState_Net(),
    x1: l.getState_StartX(), y1: l.getState_StartY(),
    x2: l.getState_EndX(),   y2: l.getState_EndY(),
    w: l.getState_LineWidth ? l.getState_LineWidth() : 6,
  });
}

const vias = [];
for (const v of await eda.pcb_PrimitiveVia.getAll()) {
  vias.push({
    id: v.getState_PrimitiveId(), net: v.getState_Net(),
    x: v.getState_X(), y: v.getState_Y(),
    // 径は固定値と思い込まない — 実径を取得(マイクロビア混在基板で必須)
    d: v.getState_Diameter ? v.getState_Diameter() : 24,
    hole: v.getState_HoleDiameter ? v.getState_HoleDiameter() : 12,
  });
}

window.__geom = { pads, tracks, vias };
return { pads: pads.length, tracks: tracks.length, vias: vias.length };
