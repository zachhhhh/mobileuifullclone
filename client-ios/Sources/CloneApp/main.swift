import SwiftUI
import CloneUI
import UIKit

@main
struct CloneApp: App {
    @StateObject private var tokens = TokenStore()
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            NavigationStack {
                RootView()
                    .environmentObject(appState)
                    .task {
                        await appState.refresh()
                    }
            }
            .environmentObject(tokens)
        }
    }
}

struct RootView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        switch appState.phase {
        case .loading:
            FeedSkeletonList()
        case .needsAuth(let message):
            AuthRequiredView(errorMessage: message) { email, password in
                await appState.login(email: email, password: password)
            }
        case .onboarding(let step):
            OnboardingView(step: step) {
                await appState.completeOnboarding()
            }
        case .home(let session, let feed):
            ScreenListView(session: session, feed: feed) {
                await appState.logout()
            }
        case .error(let message):
            ErrorView(message: message, onRetry: { await appState.refresh() })
        }
    }
}

struct AuthRequiredView: View {
    @State private var email: String = "user@example.com"
    @State private var password: String = "password123"
    @State private var isLoading = false
    let errorMessage: String?
    let onSubmit: (String, String) async -> Void

    var body: some View {
        VStack(spacing: 20) {
            Text(L10n.authTitle).font(.largeTitle)
            Text(L10n.authMessage)
                .font(.body)
                .multilineTextAlignment(.center)
                .foregroundColor(.secondary)
            if let message = errorMessage {
                Text(message)
                    .font(.footnote)
                    .foregroundColor(.red)
                    .multilineTextAlignment(.center)
            }
            TextField(L10n.fieldEmail, text: $email)
                .keyboardType(.emailAddress)
                .textInputAutocapitalization(.never)
                .disableAutocorrection(true)
                .textFieldStyle(.roundedBorder)
            SecureField(L10n.fieldPassword, text: $password)
                .textFieldStyle(.roundedBorder)
            Button {
                Task {
                    isLoading = true
                    await onSubmit(email, password)
                    isLoading = false
                }
            } label: {
                if isLoading {
                    ProgressView()
                } else {
                    Text(L10n.buttonContinue)
                }
            }
            .buttonStyle(.borderedProminent)
            .accessibilityIdentifier("loginSubmitButton")
        }
        .padding()
        .navigationTitle(L10n.authTitle)
    }
}

struct OnboardingView: View {
    let step: String
    let onContinue: () async -> Void

    var body: some View {
        VStack(spacing: 24) {
            Text(L10n.onboardingTitle)
                .font(.largeTitle)
            Text(L10n.onboardingStep(step.capitalized))
                .font(.title3)
            Button(L10n.buttonContinue) {
                Task { await onContinue() }
            }
            .buttonStyle(.borderedProminent)
        }
        .padding()
    }
}

struct ErrorView: View {
    let message: String
    let onRetry: () async -> Void

    var body: some View {
        VStack(spacing: 16) {
            Text(L10n.errorTitle).font(.title2)
            Text(message).multilineTextAlignment(.center)
                .foregroundColor(.secondary)
            Button(L10n.buttonRetry) {
                Task { await onRetry() }
            }
        }
        .padding()
    }
}

struct ScreenListView: View {
    @EnvironmentObject private var tokens: TokenStore
    @EnvironmentObject private var appState: AppState
    let session: SessionResponse
    let feed: [FeedItem]
    let onLogout: () async -> Void
    @State private var selectedItem: FeedItem?
    @State private var showPaywall = false
    @State private var loadingPaywall = false
    @State private var paywallPlans: [PaywallPlan] = []
    @State private var showNotification = false
    @State private var showProfile = false

