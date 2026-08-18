# EasyEDA/JLCPCB PCBA Checklist

Use this reference when making concrete EasyEDA/JLCPCB changes. It captures common failure modes seen in Arduino UNO-compatible PCBA ordering.

## Component Substitution

For each shortage row:

- Confirm designator, role, value, package, footprint, and quantity.
- Search current JLCPCB stock. Prefer official JLCPCB part detail pages and the fresh quote table.
- Choose a replacement with enough stock for the quote quantity and loss count.
- Verify assembly type: SMT, wave soldering, through-hole, or manual assembly as needed.
- Verify package and footprint compatibility before reusing the footprint.
- Verify passive values by units and manufacturer code, not by a visually similar part number.
  - USB-C CC pull-downs must be 5.1k ohm.
  - Example pitfall: `0603WAF510KT5E` / `C25197` is 5.1 ohm, while `0603WAF5101T5E` / `C23186` is 5.1k ohm.
- Replace all BOM-relevant fields:
  - `Supplier Part`
  - `Manufacturer`
  - `Manufacturer Part`
  - `JLCPCB Part Class`
  - `Datasheet`
  - part name/description fields when present
  - supplier footprint metadata when present
- After replacement, regenerate BOM and confirm:
  - `containsNew == true`
  - `containsOld == false`
  - manufacturer part number is the new one
- After modifying a component `Value`, check the EasyEDA log and component object again. EasyEDA can automatically clear `Supplier Part` when value changes.
- Verify replacement fields in both PCB and schematic component objects:
  - `supplier`
  - `supplierId`
  - `manufacturer`
  - `manufacturerId`
  - `name`
  - `otherProperty.Value`
  - `otherProperty.JLCPCB Part Class`
  - `otherProperty.Supplier Footprint`
  - `addIntoBom`

Do not trust a visible quote page if it was opened before the latest replacement. Stale quote URLs can keep showing old shortages.

### Stock realities (audit beyond the flagged row)

- Audit EVERY assembled part, not just the row JLC flagged. Standard passives (10k/100k 0402, 100nF/1µF/10µF MLCC) are JLC **Basic** and always stocked; odd/precise values are often **Extended** and thin (e.g. 191Ω 0402 `C25085` had 3 in stock and failed). For a non-critical role, swap an odd value to the nearest **Basic** value (191Ω→100Ω `C25076`), same footprint = supplier-only swap.
- **Modules are consign-only at JLC (0 assembly stock) and no LCSC part swap fixes it** — every listing of the same module shares empty inventory. All 0-stock: XIAO ESP32-S3 `C20467913`, `C9900154951`, XIAO ESP32-C3 `C19189385`; Raspberry Pi Pico likewise. Keep the module in the BOM (correct C-number, `addIntoBom=true`) so it lists as a consign/shortfall line; the user consigns or hand-solders.
- `C9900…` parts are EasyEDA-internal / "JLCPCB Assembly" listings — may resolve for consignment or show "No Part Selected". Prefer a real-manufacturer C-number.
- **12×12mm tact switches (THT and SMD) are all consign-only/0-stock.** In-stock tacts are 6–7.5mm SMD (e.g. GT-TC155C `C5155558`); for big buttons use small SMD + oversized caps in the enclosure.
- Verify stock per candidate via `WebFetch https://jlcpcb.com/partdetail/Cxxxx`; the EasyEDA search API and LCSC pages don't give reliable stock.

### CH340C To CH340G

Use this pattern when `CH340C` is unavailable or stale in JLCPCB/LCSC data:

- Verify current stock for the exact CH340C supplier part. Some CH340C pages can point to an alternate while the SMT page still reports zero stock.
- `CH340G` can be a practical replacement only if the PCB adds the oscillator circuit. Do not treat it as a drop-in BOM-only change.
- Use `CH340G / C14267` with an external 12 MHz crystal such as `X322512MMB4SI / C50430` and two 22 pF load capacitors such as `CL10C220JB8NNNC / C1653`, subject to current stock.
- Confirm the PCB net map:
  - pin 1: `GND`
  - pin 2: `D0_RX`
  - pin 3: `D1_TX`
  - pin 4: `CH340_V3`
  - pin 5: `USB_DP_CH340`
  - pin 6: `USB_DN_CH340`
  - pin 7: `CH340_XI`
  - pin 8: `CH340_XO`
  - pin 13: `DTR`
  - pin 16: `+5V`
- Keep the oscillator traces short, but do not route blindly across existing VIN, A4/A5, UART, or USB tracks. Run DRC after every oscillator placement attempt.

## Arduino UNO-Compatible Header Checks

- `POWER` header: use intended single-row 1x8, not 2x4.
- `DIGITAL D0-D7`: use intended single-row 1x8, not 2x4.
- `DIGITAL D8-D13/SDA/SCL`: use intended single-row 1x10, not 2x5.
- `ANALOG A0-A5`: use intended single-row 1x6.
- ICSP: use 2x3 header with normal height.
- Avoid long-tail female headers unless the user explicitly wants long pins.
- Confirm 3D/part photo when there is any doubt about height or pin length.

