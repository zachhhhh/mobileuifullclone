import Foundation

public actor BackendClient {
    public enum ClientError: Error {
        case invalidURL
        case requestFailed
        case invalidResponse
    }

    public var baseURL: URL

    public init(baseURL: URL = URL(string: ProcessInfo.processInfo.environment["CLONE_BACKEND_URL"] ?? "http://localhost:4000")!) {
        self.baseURL = baseURL
    }

    public func health() async throws -> String {
        let url = baseURL.appending(path: "health")
        let (data, response) = try await URLSession.shared.data(from: url)
        guard
            let httpResponse = response as? HTTPURLResponse,
            httpResponse.statusCode == 200,
            let body = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            let status = body["status"] as? String
        else {
            throw ClientError.requestFailed
        }
        return status
    }

    public func session() async throws -> SessionResponse {
        let url = baseURL.appending(path: "session")
        let (data, response) = try await URLSession.shared.data(from: url)
        guard let httpResponse = response as? HTTPURLResponse, (200..<300).contains(httpResponse.statusCode) else {
            throw ClientError.requestFailed
        }
        do {
            return try JSONDecoder().decode(SessionResponse.self, from: data)
        } catch {
            throw ClientError.invalidResponse
        }
    }

    public func login(email: String, password: String) async throws {
        var request = URLRequest(url: baseURL.appending(path: "auth/login"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(["email": email, "password": password])
        let (_, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw ClientError.requestFailed
        }
    }

    public func logout() async throws {
        var request = URLRequest(url: baseURL.appending(path: "auth/logout"))
        request.httpMethod = "POST"
        let (_, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw ClientError.requestFailed
        }
    }

    public func advanceOnboarding(completed: Bool, step: String? = nil) async throws -> SessionResponse.Onboarding {
        var request = URLRequest(url: baseURL.appending(path: "onboarding/advance"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        var payload: [String: Any] = ["completed": completed]
        if let step { payload["step"] = step }
        request.httpBody = try JSONSerialization.data(withJSONObject: payload, options: [])
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw ClientError.requestFailed
        }
        let decoded = try JSONDecoder().decode(OnboardingResponse.self, from: data)
        return decoded.onboarding
    }

    public func fetchFeed() async throws -> [FeedItem] {
        let url = baseURL.appending(path: "feed")
        let (data, response) = try await URLSession.shared.data(from: url)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw ClientError.requestFailed
        }
        return try JSONDecoder().decode(FeedResponse.self, from: data).items
    }

    public func contentDetail(id: String) async throws -> ContentResponse {
        let url = baseURL.appending(path: "content/\(id)")
        let (data, response) = try await URLSession.shared.data(from: url)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw ClientError.requestFailed
        }
        return try JSONDecoder().decode(ContentResponse.self, from: data)
    }

    public func updateProgress(id: String, position: Int, completed: Bool) async throws -> ContentProgress {
        var request = URLRequest(url: baseURL.appending(path: "content/\(id)/progress"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(["position": position, "completed": completed])
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw ClientError.requestFailed
        }
        return try JSONDecoder().decode(ProgressResponse.self, from: data).progress
    }

    public func fetchPaywall() async throws -> PaywallResponse {
        let url = baseURL.appending(path: "paywall")
        let (data, response) = try await URLSession.shared.data(from: url)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw ClientError.requestFailed
        }
        return try JSONDecoder().decode(PaywallResponse.self, from: data)
    }

    public func purchase(planId: String) async throws {
        var request = URLRequest(url: baseURL.appending(path: "paywall/purchase"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(["planId": planId])
        let (_, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw ClientError.requestFailed
        }
    }

    public func notificationPreview() async throws -> NotificationPreview {
        let url = baseURL.appending(path: "notifications/preview")
        let (data, response) = try await URLSession.shared.data(from: url)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw ClientError.requestFailed
        }
        return try JSONDecoder().decode(NotificationPreviewResponse.self, from: data).notification
    }

    public func fetchProfile() async throws -> ProfileResponse {
        let url = baseURL.appending(path: "profile")
        let (data, response) = try await URLSession.shared.data(from: url)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw ClientError.requestFailed
        }
        return try JSONDecoder().decode(ProfileResponse.self, from: data)
    }

    public func updateProfile(name: String) async throws -> SessionResponse.User {
        var request = URLRequest(url: baseURL.appending(path: "profile"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(["name": name])
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw ClientError.requestFailed
        }
        return try JSONDecoder().decode(ProfileResponse.self, from: data).user
    }

    public func updateFeatureFlags(paywallEnabled: Bool? = nil, notificationsEnabled: Bool? = nil) async throws -> SessionResponse.FeatureFlags {
        var request = URLRequest(url: baseURL.appending(path: "feature-flags"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        var payload: [String: Bool] = [:]
        if let paywallEnabled { payload["paywallEnabled"] = paywallEnabled }
        if let notificationsEnabled { payload["notificationsEnabled"] = notificationsEnabled }
        request.httpBody = try JSONEncoder().encode(payload)
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw ClientError.requestFailed
        }
        return try JSONDecoder().decode(FeatureFlagResponse.self, from: data).featureFlags
    }

    public func requestDownload(id: String) async throws -> DownloadResponse {
        var request = URLRequest(url: baseURL.appending(path: "content/\(id)/download"))
        request.httpMethod = "POST"
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw ClientError.requestFailed
        }
        return try JSONDecoder().decode(DownloadResponse.self, from: data)
    }

    public func deleteDownload(id: String) async throws {
        var request = URLRequest(url: baseURL.appending(path: "content/\(id)/download"))
        request.httpMethod = "DELETE"
        let (_, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw ClientError.requestFailed
        }
    }

    public func logEvent(name: String, properties: [String: String] = [:]) async {
        var request = URLRequest(url: baseURL.appending(path: "analytics/events"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONEncoder().encode(["name": name, "properties": properties])
        _ = try? await URLSession.shared.data(for: request)
    }
}

public struct SessionResponse: Decodable {
    public struct User: Decodable {
        public let authenticated: Bool
        public let name: String?
        public let avatarUrl: String?
        public let premium: Bool
    }

    public struct Onboarding: Decodable {
        public let completed: Bool
        public let step: String
    }

    public struct FeatureFlags: Decodable {
        public let paywallEnabled: Bool
        public let notificationsEnabled: Bool
    }

    public let status: String
    public let user: User
    public let onboarding: Onboarding
    public let featureFlags: FeatureFlags
    public let timestamp: String
}

private struct OnboardingResponse: Decodable {
    let onboarding: SessionResponse.Onboarding
}

public struct FeedResponse: Decodable {
    public let status: String
    public let items: [FeedItem]
}

public struct FeedItem: Decodable, Identifiable {
    public let id: String
    public let title: String
    public let subtitle: String
    public let imageUrl: String?
    public let duration: Int?
    public let difficulty: String?
    public let tags: [String]?
}

public struct ContentResponse: Decodable {
    public let status: String
    public let content: ContentDetail
    public let progress: ContentProgress
}

public struct ContentDetail: Decodable {
    public let id: String
    public let title: String
    public let description: String
    public let audioUrl: String
    public let duration: Int
    public let instructor: String
    public let coverUrl: String?
}

public struct ContentProgress: Decodable {
    public let position: Int
    public let completed: Bool
    public let updatedAt: String?
}

public struct PaywallResponse: Decodable {
    public let status: String
    public let paywallEnabled: Bool
    public let plans: [PaywallPlan]
    public let premium: Bool
}

public struct PaywallPlan: Decodable, Identifiable {
    public let id: String
    public let title: String
    public let priceLocalized: String
    public let trial: String?
    public let bestValue: Bool
}

public struct NotificationPreview: Decodable {
    public let title: String
    public let body: String
    public let deepLink: String
}

private struct NotificationPreviewResponse: Decodable {
    let status: String
    let notification: NotificationPreview
}

public struct ProfileResponse: Decodable {
    public let status: String
    public let user: SessionResponse.User
    public let featureFlags: SessionResponse.FeatureFlags
}

private struct FeatureFlagResponse: Decodable {
    let status: String
    let featureFlags: SessionResponse.FeatureFlags
}

private struct ProgressResponse: Decodable {
    let status: String
    let progress: ContentProgress
}

public struct DownloadResponse: Decodable {
    public let status: String
    public let download: DownloadInfo
}

public struct DownloadInfo: Decodable {
    public let id: String
    public let status: String
    public let downloadedAt: String
}
