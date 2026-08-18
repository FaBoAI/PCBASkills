# Display / FPC Mechanical Design (folded flat cables)

Lessons from mounting a TFT module (HS20HS072RX-class: module on the FRONT, FPC connector on the BACK) — generalizable to any folded-FPC display:

- **Get the real FPC geometry from the module datasheet's outline drawing before placing anything**: extended tail length (~20.7 mm here), where the fold happens (at the module edge — the user's photo/arrow beats your guess), and the tail-ROOT width (often far wider than the 12×0.5 mm contact end — the root needed a 26 mm opening, not the 8.4 mm the contact row suggests).
- **Route path budget**: fold at module edge → through the board (slot or edge notch) → down the back to the connector mouth. Sum front run + ~2–3 mm for the wrap through 1.6 mm FR-4 + insertion depth, and keep ≥ ~2 mm slack vs the tail length. Position the back-side connector from this budget (it ended up ~14 mm below the notch here), and clear any passives sitting where the connector lands.
- **Passing an FPC through the board mirrors its pin order**: the back-side connector must be wired in REVERSE (connector pin *n* = display pin *13 − n* for 12-pin). GND/VCC pairs are often symmetric, which hides the error — the 5 signal pins are what break. A user with the physical parts is authoritative on orientation; expect to flip once.
- **Bottom-contact flip connectors' mouth must face the slot/notch side**; connector orientation tends to oscillate across review rounds — re-confirm visually with the user before each fab export.
- **Draw a silkscreen mounting frame** (rect at the module's exact outline + a dimension label like `LCD 51.8x36.2`) as the assembly guide. If a placed "display component" footprint is used as a visual/BOM marker instead, its module-body silk usually includes a tail-fold zone on one side — align the BODY region to the frame and accept the tail zone pointing at the slot; check the hotbar pads stay ≥ 12 mil from board-outline edges (a slot IS board outline for DRC).

## Under-panel root-fold variant (no slot, connector on the SAME face as the panel)

Simpler than through-board when the front face has room: the tail folds back at its root and plugs into a connector hidden UNDER the panel. No slot/notch, and **no pin-order mirror — wire the connector STRAIGHT 1:1** (only a through-board pass mirrors the order). Verified geometry for X05A20L12T (12P 0.5 mm bottom-contact flip) on the TOP layer:

- **The mouth is on the ANCHOR-pad side** (pads 13/14), opposite the signal-contact row. rot0 → signals north / mouth south; rot90 → signals west / pin1 at the south end / mouth EAST. Landscape display with the tail exiting the right (short) edge ⇒ rot90, mouth toward the fold edge.
- **Position budget is module-relative**: put the signal-contact row ~15–16 mm from the module edge where the tail folds (HS20-class tail ≈ 20.7 mm extended; ≥19.5 mm placements have <1.5 mm slack — avoid). If the display frame moves, move the connector WITH it.
- Still re-confirm contact face + pin-1 with the physical tail before ordering — connector orientation has flipped between review rounds on every display project so far.


