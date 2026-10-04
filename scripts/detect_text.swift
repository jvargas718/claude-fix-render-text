// Detect and read text in an image with macOS Vision (offline, free).
// Usage: swift detect_text.swift <image> [--fast] [--min-height PX]
// Prints JSON: [{text, confidence, quad:{tl,tr,br,bl}, bbox:[x0,y0,x1,y1], angle_deg, height_px}]
// Coordinates are image pixels, origin top-left.
import Foundation
import Vision
import AppKit

let args = CommandLine.arguments
guard args.count >= 2, let img = NSImage(contentsOfFile: args[1]),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    FileHandle.standardError.write("usage: detect_text.swift <image> [--fast] [--min-height PX]\n".data(using: .utf8)!); exit(1)
}
let W = Double(cg.width), H = Double(cg.height)
var minH = 0.0
if let i = args.firstIndex(of: "--min-height"), i + 1 < args.count { minH = Double(args[i+1]) ?? 0 }
let req = VNRecognizeTextRequest()
req.recognitionLevel = args.contains("--fast") ? .fast : .accurate
req.usesLanguageCorrection = false   // we want what is literally printed, typos included
req.minimumTextHeight = Float(minH / H)
try VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
func p(_ pt: CGPoint) -> [Double] { [Double(pt.x) * W, (1 - Double(pt.y)) * H] }
var out: [[String: Any]] = []
for obs in req.results ?? [] {
    guard let c = obs.topCandidates(1).first else { continue }
    let tl = p(obs.topLeft), tr = p(obs.topRight), br = p(obs.bottomRight), bl = p(obs.bottomLeft)
    let xs = [tl[0], tr[0], br[0], bl[0]], ys = [tl[1], tr[1], br[1], bl[1]]
    let ang = atan2(br[1] - bl[1], br[0] - bl[0]) * 180 / .pi
    let h = hypot(tl[0] - bl[0], tl[1] - bl[1])
    out.append(["text": c.string, "confidence": Double(c.confidence),
                 "quad": ["tl": tl, "tr": tr, "br": br, "bl": bl],
                 "bbox": [xs.min()!, ys.min()!, xs.max()!, ys.max()!].map { ($0 * 10).rounded() / 10 },
                 "angle_deg": (ang * 100).rounded() / 100, "height_px": (h * 10).rounded() / 10])
}
let data = try JSONSerialization.data(withJSONObject: out, options: [.prettyPrinted, .sortedKeys])
print(String(data: data, encoding: .utf8)!)
