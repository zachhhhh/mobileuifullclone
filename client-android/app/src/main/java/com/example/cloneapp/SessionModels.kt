package com.example.cloneapp

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class SessionResponse(
    val status: String,
    val user: User,
    val onboarding: Onboarding,
    @SerialName("featureFlags") val featureFlags: FeatureFlags,
    val timestamp: String
)

@Serializable
data class User(
    val authenticated: Boolean,
    val name: String? = null,
    @SerialName("avatarUrl") val avatarUrl: String? = null,
    val premium: Boolean = false
)

@Serializable
data class Onboarding(
    val completed: Boolean,
    val step: String
)

@Serializable
data class FeatureFlags(
    @SerialName("paywallEnabled") val paywallEnabled: Boolean,
    @SerialName("notificationsEnabled") val notificationsEnabled: Boolean
)

@Serializable
data class OnboardingResponse(
    val onboarding: Onboarding
)

@Serializable
data class FeedResponse(
    val status: String,
    val items: List<FeedItem>
)

@Serializable
data class FeedItem(
    val id: String,
    val title: String,
    val subtitle: String,
    val imageUrl: String? = null,
    val duration: Int? = null,
    val difficulty: String? = null,
    val tags: List<String>? = null
)

@Serializable
data class PaywallResponse(
    val status: String,
    @SerialName("paywallEnabled") val paywallEnabled: Boolean,
    val plans: List<PaywallPlan>,
    val premium: Boolean
)

@Serializable
data class PaywallPlan(
    val id: String,
    val title: String,
    @SerialName("priceLocalized") val priceLocalized: String,
    val trial: String? = null,
    val bestValue: Boolean = false
)

@Serializable
data class NotificationPreviewResponse(
    val status: String,
    val notification: NotificationPreview
)

@Serializable
data class NotificationPreview(
    val title: String,
    val body: String,
    val deepLink: String
)

@Serializable
data class ProfileResponse(
    val status: String,
    val user: User,
    @SerialName("featureFlags") val featureFlags: FeatureFlags
)

@Serializable
data class FeatureFlagResponse(
    val status: String,
    @SerialName("featureFlags") val featureFlags: FeatureFlags
)

@Serializable
data class ContentResponse(
    val status: String,
    val content: ContentDetail,
    val progress: ContentProgress
)

@Serializable
data class ContentDetail(
    val id: String,
    val title: String,
    val description: String,
    val audioUrl: String,
    val duration: Int,
    val instructor: String,
    val coverUrl: String? = null
)

@Serializable
data class ContentProgress(
    val position: Int,
    val completed: Boolean,
    val updatedAt: String? = null
)

@Serializable
data class ProgressResponse(
    val status: String,
    val progress: ContentProgress
)


@Serializable
data class DownloadResponse(
    val status: String,
    val download: DownloadInfo
)

@Serializable
data class DownloadInfo(
    val id: String,
    val status: String,
    val downloadedAt: String
)