    var body: some View {
        List {
            Section(header: Text(L10n.sectionUser)) {
                Text(session.user.name ?? "Anonymous")
                Text(session.user.authenticated ? L10n.userAuthenticated : L10n.userGuest)
                    .foregroundColor(.secondary)
                Button(L10n.buttonLogout) {
                    Task { await onLogout() }
                }
                .buttonStyle(.bordered)
                if session.featureFlags.paywallEnabled && !(session.user.premium) {
                    Button {
                        Task {
                            loadingPaywall = true
                            if let plans = try? await appState.loadPaywall() {
                                paywallPlans = plans
                                showPaywall = true
                            }
                            loadingPaywall = false
                        }
                    } label: {
                        if loadingPaywall {
                            ProgressView()
                        } else {
                            Text(L10n.buttonUnlockPremium)
                        }
                    }
                    .buttonStyle(.borderedProminent)
                }
            }

            Section(header: Text(L10n.sectionFeed)) {
                ForEach(feed) { item in
                    FeedCard(item: item, isDownloaded: appState.downloads.contains(item.id))
                        .onTapGesture {
                            Task {
                                await appState.loadContent(id: item.id)
                                selectedItem = item
                            }
                        }
                }
            }

            Section(header: Text(L10n.sectionScreens)) {
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

            if session.featureFlags.notificationsEnabled {
                Section(header: Text(L10n.sectionNotifications)) {
                    Button(L10n.buttonPreviewNotification) {
                        Task {
                            await appState.loadNotificationPreview()
                            showNotification = true
                        }
                    }
                }
            }
        }
        .navigationTitle(L10n.screensTitle)
        .animation(.easeInOut(duration: 0.25), value: feed.count)
        .sheet(item: $selectedItem) { item in
            if let content = appState.currentContent {
                FeedDetailView(
                    item: item,
                    content: content,
                    progress: appState.currentProgress,
                    isDownloaded: appState.downloads.contains(item.id),
                    onUpdateProgress: { position, completed in
                        Task { await appState.updateProgress(id: item.id, position: position, completed: completed) }
                    },
                    onDownload: {
                        Task { await appState.downloadContent(id: item.id) }
                    },
                    onRemoveDownload: {
                        Task { await appState.removeDownload(id: item.id) }
                    },
                    onDismiss: {
                        appState.resetContent()
                    }
                )
            } else {
                ProgressView(L10n.loading).padding()
            }
        }
        .sheet(isPresented: $showPaywall) {
            PaywallView(plans: paywallPlans) { plan in
                Task {
                    await appState.purchase(planId: plan.id)
                    showPaywall = false
                }
            }
        }
        .sheet(isPresented: $showNotification) {
            if let preview = appState.notificationPreview {
                NotificationPreviewView(preview: preview)
            } else {
                ProgressView(L10n.loading)
                    .padding()
            }
        }
        .sheet(isPresented: $showProfile) {
            ProfileView(profile: appState.profile, featureFlags: session.featureFlags) { newName in
                Task { await appState.updateName(newName) }
            } onToggleFlags: { paywall, notifications in
                Task { await appState.updateFeatureFlags(paywallEnabled: paywall, notificationsEnabled: notifications) }
            } onReload: {
                Task { await appState.loadProfile() }
            }
        }
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button(action: {
                    Task {
                        await appState.loadProfile()
                        showProfile = true
                    }
                }) {
                    Image(systemName: "person.crop.circle")
                        .accessibilityLabel(Text(L10n.buttonProfileSettings))
                }
            }
        }
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
                        Text(L10n.stepsTitle).font(.headline)
                        ForEach(Array(steps.enumerated()), id: \.offset) { idx, step in
                            VStack(alignment: .leading, spacing: 4) {
                                Text("\(idx + 1). \(step.description ?? step.action)")
                                    .font(.subheadline)
                                if let status = step.status {
                                    Text(L10n.stepStatus(status))
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

struct FeedCard: View {
    let item: FeedItem
    let isDownloaded: Bool

    var body: some View {
        ZStack(alignment: .bottomLeading) {
            if let imageUrl = item.imageUrl, let url = URL(string: imageUrl) {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .empty:
                        Color.gray.opacity(0.2)
                            .overlay { ProgressView() }
                    case .success(let image):
                        image.resizable().scaledToFill()
                    case .failure:
                        Color.gray.opacity(0.4)
                    @unknown default:
                        Color.gray
                    }
                }
                .frame(height: 150)
                .clipped()
                .cornerRadius(12)
            } else {
                RoundedRectangle(cornerRadius: 12)
                    .fill(Color.blue.opacity(0.1))
                    .frame(height: 150)
            }

            VStack(alignment: .leading, spacing: 6) {
                if isDownloaded {
                    Label(L10n.feedDownloadedBadge, systemImage: "arrow.down.circle.fill")
                        .font(.caption)
                        .padding(6)
                        .background(Color.white.opacity(0.85))
                        .foregroundColor(.blue)
                        .cornerRadius(8)
                }
                Text(item.title)
                    .font(.headline)
                    .foregroundColor(.white)
                Text(item.subtitle)
                    .font(.subheadline)
                    .foregroundColor(.white.opacity(0.8))
            }
            .padding()
        }
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.black.opacity(0.05))
        )
        .padding(.vertical, 6)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text(L10n.feedCardAccessibility(item.title, item.subtitle)))
        .accessibilityHint(Text(L10n.feedCardHint))
    }
}

