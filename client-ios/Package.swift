// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "CloneUI",
    platforms: [
        .iOS(.v16)
    ],
    products: [
        .app(name: "CloneApp", targets: ["CloneApp"])
    ],
    dependencies: [
    ],
    targets: [
        .target(
            name: "CloneUI",
            path: "Sources/CloneUI",
            resources: [
                .process("Resources")
            ]
        ),
        .executableTarget(
            name: "CloneApp",
            dependencies: ["CloneUI"],
            path: "Sources/CloneApp"
        )
    ]
)