## USB Connector Checks

- Use a stocked JLCPCB USB connector with a matching EasyEDA footprint.
- Remove old USB footprint remnants before placing the new one.
- Place USB at the board edge the user requested.
- For the established left-edge placement pattern:
  - Connector faces left.
  - Connector mouth/nose is flush with the left Board Outline boundary.
  - Connector is vertically centered on the board.
- Check all USB pads route or connect through named nets:
  - VBUS/+5V
  - GND
  - D+
  - D-
  - CC1/CC2 pull-downs for USB-C when applicable
- Check D+/D- series resistors are present and connected.

## Board Outline And Layout

- Draw board boundary only on the Board Outline layer.
- Ensure the outline is a single closed rectangle polygon/polyline on the Board Outline layer, not four separate line primitives.
- When using the EasyEDA API, create a closed polygon first and place it as a polyline on the Board Outline layer. Verify old independent outline line primitives are deleted.
- Inspect the final outline primitive: exactly one closed outline polygon/polyline should remain on the Board Outline layer.
- Align edge-mounted parts to the outline, not merely near it.
- Resolve visible component overlaps before routing.
- Preserve requested silkscreen labels and keep them on a silkscreen layer.

## EasyEDA API Pitfalls

- After board copying or deletion, list all boards, schematics, and PCBs. EasyEDA may create `Board5_1`-style names and may leave orphan documents with old names.
- If a document rename returns `false`, check for stale orphan documents with the target name. Delete only documents known to be generated by the current task, then retry the rename.
- Some enum globals are unavailable in bridge-executed code. Use numeric constants from the docs when needed:
  - Top Layer: `1`
  - Bottom Layer: `2`
  - Top Silkscreen: `3`
  - Board Outline: `11`
  - normal via type: `0`
  - center string alignment: `5`
- For newly created PCB components, do not assume the immediate return object has persisted designator/name/manufacturing fields. Re-fetch with `pcb_PrimitiveComponent.getAll()`, set state fields, call `done()` when available, then verify again.
- Set stable component `uniqueId` values for newly added parts. Temporary IDs such as `$1`, `$2`, and `$3` can make schematic/PCB comparisons and import-change workflows harder to reason about.
- `SCH_Document.importChanges()` and `SCH_Netlist.setNetlist()` can return success without updating visible schematic primitives. Verify by re-opening the schematic and reading component objects.
- `pcb_Net.getNetlist('JLCEDA')` can return an array (element `0` schematic, `1` PCB), but in one observed bridge version it returned a single JSON string `{components:{...}}` instead — handle both; parse `components[designator].pinInfoMap` to read per-pin nets.
- Treat DRC categories literally. If only `Netlist Error` remains, say copper clearance/connectivity checks passed but schematic/PCB synchronization is still unresolved.
- The bridge runs in the page context, so `document`/DOM is available and there is **no screenshot API**. Calls that need a UI confirmation return `true` but do nothing until you click the dialog button via DOM: `pcb_Document.importChanges()` needs **"Apply Changes"** clicked (else PCB stays at 0 components); the autorouter needs **"Run"** clicked.
- A lingering `Netlist Error` with clean copper is usually leftover **floating named-net stub wires** in the schematic (left after deleting/swapping a component). Find via `sch_PrimitiveWire.getAllPrimitiveId()`→`get(id)`→`getState_Polyline()` by coordinate, delete, save, re-import.
- `getBomFile`/netlist read the **saved** doc: call `pcb_Document.save()` before regenerating after any field change, or the BOM shows stale values.
- Library-placed components carry `supplierId` = manufacturer-part + ".1", NOT the LCSC `C`-number. Set the real `Cxxxx` on both PCB (`toAsync().setState_SupplierId`) and schematic (`modify({supplierId})`), save, and confirm in the regenerated BOM "Supplier Part" column. Use `lib_Device.getByLcscIds([...])` to look parts up.
- `create` + `getAllPinsByPrimitiveId` in one bridge call can time out (30s) and get retried, creating duplicate `null`-designator strays — split the calls and delete strays afterward.
- Single-row 2.54mm female headers share `HDR-TH_{N}P-P2.54-V-F`; suffixes `-2/-3/_4` are different *heights*. Use the bare footprint (and a `H8.5`-style standard body) so all headers match; verify via `getState_OtherProperty()["Footprint"]`/`["3D Model Title"]`.
- For edge connectors, the mouth is the side opposite the signal-pad row; rotate it to face outward and overhang the outline. After moving routed parts, rip up all tracks+vias before re-autorouting.

## Schematic Net-Label Policy

