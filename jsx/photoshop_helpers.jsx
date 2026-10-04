// fix-render-text: Photoshop ExtendScript helpers.
// Load inside photoshop_execute_script with:  $.evalFile(new File("~/.claude/skills/fix-render-text/jsx/photoshop_helpers.jsx"));
// All coordinates are document pixels, origin top-left. Angles in degrees; positive = baseline falls to the right.
// Non-ASCII characters (®, ™, accents, curly quotes) must be passed as \u escapes.

var FRT = (function () {
  function px(v) { return v.as("px"); }
  function cT(s) { return charIDToTypeID(s); }
  function doc() { return app.activeDocument; }

  // Working copy: duplicate Background as a cleanup layer (original pixels stay untouched underneath).
  function ensureCleanupLayer(name) {
    var d = doc(); name = name || "Text cleanup";
    try { return d.artLayers.getByName(name); } catch (e) {}
    var src = d.artLayers[d.artLayers.length - 1];
    var c = src.duplicate(); c.name = name; c.move(src, ElementPlacement.PLACEBEFORE); return c;
  }

  // Parallelogram that follows a sloped text line. ang = baseline angle.
  function band(xl, xr, yTop, yBot, ang) {
    var t = Math.tan(ang * Math.PI / 180), dy = (xr - xl) * t;
    return [[xl, yTop], [xr, yTop + dy], [xr, yBot + dy], [xl, yBot]];
  }

  // Remove text on flat/gradient surfaces: median + grain. (Content-Aware Fill blotches smooth surfaces.)
  // polys: array of point arrays. radius ~ 0.7-1x the cap height; passes 2.
  function cleanup(polys, o) {
    o = o || {}; var d = doc(); var L = ensureCleanupLayer(o.layer); d.activeLayer = L;
    for (var i = 0; i < polys.length; i++) d.selection.select(polys[i], i ? SelectionType.EXTEND : SelectionType.REPLACE, 0, true);
    d.selection.feather(o.feather || 3);
    for (var p = 0; p < (o.passes || 2); p++) L.applyMedianNoise(o.radius || 22);
    if (o.blur) L.applyGaussianBlur(o.blur);
    L.applyAddNoise(o.noise === undefined ? 1.2 : o.noise, NoiseDistribution.GAUSSIAN, true);
    d.selection.deselect();
    return "cleaned " + polys.length + " regions on '" + L.name + "'";
  }

  function makeText(o) {
    var d = doc(); var L = d.artLayers.add(); L.kind = LayerKind.TEXT; L.name = o.name;
    var ti = L.textItem; ti.kind = TextType.POINTTEXT; ti.font = o.font || "HelveticaNeue";
    ti.size = new UnitValue(o.size || 30, "px"); ti.antiAliasMethod = AntiAlias.SMOOTH; ti.contents = o.text;
    if (o.tracking !== undefined) ti.tracking = o.tracking;
    ti.horizontalScale = o.hscale || 100;
    if (o.leading) { ti.useAutoLeading = false; ti.leading = new UnitValue(o.leading, "px"); }
    var c = new SolidColor(); c.rgb.red = o.rgb[0]; c.rgb.green = o.rgb[1]; c.rgb.blue = o.rgb[2]; ti.color = c;
    if (o.align === "right") ti.justification = Justification.RIGHT;
    ti.position = [new UnitValue(o.x, "px"), new UnitValue(o.baseline, "px")];
    return L;
  }

  // Fit width: "size" scales the font, "hscale" squeezes horizontally (side panels, foreshortened faces).
  function fitWidth(L, o) {
    var b = L.bounds, w = px(b[2]) - px(b[0]), ti = L.textItem;
    if (!o.width) return;
    if (o.fit === "hscale") ti.horizontalScale = Math.max(15, Math.min(200, ti.horizontalScale * o.width / w));
    else { ti.size = new UnitValue(px(ti.size) * o.width / w, "px"); if (o.leading) ti.leading = new UnitValue(o.leading, "px"); }
    ti.position = [new UnitValue(o.x, "px"), new UnitValue(o.baseline, "px")];
    if (o.align === "right") { b = L.bounds; L.translate(new UnitValue(o.x - px(b[2]), "px"), 0); }
  }

  // Front-facing text: rotate around the baseline start so it matches the measured slope.
  function addTextRotated(o) {
    var L = makeText(o); fitWidth(L, o);
    var b = L.bounds, ax = px(b[0]), ay = px(b[1]);
    L.rotate(o.angle || 0, AnchorPosition.TOPLEFT);
    var th = (o.angle || 0) * Math.PI / 180, dx = o.x - ax, dy = o.baseline - ay;
    var nx = ax + Math.cos(th) * dx - Math.sin(th) * dy, ny = ay + Math.sin(th) * dx + Math.cos(th) * dy;
    L.translate(new UnitValue(o.x - nx, "px"), new UnitValue(o.baseline - ny, "px"));
    return o.name + " size=" + px(L.textItem.size).toFixed(1) + " hs=" + L.textItem.horizontalScale.toFixed(0) + " bounds=" + L.bounds.toString();
  }

  // Receding faces: letters stay upright in perspective, so shear vertically instead of rotating.
  // Skewing about the layer centre moves a point at x by (x - cx) * tan(angle); undo that for the
  // anchor point (o.x, o.baseline) so the baseline stays exactly where it was measured.
  function addTextSkewed(o) {
    var L = makeText(o); o.fit = o.fit || "hscale"; fitWidth(L, o);
    var b = L.bounds, cx = (px(b[0]) + px(b[2])) / 2;
    doc().activeLayer = L;
    var desc = new ActionDescriptor(), ref = new ActionReference();
    ref.putEnumerated(cT('Lyr '), cT('Ordn'), cT('Trgt')); desc.putReference(cT('null'), ref);
    desc.putEnumerated(cT('FTcs'), cT('QCSt'), cT('Qcsa'));
    var sk = new ActionDescriptor(); sk.putUnitDouble(cT('Hrzn'), cT('#Ang'), 0); sk.putUnitDouble(cT('Vrtc'), cT('#Ang'), o.angle || 0);
    desc.putObject(cT('Skew'), cT('Pnt '), sk); executeAction(cT('Trnf'), desc, DialogModes.NO);
    var dy = -(o.x - cx) * Math.tan((o.angle || 0) * Math.PI / 180);
    L.translate(0, new UnitValue(dy, "px"));
    return o.name + " size=" + px(L.textItem.size).toFixed(1) + " hs=" + L.textItem.horizontalScale.toFixed(0) + " bounds=" + L.bounds.toString();
  }

  // Match the render's softness: group -> smart object, then Gaussian blur + grain as smart filters.
  // Text stays editable inside the smart object; filters can be tweaked or switched off later.
  // Get the radius from scripts/match_softness.py (compares against the render's own lettering).
  function softenGroup(groupName, radius, noisePct) {
    var d = doc(), g = d.layerSets.getByName(groupName);
    var vis = {}; for (var i = 0; i < d.layers.length; i++) vis[d.layers[i].name] = d.layers[i].visible;
    d.activeLayer = g;
    executeAction(stringIDToTypeID("newPlacedLayer"), undefined, DialogModes.NO);
    var so = d.activeLayer; so.name = groupName + " (softened to match render)";
    var gb = new ActionDescriptor(); gb.putUnitDouble(cT('Rds '), cT('#Pxl'), radius);
    executeAction(cT('GsnB'), gb, DialogModes.NO);
    if (noisePct) {
      var nz = new ActionDescriptor(); nz.putEnumerated(cT('Dstr'), cT('Dstr'), cT('Gsn '));
      nz.putUnitDouble(cT('Nose'), cT('#Prc'), noisePct); nz.putBoolean(cT('Mnch'), true);
      executeAction(cT('AdNs'), nz, DialogModes.NO);
    }
    // Converting/filtering can flip other layers' visibility; restore what the user had.
    for (var j = 0; j < d.layers.length; j++) { var l = d.layers[j]; if (vis[l.name] !== undefined) l.visible = vis[l.name]; }
    so.visible = true;
    return so.name + " blur=" + radius + " noise=" + (noisePct || 0) + "%";
  }

  function groupTextLayers(name) {
    var d = doc(), g; try { g = d.layerSets.getByName(name); } catch (e) { g = d.layerSets.add(); g.name = name; }
    var n = 0; for (var i = d.artLayers.length - 1; i >= 0; i--) { var l = d.artLayers[i]; if (l.kind == LayerKind.TEXT) { l.move(g, ElementPlacement.INSIDE); n++; } }
    return n + " text layers grouped in '" + name + "'";
  }

  // Merged snapshot (optionally cropped) to PNG/JPG for checking. box = [l,t,r,b] in px.
  function snapshot(path, box, scalePct) {
    var d = doc(), t = d.duplicate("frt_snapshot", true);
    if (box) t.crop([UnitValue(box[0], "px"), UnitValue(box[1], "px"), UnitValue(box[2], "px"), UnitValue(box[3], "px")]);
    if (scalePct) t.resizeImage(UnitValue(scalePct, "percent"), null, null, ResampleMethod.BICUBIC);
    var f = new File(path);
    if (/\.png$/i.test(path)) t.saveAs(f, new PNGSaveOptions(), true); else { var o = new JPEGSaveOptions(); o.quality = 10; t.saveAs(f, o, true); }
    t.close(SaveOptions.DONOTSAVECHANGES); app.activeDocument = d; return f.fsName;
  }

  return { ensureCleanupLayer: ensureCleanupLayer, band: band, cleanup: cleanup, addTextRotated: addTextRotated,
           addTextSkewed: addTextSkewed, groupTextLayers: groupTextLayers, softenGroup: softenGroup, snapshot: snapshot };
})();
