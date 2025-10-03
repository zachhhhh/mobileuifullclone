import Foundation
import Combine

public enum AppPhase: Equatable {
    case loading
    case needsAuth(message: String? = nil)
    case onboarding(step: String)
    case home(SessionResponse, [FeedItem])
    case error(String)
}

@MainActor
public final class AppState: ObservableObject {
    @Published public private(set) var phase: AppPhase = .loading
    @Published public private(set) var paywallPlans: [PaywallPlan] = []
    @Published public private(set) var notificationPreview: NotificationPreview?
    @Published public private(set) var profile: ProfileResponse?
    @Published public private(set) var currentContent: ContentDetail?
    @Published public private(set) var currentProgress: ContentProgress?
    @Published public private(set) var downloads: Set<String> = []
    private let backend: BackendClient

    public init(backend: BackendClient = BackendClient()) {
        self.backend = backend
    }

    public func refresh() async {
        phase = .loading
        do {
            let session = try await backend.session()
            if !session.user.authenticated {
                phase = .needsAuth()
                return
            }
            if !session.onboarding.completed {
                phase = .onboarding(step: session.onboarding.step)
                return
            }
            let feed = try await backend.fetchFeed()
            paywallPlans = []
            phase = .home(session, feed)
            profile = try? backend.fetchProfile()
        } catch {
            phase = .error(error.localizedDescription)
        }
    }

    public func login(email: String, password: String) async {
        phase = .loading
        do {
            try await backend.login(email: email, password: password)
            await refresh()
        } catch {
            phase = .needsAuth(message: error.localizedDescription)
        }
    }

    public func logout() async {
        do { try await backend.logout() } catch { }
        phase = .needsAuth()
    }

    public func completeOnboarding() async {
        phase = .loading
        do {
            _ = try await backend.advanceOnboarding(completed: true)
            await refresh()
        } catch {
            phase = .error(error.localizedDescription)
        }
    }

    public func loadPaywall() async throws -> [PaywallPlan] {
        let response = try await backend.fetchPaywall()
        paywallPlans = response.plans
        await backend.logEvent(name: "paywall_view")
        return response.plans
    }

    public func purchase(planId: String) async {
        do {
            try await backend.purchase(planId: planId)
            await backend.logEvent(name: "purchase", properties: ["plan_id": planId])
            await refresh()
        } catch {
            phase = .error(error.localizedDescription)
        }
    }

    public func loadNotificationPreview() async {
        do {
            notificationPreview = try await backend.notificationPreview()
            await backend.logEvent(name: "notification_preview")
        } catch {
            phase = .error(error.localizedDescription)
        }
    }

    public func loadProfile() async {
        do {
            profile = try await backend.fetchProfile()
        } catch {
            phase = .error(error.localizedDescription)
        }
    }

    public func updateName(_ name: String) async {
        do {
            _ = try await backend.updateProfile(name: name)
            await refresh()
        } catch {
            phase = .error(error.localizedDescription)
        }
    }

    public func updateFeatureFlags(paywallEnabled: Bool? = nil, notificationsEnabled: Bool? = nil) async {
        do {
            _ = try await backend.updateFeatureFlags(paywallEnabled: paywallEnabled, notificationsEnabled: notificationsEnabled)
            await backend.logEvent(name: "feature_flags_update", properties: ["paywall": String(paywallEnabled ?? false), "notifications": String(notificationsEnabled ?? false)])
            await refresh()
        } catch {
            phase = .error(error.localizedDescription)
        }
    }

    public func loadContent(id: String) async {
        do {
            let response = try await backend.contentDetail(id: id)
            currentContent = response.content
            currentProgress = response.progress
            if downloads.contains(id) {
                currentProgress = ContentProgress(position: response.content.duration, completed: true, updatedAt: response.progress.updatedAt)
            }
            await backend.logEvent(name: "content_view", properties: ["content_id": id])
        } catch {
            phase = .error(error.localizedDescription)
        }
    }

    public func updateProgress(id: String, position: Int, completed: Bool) async {
        do {
            currentProgress = try await backend.updateProgress(id: id, position: position, completed: completed)
            await backend.logEvent(name: "content_progress", properties: ["content_id": id, "completed": String(completed)])
        } catch {
            phase = .error(error.localizedDescription)
        }
    }

    public func resetContent() {
        currentContent = nil
        currentProgress = nil
    }

    public func logEvent(_ name: String, properties: [String: String] = [:]) {
        Task { await backend.logEvent(name: name, properties: properties) }
    }

    public func downloadContent(id: String) async {
        do {
            let response = try await backend.requestDownload(id: id)
            downloads.insert(response.download.id)
            await backend.logEvent(name: "download", properties: ["content_id": id])
        } catch {
            phase = .error(error.localizedDescription)
        }
    }

    public func removeDownload(id: String) async {
        do {
            try await backend.deleteDownload(id: id)
            downloads.remove(id)
            await backend.logEvent(name: "download_delete", properties: ["content_id": id])
        } catch {
            phase = .error(error.localizedDescription)
        }
    }
}
