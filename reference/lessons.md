# Lessons from real jobs

## Multi-colorway electronics carton render (front and side panels)
- The source of truth was an outlined Illustrator tech pack (`_OL`). It was exported at 200% and read from crops.
- The render was 5504×3072. Preview images come back about 1600 px wide, so **always measure at full resolution**. Multiply preview coordinates by width/1600 only to find areas roughly.
- **Content-Aware Fill on a smooth gray carton left visible lighter and darker patches.** A median filter (radius 22, two passes) plus 1.2% monochrome grain was invisible.
- Front copy sloped about −1.8° (rule lines about −2.1°). Rotation matched.
- Side panels sloped +6° to +14°, getting steeper further down the face (perspective). Rotating would have tilted the letters, so **vertical skew** matched. Each line gets its own angle.
- Graphic elements (thin icon bars) touched the label text, and automatic detection merged them. Gridded zoom crops gave the coordinates. Bands must stop 6 px or more from such elements.
- Fonts:
  - Helvetica Neue Regular at 80% horizontal scale matched the AI's condensed sans on the front.
  - Medium caps matched the side labels.
  - The first try at 100% width looked too light and wide.
- Light text on gray was about (238,237,241). Foil colors were sampled from solid icon areas on each colorway.
- The render split one line of the source copy over two lines with wrong values. Flag this kind of layout difference for the user instead of choosing silently.

## MOSSBLOOM demo (fictional brand: Firefly render plus a tech pack built in Illustrator)
- **Illustrator special characters:** `—`-style escapes in the tool call arrive already decoded, and the illustrator server then reads the script as MacRoman, which gives "‚Äî". In Illustrator scripts **use `String.fromCharCode(0x2014)`**. (The Photoshop server handled `®` fine.)
- **Illustrator scripts that change many text frames, then save and export, can run past the server's 30-second limit.** The edits still apply. Split the work into small calls: edit, then save, then export. Check the state before retrying.
- **Illustrator stops answering scripts when it's in the background**, probably App Nap. Running `open -a "Adobe Illustrator"` (the full app path) before each Illustrator call fixed it every time. Also: `cut` is a reserved global in Illustrator's JavaScript, so don't name a variable `cut`.
- Text frames are slow to create. Cache `app.textFonts.getByName()` lookups and keep each call to about 10 frames or fewer.
- The Firefly render (1792×2304) kept the large front copy legible and garbled all 16 lines of small paragraph text on the side panel, sloping −7° to −14° on the receding face.
- **New type looked more in focus than the render.** Measured with `match_softness.py` against the correctly printed headings: new type sharpness 3.69 against the reference's 2.57. A 0.9 px Gaussian blur plus 1.5% mono grain as smart filters brought it to 2.41. Now a standard step.
- Firefly output arrives as a **smart object layer**, so the duplicated cleanup layer is a smart object too, and the median and noise become smart filters (fine, still non-destructive).
- Converting the text group to a smart object flipped other layers' visibility. `softenGroup` now records and restores visibility. Always snapshot and look after any smart object conversion.
- Skew helper: anchoring by bounds made lines without descenders sit off their baseline. It now corrects with dy = −(x − cx)·tan(angle), which is exact.
