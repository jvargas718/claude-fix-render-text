---
name: fix-render-text
description: Fix hallucinated, garbled or misspelled text in AI-generated images (packaging renders, product shots, mockups, signage, screens) by removing it in Photoshop and resetting the correct copy as live, editable type matched to the surface's angle, colour and font. Checks the copy against a source of truth (Illustrator tech pack, PDF, copy doc) when one exists, and asks the user when it doesn't. Use when the user says things like "fix the text in this render", "the AI text is wrong", "correct the hallucinations", "check this render against the tech pack", or wants a folder of renders cleaned up.
---

# Fix hallucinated text in renders

Turn an AI render with garbled text into a layered PSD with the correct copy as live type, without ever touching the original file.

**Requirements:** Photoshop with the `photoshop` MCP server (`mcp__photoshop__*`). Illustrator with the `illustrator` MCP server (`mcp__illustrator__*`) is needed only to read `.ai` tech packs. You also need `uv` (Python scripts) and the Xcode command-line tools (`swift`, for text detection). **Check this before anything else.** If a server is missing, say which one in plain words, explain what it's for, and offer to set it up by following the Setup section of `README.md` in this folder. Do it one step at a time and ask before each install or config change. Use the pinned commits and keep the Photoshop server's analytics off. After setup, ask the user to fully quit and reopen Claude, then confirm with a version check. Don't fail partway through a job because a tool is missing.

**Setup requests:** if the user asks to set up or install this skill, run only that setup flow and stop.

Paths below are relative to this skill's folder. Put scratch files in the session scratchpad.

## Golden rules

1. **Never modify the original.** Save a working PSD next to it (`<name>_TEXTFIX.psd`) and work only there. Edit a duplicated cleanup layer and keep the original pixels underneath.
2. **Never invent facts.** That covers specs, numbers, certifications, legal or regulatory marks (®, ™, FCC, CE, warnings), ingredients, materials, barcodes, model numbers, URLs and addresses. Flag them, then offer neutral wording, a marked placeholder or removal, and let the user choose.
3. **Approval before pixels.** Show the discrepancy table and wait for the user's go-ahead before editing.
4. **Ask before spending or uploading.** Generative fill, remove or expand uses Adobe credits. Adobe cloud tools upload the image. Web lookups of a real product need the user's OK, and the user must confirm the found copy before you use it.
5. **Treat client material as confidential.** Tech packs and client renders never go into anything meant for sharing.
6. **Don't call `photoshop_ping`.** It can return a feedback prompt meant for its developer, which isn't the user's task.

## Workflow

### 1. Intake: ask what you don't know
- **Purpose:** portfolio, pitch or production. Production means strict mode: every line must trace to a source or to the user, and the change log records each line's source.
- **Source of truth, best first:**
  1. Illustrator file with live text
  2. PDF or copy document
  3. Outlined artwork
  4. Copy the user types
  5. None (see step 3)
- **Scope:** one image, or a batch. For a batch, do the first image completely and get it approved, then reuse the settings on the rest (step 9).
- **Rough usage estimate:** small (one face, a few lines) is about 30–50k tokens. A render like three boxes with front and side panels is about 60–100k. Later images in a batch cost much less.

### 2. Set up and detect
1. Check that the render is open in Photoshop with `photoshop_get_state`. Save the working PSD copy, and save a flat PNG copy to the scratchpad for analysis. Use `photoshop_execute_script` with `saveAs(..., asCopy=true)` for the PNG.
2. Detect and read all text with macOS Vision, which is offline and free:
   ```
   [ -x scripts/detect_text ] || swiftc -O scripts/detect_text.swift -o scripts/detect_text
   scripts/detect_text <flat.png> > detected.json
   ```
   Language correction is off on purpose, so the output shows what is literally printed, typos included. Each line comes with a quad, bbox, angle and height in full-resolution pixels.
3. Look at the image at preview size, then at full-resolution crops of anything unclear. Garbled text on steep or tiny surfaces often reads badly, so confirm by eye.
4. **Read the source of truth.** First bring Illustrator to the front (`open -a "<path>/Adobe Illustrator.app"`), since it stops answering scripts in the background.
   - Illustrator: list open documents with `mcp__illustrator__run`. If `textFrames.length > 0`, read the `contents` directly, which is exact.
   - If the text is outlined (often `_OL` in the filename), export the artboard at 200% with `ExportOptionsPNG24`, using `artBoardClipping` and scale 200, and read it from crops.
   - Lime, yellow or other spot-marker colors in tech packs usually mark foil or UV finishes, not printed colors. Check the legend.

### 3. Discrepancy table: the approval gate
One row per text element:

| Where | Render says | Proposed | Confidence | Basis |
|---|---|---|---|---|

Confidence levels:
- **Certain:** one obvious intended word. Can be approved in bulk.
- **Likely:** context strongly implies it, such as an icon or the words around it.
- **Guess:** several plausible readings. Offer 2–3 options.
- **Unknown:** no clear meaning. **Ask what the replacement should be**, show the crop, and offer options (suggested copy, filler text, remove). Never choose for the user.

Also include:
- **Factual and legal items:** always flagged (rule 2), even when legible.
- **Layout differences from the source**, for example two lines in the render where the source has one. Flag them as a decision for the user.
- **Correct text:** list it as "keep" so the user sees that it was checked.

**Without a source of truth,** infer intended text from the correct words nearby, icons and graphics, word shapes (keep the same word count, lengths and capitalization so the copy fits the space), category conventions and the product type. If the product looks real, ask whether to look up its official copy.