struct FeedSkeletonCard: View {
    var body: some View {
        RoundedRectangle(cornerRadius: 12)
            .fill(LinearGradient(
                gradient: Gradient(colors: [Color.gray.opacity(0.2), Color.gray.opacity(0.35), Color.gray.opacity(0.2)]),
                startPoint: .leading,
                endPoint: .trailing
            ))
            .frame(height: 150)
            .shimmering()
    }
}

struct FeedSkeletonList: View {
    var body: some View {
        List {
            Section("Feed") {
                ForEach(0..<3, id: \.self) { _ in
                    FeedSkeletonCard()
                        .listRowSeparator(.hidden)
                }
            }
        }
        .listStyle(.insetGrouped)
        .redacted(reason: .placeholder)
    }
}

private struct ShimmerModifier: ViewModifier {
    @State private var phase: CGFloat = 0

    func body(content: Content) -> some View {
        content
            .overlay(
                LinearGradient(
                    gradient: Gradient(colors: [.clear, Color.white.opacity(0.4), .clear]),
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .blendMode(.plusLighter)
                .mask(content)
                .opacity(0.8)
                .offset(x: phase)
            )
            .onAppear {
                withAnimation(.linear(duration: 1.2).repeatForever(autoreverses: false)) {
                    phase = 200
                }
            }
    }
}

private extension View {
    func shimmering() -> some View {
        modifier(ShimmerModifier())
    }
}

struct FeedDetailView: View {
    @Environment(\.dismiss) private var dismiss
    let item: FeedItem
    let content: ContentDetail
    let progress: ContentProgress?
    let isDownloaded: Bool
    let onUpdateProgress: (Int, Bool) -> Void
    let onDownload: () -> Void
    let onRemoveDownload: () -> Void
    let onDismiss: () -> Void
    @State private var position: Double = 0
    @State private var isPlaying = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                artwork
                Text(content.title)
                    .font(.title2)
                    .bold()
                Text(content.description)
                    .font(.body)
                infoRow
                playerControls
            }
            .padding()
        }
        .presentationDetents([.medium, .large])
        .onAppear {
            position = Double(progress?.position ?? 0)
        }
        .onDisappear {
            onDismiss()
        }
    }

    private var artwork: some View {
        Group {
            if let cover = content.coverUrl, let url = URL(string: cover) {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .empty:
                        ProgressView()
                    case .success(let image):
                        image.resizable().aspectRatio(contentMode: .fit)
                    case .failure:
                        Color.gray.opacity(0.3)
                    @unknown default:
                        Color.gray
                    }
                }
            } else {
                RoundedRectangle(cornerRadius: 16)
                    .fill(Color.blue.opacity(0.2))
                    .frame(height: 180)
            }
        }
        .cornerRadius(16)
    }

    private var infoRow: some View {
        HStack {
            Label(L10n.feedDuration(content.duration / 60), systemImage: "clock")
            Spacer()
            Text(L10n.feedInstructor(content.instructor))
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }

    private var playerControls: some View {
        VStack(alignment: .leading, spacing: 12) {
            Slider(
                value: Binding(get: { position }, set: { newValue in position = newValue }),
                in: 0...Double(content.duration),
                onEditingChanged: { editing in
                    if !editing {
                        onUpdateProgress(Int(position), false)
                    }
                }
            )
            .tint(.blue)
            .accessibilityLabel(Text(L10n.playerPlay))
            .accessibilityValue(Text(L10n.playerPositionValue(Int(position), content.duration)))

            HStack {
                Button {
                    let newPosition = max(position - 15, 0)
                    position = newPosition
                    onUpdateProgress(Int(newPosition), false)
                } label: { Label(L10n.playerBack15, systemImage: "gobackward.15") }
                Spacer()
                Button {
                    isPlaying.toggle()
                } label: {
                    Image(systemName: isPlaying ? "pause.circle.fill" : "play.circle.fill")
                        .font(.system(size: 44))
                        .accessibilityLabel(Text(isPlaying ? L10n.playerPause : L10n.playerPlay))
                }
                Spacer()
                Button {
                    let newPosition = min(position + 15, Double(content.duration))
                    position = newPosition
                    onUpdateProgress(Int(newPosition), false)
                } label: { Label(L10n.playerForward15, systemImage: "goforward.15") }
            }

            Button(L10n.buttonMarkComplete) {
                position = Double(content.duration)
                onUpdateProgress(content.duration, true)
            }
            .buttonStyle(.bordered)

            Button(isDownloaded ? L10n.buttonRemoveDownload : L10n.buttonDownload) {
                if isDownloaded { onRemoveDownload() } else { onDownload() }
            }
            .buttonStyle(.borderedProminent)
            Button(L10n.buttonClose) {
                dismiss()
                onDismiss()
            }
            .buttonStyle(.borderless)
            .padding(.top, 8)
        }
    }
}

