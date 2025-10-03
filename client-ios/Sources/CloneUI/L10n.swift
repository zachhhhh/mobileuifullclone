import Foundation
import SwiftUI

enum L10n {
    static let screensTitle: LocalizedStringKey = "screens.title"
    static let sectionUser: LocalizedStringKey = "section.user"
    static let sectionFeed: LocalizedStringKey = "section.feed"
    static let sectionScreens: LocalizedStringKey = "section.screens"
    static let sectionNotifications: LocalizedStringKey = "section.notifications"
    static let buttonLogout: LocalizedStringKey = "button.logout"
    static let buttonUnlockPremium: LocalizedStringKey = "button.unlockPremium"
    static let buttonPreviewNotification: LocalizedStringKey = "button.previewNotification"
    static let buttonProfileSettings: LocalizedStringKey = "button.profileSettings"

    static let userAuthenticated: LocalizedStringKey = "user.role.authenticated"
    static let userGuest: LocalizedStringKey = "user.role.guest"
    static let loading = NSLocalizedString("loading.text", bundle: .module, comment: "Loading placeholder")

    static let authTitle: LocalizedStringKey = "auth.title"
    static let authMessage = NSLocalizedString("auth.message", bundle: .module, comment: "Auth subtitle")
    static let fieldEmail: LocalizedStringKey = "field.email"
    static let fieldPassword: LocalizedStringKey = "field.password"
    static let buttonContinue: LocalizedStringKey = "button.continue"
    static let buttonRetry: LocalizedStringKey = "button.retry"

    static let onboardingTitle: LocalizedStringKey = "onboarding.title"
    static func onboardingStep(_ step: String) -> String {
        tr("onboarding.step", step)
    }

    static let stepsTitle: LocalizedStringKey = "steps.title"
    static func stepStatus(_ status: String) -> String { tr("steps.status", status) }
    static func stepBullet(_ value: String) -> String { tr("steps.bullet", value) }

    static let feedDownloadedBadge: LocalizedStringKey = "feed.downloaded"
    static func feedCardAccessibility(_ title: String, _ subtitle: String) -> String {
        tr("feed.card.accessibility", title, subtitle)
    }
    static let feedCardHint = NSLocalizedString("feed.card.hint", bundle: .module, comment: "")

    static func feedDuration(_ minutes: Int) -> String {
        tr("feed.duration", minutes)
    }
    static func feedInstructor(_ name: String) -> String {
        tr("feed.instructor", name)
    }

    static let playerBack15: LocalizedStringKey = "player.back15"
    static let playerForward15: LocalizedStringKey = "player.forward15"
    static let playerPlay: LocalizedStringKey = "player.play"
    static let playerPause: LocalizedStringKey = "player.pause"
    static let buttonMarkComplete: LocalizedStringKey = "button.markComplete"
    static let buttonDownload: LocalizedStringKey = "button.download"
    static let buttonRemoveDownload: LocalizedStringKey = "button.removeDownload"
    static let buttonClose: LocalizedStringKey = "button.close"
    static func playerPositionValue(current: Int, total: Int) -> String {
        tr("player.position.value", current, total)
    }

    static let paywallTitle: LocalizedStringKey = "paywall.title"
    static let paywallSubtitle = NSLocalizedString("paywall.subtitle", bundle: .module, comment: "")
    static let paywallBestValue: LocalizedStringKey = "paywall.bestValue"

    static let notificationPreviewTitle: LocalizedStringKey = "notification.preview.title"

    static let profileTitle: LocalizedStringKey = "profile.title"
    static let profileDisplayName: LocalizedStringKey = "profile.displayName"
    static let profileAccount: LocalizedStringKey = "profile.account"
    static let buttonSaveName: LocalizedStringKey = "button.saveName"
    static let profileFeatureFlags: LocalizedStringKey = "profile.featureFlags"
    static let togglePaywall: LocalizedStringKey = "toggle.paywall"
    static let toggleNotifications: LocalizedStringKey = "toggle.notifications"
    static let buttonApply: LocalizedStringKey = "button.apply"

    static let errorTitle: LocalizedStringKey = "error.title"
    static let genericUnknown: String = NSLocalizedString("generic.unknown", bundle: .module, comment: "")

    private static func tr(_ key: String, _ args: CVarArg...) -> String {
        let format = NSLocalizedString(key, bundle: .module, comment: "")
        return String(format: format, locale: Locale.current, arguments: args)
    }
}
