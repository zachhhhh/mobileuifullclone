import SwiftUI
import CloneUI
import UIKit

@main
struct CloneApp: App {
    @StateObject private var tokens = TokenStore()
    @State private var backendStatus: String = "loading"
    private let backendClient = BackendClient()

    var body: some Scene {
        WindowGroup {
            NavigationStack {
                ScreenListView(backendStatus: backendStatus)
                    .task {
                        do {
                            backendStatus = try await backendClient.health()
                        } catch {
                            backendStatus = "error"
                        }
                    }
            }
            .environmentObject(tokens)
        }
    }
}

struct ScreenListView: View {
    @EnvironmentObject private var tokens: TokenStore
    let backendStatus: String

    var body: some View {
        List {
            Section("Backend") {
                Text("Status: \(backendStatus)")
                    .font(.subheadline)
            }

            ForEach(tokens.tokens.screens.sorted(by: { $0.key < $1.key }), id: \.key) { key, value in
                NavigationLink {
                    ScreenDetailView(token: value)
                } label: {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(value.name ?? key).font(.headline)
                        if let status = value.status {
                            Text(status.capitalized).font(.subheadline).foregroundColor(.secondary)
                        }
                        if let desc = value.description, !desc.isEmpty {
                            Text(desc).font(.footnote).foregroundColor(.secondary)
                        }
                    }
                }
            }
        }
        .navigationTitle("Screens")
    }
}

struct ScreenDetailView: View {
    let token: ScreenToken

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if let screenshot = token.screenshot, let image = loadImage(named: screenshot) {
                    Image(uiImage: image).resizable().scaledToFit().cornerRadius(12)
                }

                if let metrics = token.metrics {
                    MetricsView(metrics: metrics)
                }

                if let steps = token.steps, !steps.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Steps").font(.headline)
                        ForEach(Array(steps.enumerated()), id: \.offset) { idx, step in
                            VStack(alignment: .leading, spacing: 4) {
                                Text("\(idx + 1). \(step.description ?? step.action)")
                                    .font(.subheadline)
                                if let status = step.status {
                                    Text("Status: \(status)")
                                        .font(.caption)
                                        .foregroundColor(status == "passed" ? .green : .red)
                                }
                            }
                        }
                    }
                }
            }
            .padding()
        }
        .navigationTitle(token.name ?? "Detail")
    }

    private func loadImage(named path: String) -> UIImage? {
        let components = path.split(separator: "/").map(String.init)
        guard let resource = components.last?.split(separator: ".").first else { return nil }
        return UIImage(named: String(resource))
    }
}

struct MetricsView: View {
    let metrics: ScreenMetrics

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Metrics").font(.headline)
            if let count = metrics.element_count {
                Text("Element count: \(count)").font(.subheadline)
            }
            if let accessibility = metrics.accessibility, !accessibility.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Accessibility").font(.subheadline)
                    ForEach(0..<min(accessibility.count, 5), id: \.self) { idx in
                        let entry = accessibility[idx]
                        Text("• \(entry.label ?? entry.identifier ?? "Unknown")")
                            .font(.caption)
                    }
                }
            }
        }
    }
}
