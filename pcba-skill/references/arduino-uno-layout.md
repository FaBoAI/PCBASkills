# Arduino UNO-Compatible Layout Notes

When exact Arduino UNO compatibility is requested, use the official Arduino UNO Rev3 board as the mechanical reference and verify header placement numerically, not only by eye.

- Use a 2700 mil x 2100 mil board outline for the UNO-sized rectangle when the local coordinate system starts at the board corner. This corresponds to 68.58 mm x 53.34 mm.
- Place the primary Arduino headers at the reference coordinates in mils and verify `dx=0`, `dy=0`, and matching rotation after placement:
  - `H1` POWER: `(1450, 100)`, rotation `0`.
  - `H3` A0-A5: `(2250, 100)`, rotation `0`.
  - `H4` D8-D13/SDA/SCL: `(1190, 2000)`, rotation `180`.
  - `H2` D0-D7: `(2150, 2000)`, rotation `180`.
  - `H5` ICSP: `(2555, 1100)`, rotation `270`.
- Keep the Arduino header footprints single-row female headers unless the user explicitly requests another connector type.
- Use the SAME female-header family/height for every header. The 2.54mm single-row female footprints follow the name `HDR-TH_{N}P-P2.54-V-F`; a trailing suffix like `-2`/`-3`/`_4` is a *different-height* variant and will look taller/shorter than the others (e.g. `XDM254C-1-06-Z-3.0-G0` is a tall 3.0 variant). Pick the bare `HDR-TH_6P-P2.54-V-F` and confirm a standard ~8.5mm body (part names often encode it, e.g. `...-H8.5`) so H3 matches H1/H2/H4. Verify each header's `Footprint`/`3D Model Title` via `getState_OtherProperty()` and compare across H1–H5.
- Leave enough keepout/clearance around the offset digital-header gap; do not "straighten" the UNO header spacing into a generic 0.1 inch grid.
- **Mounting holes** (4x, 3.2mm/126mil diameter, matching M3/4-40 per the official Adafruit/johngineer "Arduino Dimensions and Hole Patterns" drawing), in the same mil coordinate system as the headers (origin at the board's top-left corner, X right, Y down, USB-C on the left edge):
  - `(600, 100)` — top-left, near the POWER header.
  - `(2600, 700)` — right side, upper.
  - `(550, 2000)` — bottom-left. **Not X-aligned with the top-left hole** — it sits 50mil further left (a genuine quirk of the official Arduino board, confirmed against a user-supplied reference drawing); do not "fix" this by aligning it to `x=600`.
  - `(2600, 1800)` — right side, lower.
  - The chained/cumulative dimensioning in the official PDF is easy to misread (a naive reading of the vertical chain undercounts by one segment vs. the labeled total height) — cross-check any hole coordinates you derive from a dimension drawing against the total board height/width before trusting them, and prefer a user-supplied reference image over your own chain-parsing when one is available.
  - Right-side holes sit close enough to the board edge (100mil/2.54mm) that a snug enclosure wall will have very little clearance around a boss there (see Fusion section below) — this is inherent to the official board, not a placement mistake.
  - Create mounting holes as unplated (NPTH) round pads: `pcb_PrimitivePad.create(12 /* MULTI layer */, "MH1", x, y, 0, ["ELLIPSE", 126, 126], "" /* no net */, ["ROUND", 126], 0, 0, 0, false /* metallization */, 0 /* EPCB_PrimitivePadType.NORMAL */, undefined, null, null, false)`. Adding these to an already-placed, already-routed board is a **layout-changing edit**: rip up tracks/vias/pour, check hole-vs-component clearance (bosses/pads near existing parts), reroute, and re-pour exactly as for any moved component (see "Rip-up & Reroute").
- **Per-pin silkscreen labels** (optional, but this is what makes a board read as genuinely "Arduino-compatible" rather than just electrically compatible): real Arduino boards print the pin function next to each pin, not a generic header reference designator.
  - POWER (1x8): `NC, IOREF, RESET, 3V3, 5V, GND, GND, VIN`.
  - Digital 0-7 (1x8): plain numbers `0`..`7` (pins 0/1 are RX/TX but a bare number is enough).
  - Analog (1x6): `A0`..`A5`.
  - Digital 8-13 + SPI/I2C (1x10): `8, 9, 10, 11, 12, 13, GND, AREF, SDA, SCL`.
  - ICSP (2x3): usually unlabeled on the real board (just a pin-1 indicator) — skip individual labels here.
  - Hide the generic header `Designator` (H1, H2, …) from silkscreen instead of leaving both visible — find its attribute via `pcb_PrimitiveAttribute.getAllPrimitiveId()` (IDs are `${componentPrimitiveId}${suffix}`), fetch with `.get()`, filter by `key === "Designator"`, and set `valueVisible: false` via `pcb_PrimitiveAttribute.modify(id, {valueVisible:false})`.
  - At 100mil pin pitch, multi-character labels (`RESET`, `IOREF`, `AREF`) do not fit horizontally — rotate the string `90` degrees and size/position it so the label's long axis (its *text length*, which becomes the vertical extent once rotated) fits within the gap between the header row and whatever is on that side (board edge or interior components), not just eyeballed: compute `roughly 0.65 * fontSize * characterCount` for the longest label in the row and keep that much clearance from the pad row.