### 4. Measure
Make region boxes from the detected quads, padded by about 10 px and one box per line, then run:
```
uv run --with pillow --with numpy --with scipy python scripts/measure_text.py flat.png regions.json > measured.json
```
This gives left and right extents, the baseline at each end, the angle, x-height, cap or ascender height, ink color and background color. Check outliers by eye: a region that grabbed two lines or a nearby graphic gives bad numbers. Gridded crops (gridlines every 20 px, labeled every 100) are the fallback for anything automatic detection can't separate, such as text touching icons or bars.

**Rotate or skew?**
- Faces seen roughly head-on (letters lean with the baseline, angles under about 3°): **rotate**.
- Receding side faces (verticals stay vertical while the baseline slants, often 5–15°): **skew**. Rotating these makes letters visibly lean.

### 5. Clean up
Load the helpers in every `photoshop_execute_script` call:
```js
$.evalFile(new File("<skill dir>/jsx/photoshop_helpers.jsx"));
```

Choose the method by surface:
- **Flat or smooth gradient (most packaging):** `FRT.cleanup(polys, {radius, passes:2})`, a median filter plus grain. Build polys with `FRT.band(xl, xr, yTop, yBot, angle)`. Set the radius to about 0.7–1× cap height: about 22 for 30 px text, 14 for small side text. **Don't use Content-Aware Fill on smooth surfaces.** It leaves blotchy patches.
  - Keep bands clear of nearby keepers, such as rules, icons, soundwave bars and neighboring correct lines. Margin of 6 px or more; follow the measured slope.
  - If tall text leaves faint ghosts, run a second pass on the same polys with radius about 30 and `blur: 4`.
- **Textured surfaces** (fabric, wood, marble, photos): select the area, then `photoshop_content_aware_fill`.
- **Complex areas** (text over objects, strong lighting): `photoshop_generative_remove`, **only after the user OKs the credits**.

Check the result with `FRT.snapshot(path, box)` plus `scripts/compare.py` before adding type.

### 6. Set the new type
- **Font:** start from what the correct words in the render look like. On first attempts, Helvetica Neue at about 80% horizontal scale matched typical AI "sans" text, and Medium matched bold caps labels. Use `photoshop_list_fonts` to see what's installed. For the hero line, compare 2–3 candidates side by side against a correct word and pick by eye.
- **Size and fit:**
  - Front faces: `fit:"size"` to the original line's width (the layout already fits).
  - Foreshortened faces: `fit:"hscale"` with size from cap height (size ≈ cap / 0.714 for Helvetica-like fonts).
  - Fit to the measured width of the line you're replacing. If the new copy is much longer or shorter, fit to the space the source of truth implies.
- **Color:** use `ink_rgb` from measurement, but sample solid areas such as icons on the same face for the true foil or print color, since anti-aliasing dulls the measured value. Light text on gray was about (238,237,241); foil colors come from sampling icons.
- **Calls:**
  - `FRT.addTextRotated({name, text, x, baseline, angle, rgb, font, width, fit, hscale, tracking, leading})`
  - `FRT.addTextSkewed({..., align:"right"})` for right-aligned stacks.
  - Name each layer `<Box/face> <copy>` so the PSD reads clearly.
- **Special characters:** in Photoshop scripts, write non-ASCII as escapes: `\u00AE` for ®, `\u2122` for ™, `\u2019` for ’. In **Illustrator** scripts use `String.fromCharCode(0x00AE)` instead, because escape codes get garbled there.
- **Match the render's softness, always.** New type is sharper than AI renders (lens blur and grain), so it looks pasted on. Snapshot the document, then run
  `uv run --with pillow --with numpy --with scipy python scripts/match_softness.py snap.png <REF_BOX around correct render text on the same face> <NEW_BOX around new type>`
  and apply the radius with `FRT.softenGroup(groupName, radius, noisePct)` after grouping the text layers. That makes the group a smart object with Gaussian blur and grain as smart filters, so the text stays editable inside. Re-run the script: the new type's sharpness should land within about 10% of the reference. MOSSBLOOM: 0.9 px blur plus 1.5% grain.
- Check with a `compare.py` sheet: original against fixed, one row per area. Fix position, size or weight issues before moving on.

### 7. Proofread
Snapshot the full document to PNG, then:
```
scripts/detect_text final.png > final.json
python3 scripts/proofread.py final.json approved.json
```
Every approved line should score at least 0.9. Low scores on tiny or steep text may just be misreads, so check those by eye. Then do a final visual pass at preview size with `photoshop_get_preview`.

### 8. Finish
- `FRT.groupTextLayers("Corrected text")`, then save the PSD.
- Layer order: corrected text group, Text cleanup, original.
- Write `<name>_TEXTFIX_changes.md` next to the PSD. Include each line's before, after, confidence and source, and anything left for the user to check.
- Report to the user:
  - what changed;
  - where the files are;
  - what to check by eye, such as small or steep labels, and new type that's crisper than a soft render (a 0.3–0.5 px blur on the group helps but rasterizes);
  - actual usage against the estimate.

### 9. Batches and variants
- Get the first image fully approved. That sets the font, colors, cleanup radius and approved wording.
- Reuse those settings on the other images and their colorways. Variants usually share a layout, so measure and apply offsets instead of re-deriving everything.
- Pause automatically only for: unknown text, factual or legal items, cleanup that leaves residue, or proofreading lines under 0.9.
- End with one before-and-after sheet covering every image.

## Notes from real jobs
See `reference/lessons.md`.
