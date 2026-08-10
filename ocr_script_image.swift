#!/usr/bin/env swift

import AppKit
import Foundation
import Vision

guard CommandLine.arguments.count == 2 else {
  FileHandle.standardError.write(Data("usage: ocr_script_image <image>\n".utf8))
  exit(2)
}

let imageURL = URL(fileURLWithPath: CommandLine.arguments[1])
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["zh-Hans", "en-US"]
request.usesLanguageCorrection = true

do {
  try VNImageRequestHandler(url: imageURL).perform([request])
  let lines = (request.results ?? []).compactMap { observation -> [String: Any]? in
    guard let candidate = observation.topCandidates(1).first else {
      return nil
    }
    let box = observation.boundingBox
    return [
      "text": candidate.string,
      "confidence": candidate.confidence,
      "x": box.origin.x,
      "y": box.origin.y,
      "width": box.width,
      "height": box.height,
    ]
  }
  let data = try JSONSerialization.data(withJSONObject: lines, options: [.prettyPrinted, .sortedKeys])
  FileHandle.standardOutput.write(data)
  FileHandle.standardOutput.write(Data("\n".utf8))
} catch {
  FileHandle.standardError.write(Data("OCR failed: \(error)\n".utf8))
  exit(1)
}
