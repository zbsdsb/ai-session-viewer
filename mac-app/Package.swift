// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "AISessionViewer",
    platforms: [.macOS(.v13)],
    products: [
        .executable(name: "AISessionViewer", targets: ["AISessionViewer"]),
    ],
    targets: [
        .executableTarget(
            name: "AISessionViewer",
            linkerSettings: [
                .linkedLibrary("sqlite3")
            ]
        )
    ]
)
