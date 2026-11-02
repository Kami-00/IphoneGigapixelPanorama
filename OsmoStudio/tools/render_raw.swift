import Foundation
import CoreImage
import ImageIO
let args=CommandLine.arguments
 guard args.count==3 else{fatalError("input.dng output.jpg")}
let url=URL(fileURLWithPath:args[1])
guard let raw=CIRAWFilter(imageURL:url,options:[:]),let image=raw.outputImage else{fatalError("RAW konnte nicht entwickelt werden")}
let context=CIContext(options:[.cacheIntermediates:false])
let cs=CGColorSpace(name:CGColorSpace.sRGB)!
if URL(fileURLWithPath:args[2]).pathExtension.lowercased()=="png" {
    try context.writePNGRepresentation(of:image,to:URL(fileURLWithPath:args[2]),format:.RGBA8,colorSpace:cs)
} else {
    try context.writeJPEGRepresentation(of:image,to:URL(fileURLWithPath:args[2]),colorSpace:cs,options:[kCGImageDestinationLossyCompressionQuality as CIImageRepresentationOption:1.0])
}
print("\(Int(image.extent.width)) × \(Int(image.extent.height))")
