// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "PingPilotGlass",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(name: "PingPilotGlass", targets: ["PingPilotGlass"])
    ],
    targets: [
        .executableTarget(
            name: "PingPilotGlass",
            path: "Sources/PingPilotGlass"
        )
    ]
)
