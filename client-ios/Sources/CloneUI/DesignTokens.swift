import Foundation
import SwiftUI

public struct ScreenToken: Decodable {
    public let name: String?
    public let description: String?
    public let status: String?
    public let screenshot: String?
    public let hierarchy: String?
    public let directory: String?
    public let metrics: ScreenMetrics?
    public let steps: [Step]?
}

public struct ScreenMetrics: Decodable {
    public let element_count: Int?
    public let class_frequency: [String: Int]?
    public let accessibility: [AccessibilityEntry]?
}

public struct Step: Decodable {
    public let index: Int?
    public let action: String?
    public let description: String?
    public let status: String?
}

public struct AccessibilityEntry: Decodable {
    public let label: String?
    public let identifier: String?
    public let value: String?
}

public struct DesignTokens: Decodable {
    public let run_id: String?
    public let screens: [String: ScreenToken]
}

public final class TokenStore: ObservableObject {
    @Published public private(set) var tokens: DesignTokens = DesignTokens(run_id: nil, screens: [:])

    public init() {
        load()
    }

    public func load(from url: URL? = nil) {
        let fileURL = url ?? Bundle.module.url(forResource: "tokens", withExtension: "json")
        guard let fileURL else {
            print("DesignTokens: tokens.json missing")
            return
        }

        do {
            let data = try Data(contentsOf: fileURL)
            let decoder = JSONDecoder()
            tokens = try decoder.decode(DesignTokens.self, from: data)
        } catch {
            print("DesignTokens: failed to decode tokens.json -> \(error)")
        }
    }
}