- Prefer net labels for repeated or long connections.
- It is acceptable for schematic wires not to touch directly when the net names match.
- Confirm the following net classes propagate to PCB:
  - `+5V`, `+3V3`, `GND`, `VIN`
  - `RESET`, auto-reset capacitor/DTR net
  - `USB_D+`, `USB_D-` or the project's equivalent names
  - UART TX/RX between USB-UART and MCU
  - SPI/ICSP nets
  - Arduino digital and analog header nets

## Autorouting And Manufacturing Output

- When requested, use `Route > Auto Routing...`. Via the bridge there is no PCB autoroute API — click the `Route` header span, the `Auto Routing...` item, then the dialog's **`Run`** button (DOM). Do not click `Cancel` after it finishes (routes survive but it throws a canvas-subscription error).
- **Before re-autorouting after any routed part moved/rotated/swapped, loop-delete tracks/vias/poured until verified `0`.** One delete pass leaves leftovers (pass-0 ~480 deleted, pass-1 still finds 8–16); routing a partially-routed board gives random junk errors. Loop {delete layer-1+2 lines + `pcb_PrimitiveVia` + `pcb_PrimitivePoured`; re-read counts} until all `==0`, then Run. Don't hand-route congested rows (clearance) — a clean full rip + one autoroute pass handles density better.
- If `getAllPrimitiveId` throws "Cannot read properties of null (reading 'map')" after autoroute, the doc is in a stuck post-router state; recover (routes survive) via `openDocument(schematicUuid)` → wait → `openDocument(pcbUuid)` → wait.
- **GND pour:** definition = `pcb_PrimitivePour`; filled copper = `pcb_PrimitivePoured`. No fill API — Tools → "Copper Manager..." → "Rebuild All" → "Confirm" (DOM). If `pcb_PrimitivePoured` count stays `0` after Rebuild, the session is stuck → **restart EasyEDA Pro** (doc reload won't fix); then rebuild fills. Re-pour after every reroute and verify count `> 0`.
- Confirm the log reports `nets completion: 100.00%`, or equivalently that `pcb_Drc.check(false,false,true)` reports **0 Connection Errors**.
- Inspect for unconnected USB pads and header nets after autoroute.
- Generate manufacturing data only after routing is complete.
- Use `Order PCB/FPC at JLCPCB`, not similarly named export options.
- Confirm the EasyEDA dialog after order data generation.
- If EasyEDA shows a modal dialog during the requested workflow, press the appropriate confirm/OK/continue button so the workflow is not left blocked.
- Open the newly generated URL in Chrome when the user wants to continue ordering.
- Treat EasyEDA's "Order data generated finish" Confirm button as order-data handoff only. It is not the final JLCPCB purchase button.
- If the user says a human will place the order, stop after opening the regenerated quote/order-prep page.
- If the JLCPCB quote or SMT page is dynamic, login-gated, or otherwise not machine-readable, report that final PCBA shortage verification still needs human review.
- EasyEDA shortcut order APIs can return `false` for all combinations of `interactive` and `ignoreWarning`, especially when the client blocks order handoff or a netlist warning remains. Do not imply the quote was regenerated in that case.
- `placePcbOrder()` (and the components-order variants) are interactive-only and are **blocked by the harness safety classifier** as real order transactions. For "order data + quote" scope, generate the files below and let the human open the quote / upload to JLCPCB; state that quote-page verification was not done.
- When shortcut order APIs fail, export manufacturing data directly:
  - `pcb_ManufactureData.getBomFile('BoardName_BOM', 'csv')`
  - `pcb_ManufactureData.getPickAndPlaceFile('BoardName_PickAndPlace', 'csv')`
  - `pcb_ManufactureData.getGerberFile('BoardName_Gerber')`
- Validate generated files locally:
  - Search the BOM for the old and new supplier part codes.
  - Search Pick-and-Place for changed designators.
  - Test Gerber zip integrity with `unzip -t`.
  - If the Gerber file object has no `.zip` suffix in its name, save it with a `.zip` extension when the MIME/content is a zip.
  - These getters return browser `File` objects; transfer over the bridge by `await f.arrayBuffer()` → chunked base64 → return → decode/save with a host script.
  - **Current EasyEDA returns BOM and Pick-and-Place as `.xlsx`, not CSV** (`Export_BOM.xlsx`; Pick-and-Place named `Pick_Place`, bytes start `PK\x03\x04`). Save `.xlsx`, verify by reading `xl/sharedStrings.xml` from the zip and grepping designators / new+old C-numbers. Legacy CSV (UTF-16) handling still applies if the bridge returns CSV. Gerber stays `.zip`.

## Final Response Template

Keep the final response short and concrete:

- State the changed designator and old/new JLCPCB part codes.
- State stock/shortfall status.
- State BOM verification: old absent, new present.
- State whether order data was regenerated and a new quote URL opened.
- State that final purchase/payment was not performed unless explicitly authorized.