struct PaywallView: View {
    let plans: [PaywallPlan]
    let onSelect: (PaywallPlan) -> Void

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                Text(L10n.paywallTitle)
                    .font(.largeTitle)
                    .bold()
                Text(L10n.paywallSubtitle)
                    .foregroundColor(.secondary)
                ForEach(plans) { plan in
                    Button {
                        onSelect(plan)
                    } label: {
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text(plan.title).font(.headline)
                                if plan.bestValue {
                                    Spacer()
                                    Text(L10n.paywallBestValue)
                                        .font(.caption)
                                        .padding(6)
                                        .background(Color.orange.opacity(0.2))
                                        .cornerRadius(8)
                                }
                            }
                            Text(plan.priceLocalized)
                                .font(.subheadline)
                            if let trial = plan.trial {
                                Text(trial)
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                        }
                        .padding()
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(RoundedRectangle(cornerRadius: 14).fill(Color.blue.opacity(0.1)))
                    }
                    .buttonStyle(.plain)
                }
                Spacer()
            }
            .padding()
            .navigationTitle("Premium")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

struct NotificationPreviewView: View {
    let preview: NotificationPreview
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 16) {
            Text(preview.title)
                .font(.headline)
            Text(preview.body)
                .font(.body)
                .multilineTextAlignment(.center)
            Text(preview.deepLink)
                .font(.caption)
                .foregroundColor(.secondary)
            Button(L10n.buttonClose) { dismiss() }
                .buttonStyle(.borderedProminent)
        }
        .padding()
    }
}

struct ProfileView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var name: String
    @State private var paywallEnabled: Bool
    @State private var notificationsEnabled: Bool
    let onUpdateName: (String) -> Void
    let onToggleFlags: (Bool, Bool) -> Void
    let onReload: () -> Void

    init(profile: ProfileResponse?, featureFlags: SessionResponse.FeatureFlags, onUpdateName: @escaping (String) -> Void, onToggleFlags: @escaping (Bool, Bool) -> Void, onReload: @escaping () -> Void) {
        _name = State(initialValue: profile?.user.name ?? "")
        _paywallEnabled = State(initialValue: profile?.featureFlags.paywallEnabled ?? featureFlags.paywallEnabled)
        _notificationsEnabled = State(initialValue: profile?.featureFlags.notificationsEnabled ?? featureFlags.notificationsEnabled)
        self.onUpdateName = onUpdateName
        self.onToggleFlags = onToggleFlags
        self.onReload = onReload
    }

    var body: some View {
        NavigationStack {
            Form {
                Section(L10n.profileAccount) {
                    TextField(L10n.profileDisplayName, text: $name)
                    Button(L10n.buttonSaveName) {
                        onUpdateName(name)
                        dismiss()
                    }
                }

                Section(header: Text(L10n.profileFeatureFlags)) {
                    Toggle(L10n.togglePaywall, isOn: $paywallEnabled)
                    Toggle(L10n.toggleNotifications, isOn: $notificationsEnabled)
                    Button(L10n.buttonApply) {
                        onToggleFlags(paywallEnabled, notificationsEnabled)
                        onReload()
                    }
                }
            }
            .navigationTitle(L10n.profileTitle)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(L10n.buttonClose) { dismiss() }
                }
            }
        }
    }
}

struct MetricsView: View {
    let metrics: ScreenMetrics

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(L10n.metricsTitle).font(.headline)
            if let count = metrics.element_count {
                Text(L10n.metricsElementCount(count)).font(.subheadline)
            }
            if let accessibility = metrics.accessibility, !accessibility.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Text(L10n.metricsAccessibilityTitle).font(.subheadline)
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
