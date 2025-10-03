package com.example.cloneapp

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TextField
import androidx.compose.material3.Slider
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.semantics.progressBarRangeInfo
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.value
import androidx.compose.ui.semantics.ProgressBarRangeInfo
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.res.stringResource
import androidx.compose.foundation.background
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.isSystemInDarkTheme
import kotlin.math.max
import kotlin.math.min
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.animateItemPlacement
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    val backend = remember { BackendClient.default(applicationContext) }
                    TokenScreen(
                        loadTokens = { TokenStore.load(applicationContext) },
                        backend = backend
                    )
                }
            }
        }
    }
}

enum class AppPhase {
    Loading,
    NeedsAuth,
    Onboarding,
    Home,
    Error
}

data class UiState(
    val phase: AppPhase = AppPhase.Loading,
    val session: SessionResponse? = null,
    val tokens: DesignTokens = DesignTokens(),
    val feed: List<FeedItem> = emptyList(),
    val message: String? = null,
    val notificationPreview: NotificationPreview? = null,
    val profile: ProfileResponse? = null,
    val currentContent: ContentDetail? = null,
    val currentProgress: ContentProgress? = null,
    val downloads: Set<String> = emptySet()
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TokenScreen(
    loadTokens: suspend () -> DesignTokens,
    backend: BackendClient
) {
    var state by remember { mutableStateOf(UiState()) }
    val scope = rememberCoroutineScope()
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var selectedItem by remember { mutableStateOf<FeedItem?>(null) }
    val paywallState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var showPaywall by remember { mutableStateOf(false) }
    var paywallPlans by remember { mutableStateOf<List<PaywallPlan>>(emptyList()) }
    var notificationPreview by remember { mutableStateOf<NotificationPreview?>(null) }
    var showNotification by remember { mutableStateOf(false) }
    val profileSheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var showProfile by remember { mutableStateOf(false) }
    suspend fun refresh() {
        try {
            val tokens = loadTokens()
            val session = backend.session()
            val phase = when {
                !session.user.authenticated -> AppPhase.NeedsAuth
                !session.onboarding.completed -> AppPhase.Onboarding
                else -> AppPhase.Home
            }
            val feed = if (phase == AppPhase.Home) backend.fetchFeed() else emptyList()
            val profile = if (phase == AppPhase.Home) backend.fetchProfile() else null
            state = UiState(phase = phase, session = session, tokens = tokens, feed = feed, profile = profile, downloads = state.downloads)
        } catch (t: Throwable) {
            state = UiState(phase = AppPhase.Error, message = t.message)
        }
    }

    LaunchedEffect(Unit) {
        refresh()
    }

    suspend fun handleLogin(email: String, password: String) {
        state = state.copy(phase = AppPhase.Loading)
        try {
            backend.login(email, password)
            val session = backend.session()
            val tokens = loadTokens()
            val feed = backend.fetchFeed()
            val profile = backend.fetchProfile()
            state = UiState(phase = AppPhase.Home, session = session, tokens = tokens, feed = feed, profile = profile, downloads = state.downloads)
        } catch (t: Throwable) {
            state = UiState(phase = AppPhase.NeedsAuth, message = t.message)
        }
    }

    suspend fun handleOnboardingComplete() {
        state = state.copy(phase = AppPhase.Loading)
        try {
            backend.advanceOnboarding(true)
            val session = backend.session()
            val tokens = loadTokens()
            val feed = backend.fetchFeed()
            val profile = backend.fetchProfile()
            state = UiState(phase = AppPhase.Home, session = session, tokens = tokens, feed = feed, profile = profile, downloads = state.downloads)
        } catch (t: Throwable) {
            state = UiState(phase = AppPhase.Error, message = t.message)
        }
    }

    suspend fun handleLogout() {
        backend.logout()
        state = UiState(phase = AppPhase.NeedsAuth)
    }

    suspend fun openPaywall() {
        try {
            val response = backend.fetchPaywall()
            if (!response.paywallEnabled) return
            paywallPlans = response.plans
            showPaywall = true
            paywallState.show()
            backend.logEvent(name = "paywall_view")
        } catch (t: Throwable) {
            state = UiState(phase = AppPhase.Error, message = t.message)
        }
    }

    suspend fun purchasePlan(planId: String) {
        try {
            backend.purchase(planId)
            showPaywall = false
            paywallState.hide()
            refresh()
            backend.logEvent(name = "purchase", properties = mapOf("plan_id" to planId))
        } catch (t: Throwable) {
            state = UiState(phase = AppPhase.Error, message = t.message)
        }
    }

    suspend fun downloadContent(id: String) {
        try {
            backend.requestDownload(id)
            backend.logEvent(name = "download", properties = mapOf("content_id" to id))
            state = state.copy(downloads = state.downloads + id)
        } catch (t: Throwable) {
            state = UiState(phase = AppPhase.Error, message = t.message)
        }
    }

    suspend fun removeDownload(id: String) {
        try {
            backend.deleteDownload(id)
            backend.logEvent(name = "download_delete", properties = mapOf("content_id" to id))
            state = state.copy(downloads = state.downloads - id)
        } catch (t: Throwable) {
            state = UiState(phase = AppPhase.Error, message = t.message)
        }
    }

    suspend fun loadNotificationPreview() {
        try {
            val preview = backend.notificationPreview()
            notificationPreview = preview
            showNotification = true
            backend.logEvent(name = "notification_preview")
        } catch (t: Throwable) {
            state = UiState(phase = AppPhase.Error, message = t.message)
        }
    }

    when (state.phase) {
        AppPhase.Loading -> FeedSkeletonList()
        AppPhase.NeedsAuth -> AuthRequiredView(state.message) { email, password ->
            scope.launch { handleLogin(email, password) }
        }
        AppPhase.Onboarding -> OnboardingView(step = state.session?.onboarding?.step ?: "welcome") {
            scope.launch { handleOnboardingComplete() }
        }
        AppPhase.Home -> HomeView(
            state,
            onItemSelected = { item ->
                scope.launch {
                    val detail = backend.contentDetail(item.id)
                    backend.logEvent(name = "content_view", properties = mapOf("content_id" to item.id))
                    state = state.copy(currentContent = detail.content, currentProgress = detail.progress)
                    selectedItem = item
                    sheetState.show()
                }
            },
            onUnlockPremium = { scope.launch { openPaywall() } },
            onPreviewNotification = { scope.launch { loadNotificationPreview() } },
            onOpenProfile = {
                scope.launch {
                    val profile = backend.fetchProfile()
                    state = state.copy(profile = profile)
                    showProfile = true
                    profileSheetState.show()
                }
            }
        ) {
            scope.launch { handleLogout() }
        }
        AppPhase.Error -> ErrorView(state.message ?: "Unknown error") {
            scope.launch { refresh() }
        }
    }

    if (selectedItem != null && state.currentContent != null) {
        ModalBottomSheet(
            onDismissRequest = {
                selectedItem = null
                state = state.copy(currentContent = null, currentProgress = null)
            },
            sheetState = sheetState
        ) {
            ContentDetailSheet(
                item = selectedItem!!,
                content = state.currentContent!!,
                progress = state.currentProgress,
                onSeekFinished = { newPos ->
                    scope.launch {
                        val updated = backend.updateProgress(selectedItem!!.id, newPos, false)
                        state = state.copy(currentProgress = updated)
                        backend.logEvent(name = "content_progress", properties = mapOf("content_id" to selectedItem!!.id, "completed" to "false"))
                    }
                },
                onComplete = {
                    scope.launch {
                        val updated = backend.updateProgress(selectedItem!!.id, state.currentContent!!.duration, true)
                        state = state.copy(currentProgress = updated)
                        backend.logEvent(name = "content_progress", properties = mapOf("content_id" to selectedItem!!.id, "completed" to "true"))
                    }
                },
                onClose = {
                    selectedItem = null
                    state = state.copy(currentContent = null, currentProgress = null)
                }
            )
        }
    }

    if (showPaywall) {
        ModalBottomSheet(
            onDismissRequest = {
                showPaywall = false
                scope.launch { paywallState.hide() }
            },
            sheetState = paywallState
        ) {
            PaywallSheet(plans = paywallPlans, onSelect = { plan ->
                scope.launch { purchasePlan(plan.id) }
            })
        }
    }

    if (showNotification && notificationPreview != null) {
        AlertDialog(
            onDismissRequest = { showNotification = false },
            confirmButton = {
                TextButton(onClick = { showNotification = false }) {
                    Text(stringResource(R.string.button_close))
                }
            },
            title = { Text(notificationPreview!!.title) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(notificationPreview!!.body)
                    Text(notificationPreview!!.deepLink, style = MaterialTheme.typography.labelSmall)
                }
            }
        )
    }

    if (showProfile) {
        ModalBottomSheet(
            onDismissRequest = {
                showProfile = false
                scope.launch { profileSheetState.hide() }
            },
            sheetState = profileSheetState
        ) {
            ProfileSheet(
                profile = state.profile,
                onSave = { name ->
                    scope.launch {
                        backend.updateProfileName(name)
                        backend.logEvent(name = "profile_update")
                        showProfile = false
                        profileSheetState.hide()
                        refresh()
                    }
                },
                onToggle = { paywall, notifications ->
                    scope.launch {
                        backend.updateFeatureFlags(paywallEnabled = paywall, notificationsEnabled = notifications)
                        backend.logEvent(name = "feature_flags_update", properties = mapOf("paywall" to paywall.toString(), "notifications" to notifications.toString()))
                        refresh()
                    }
                }
            )
        }
    }
}

@Composable
fun LoadingView() {
    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        CircularProgressIndicator()
        Spacer(Modifier.height(12.dp))
        Text(stringResource(R.string.loading_text))
    }
}

@Composable
fun AuthRequiredView(errorMessage: String?, onSubmit: (String, String) -> Unit) {
    var email by remember { mutableStateOf("user@example.com") }
    var password by remember { mutableStateOf("password123") }
    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(stringResource(R.string.auth_title), style = MaterialTheme.typography.titleLarge)
        Spacer(Modifier.height(12.dp))
        if (errorMessage != null) {
            Text(errorMessage, color = MaterialTheme.colorScheme.error)
            Spacer(Modifier.height(8.dp))
        }
        TextField(
            value = email,
            onValueChange = { email = it },
            label = { Text(stringResource(R.string.field_email)) }
        )
        Spacer(Modifier.height(8.dp))
        TextField(
            value = password,
            onValueChange = { password = it },
            label = { Text(stringResource(R.string.field_password)) },
            visualTransformation = PasswordVisualTransformation()
        )
        Spacer(Modifier.height(12.dp))
        Button(onClick = { onSubmit(email, password) }) {
            Text(stringResource(R.string.button_continue))
        }
    }
}

@Composable
fun OnboardingView(step: String, onContinue: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(stringResource(R.string.onboarding_title), style = MaterialTheme.typography.titleLarge)
        Spacer(Modifier.height(8.dp))
        Text(stringResource(R.string.onboarding_step, step), style = MaterialTheme.typography.bodyMedium)
        Spacer(Modifier.height(12.dp))
        Button(onClick = onContinue) {
            Text(stringResource(R.string.button_continue))
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun HomeView(
    state: UiState,
    onItemSelected: (FeedItem) -> Unit,
    onUnlockPremium: () -> Unit,
    onPreviewNotification: () -> Unit,
    onOpenProfile: () -> Unit,
    onLogout: () -> Unit
) {
    val session = state.session
    val tokens = state.tokens
    val feed = state.feed
    LazyColumn {
        item {
            Text(stringResource(R.string.welcome_user, session?.user?.name ?: stringResource(R.string.user_guest)), style = MaterialTheme.typography.titleLarge)
            Spacer(Modifier.height(8.dp))
            Button(onLogout) { Text(stringResource(R.string.button_logout)) }
            Spacer(Modifier.height(12.dp))
            if (session != null && session.featureFlags.paywallEnabled && !session.user.premium) {
                Button(onUnlockPremium) {
                    Text(stringResource(R.string.button_unlock_premium))
                }
                Spacer(Modifier.height(12.dp))
            }
            if (session?.featureFlags?.notificationsEnabled == true) {
                Button(onPreviewNotification) {
                    Text(stringResource(R.string.button_preview_notification))
                }
                Spacer(Modifier.height(12.dp))
            }
            Button(onOpenProfile) {
                Text(stringResource(R.string.button_profile_settings))
            }
            Spacer(Modifier.height(12.dp))
        }
        if (feed.isNotEmpty()) {
            item {
                Text(stringResource(R.string.section_feed), style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(8.dp))
            }
            items(feed, key = { it.id }) { item ->
            FeedCard(item, state.downloads.contains(item.id), onClick = { onItemSelected(item) })
                    .animateItemPlacement()
                Spacer(Modifier.height(16.dp))
            }
        }
        items(tokens.screens.toList()) { (key, value) ->
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                Text(value.name ?: key, style = MaterialTheme.typography.titleMedium)
                value.description?.let {
                    Text(it, style = MaterialTheme.typography.bodySmall)
                }
                value.status?.let {
                    Text(stringResource(R.string.feed_card_status, it), style = MaterialTheme.typography.labelSmall)
                }
            }
            Spacer(Modifier.height(16.dp))
        }
    }
}

@Composable
fun FeedCard(item: FeedItem, isDownloaded: Boolean, onClick: () -> Unit) {
    val description = stringResource(R.string.feed_card_accessibility, item.title, item.subtitle)
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp)
            .clip(RoundedCornerShape(16.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .semantics {
                contentDescription = description
                if (isDownloaded) stateDescription = stringResource(R.string.feed_downloaded_badge)
            }
            .clickable(onClick = onClick)
            .padding(16.dp)
    ) {
        if (isDownloaded) {
            Text(stringResource(R.string.feed_downloaded_badge), color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.labelSmall)
        }
        Text(item.title, style = MaterialTheme.typography.titleMedium)
        Text(item.subtitle, style = MaterialTheme.typography.bodySmall)
        item.duration?.let {
            Text(stringResource(R.string.feed_duration, it / 60), style = MaterialTheme.typography.labelSmall)
        }
        Spacer(Modifier.height(8.dp))
        TextButton(onClick = onClick) {
            Text(stringResource(R.string.button_view_details))
        }
    }
}

@Composable
fun PaywallSheet(plans: List<PaywallPlan>, onSelect: (PaywallPlan) -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(stringResource(R.string.paywall_title), style = MaterialTheme.typography.titleLarge)
        Text(
            "Meditations, offline access, and more.",
            style = MaterialTheme.typography.bodyMedium
        )
        plans.forEach { plan ->
            Button(onClick = { onSelect(plan) }, modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.fillMaxWidth()) {
                    Text(plan.title, style = MaterialTheme.typography.titleMedium)
                    Text(plan.priceLocalized, style = MaterialTheme.typography.bodySmall)
                    plan.trial?.let {
                        Text(it, style = MaterialTheme.typography.labelSmall)
                    }
                }
            }
        }
    }
}

@Composable
fun ProfileSheet(
    profile: ProfileResponse?,
    onSave: (String) -> Unit,
    onToggle: (Boolean, Boolean) -> Unit
) {
    var name by remember { mutableStateOf(profile?.user?.name ?: "") }
    var paywallEnabled by remember { mutableStateOf(profile?.featureFlags?.paywallEnabled ?: true) }
    var notificationsEnabled by remember { mutableStateOf(profile?.featureFlags?.notificationsEnabled ?: true) }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(stringResource(R.string.profile_title), style = MaterialTheme.typography.titleLarge)
        TextField(value = name, onValueChange = { name = it }, label = { Text(stringResource(R.string.profile_display_name)) })
        Button(onClick = { onSave(name) }, modifier = Modifier.fillMaxWidth()) {
            Text(stringResource(R.string.button_save_name))
        }
        Spacer(Modifier.height(12.dp))
        Text(stringResource(R.string.profile_feature_flags), style = MaterialTheme.typography.titleMedium)
        SwitchRow(
            label = "Paywall enabled",
            checked = paywallEnabled,
            onCheckedChange = { paywallEnabled = it }
        )
        SwitchRow(
            label = "Notifications enabled",
            checked = notificationsEnabled,
            onCheckedChange = { notificationsEnabled = it }
        )
        Button(onClick = { onToggle(paywallEnabled, notificationsEnabled) }, modifier = Modifier.fillMaxWidth()) {
            Text(stringResource(R.string.button_apply))
        }
    }
}

@Composable
fun SwitchRow(label: String, checked: Boolean, onCheckedChange: (Boolean) -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label)
        Switch(checked = checked, onCheckedChange = onCheckedChange)
    }
}

@Composable
fun FeedSkeletonList() {
    val shimmer = rememberShimmerBrush()
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        items(3) { _ ->
            Spacer(Modifier.height(12.dp))
            Box(
                modifier = Modifier
                    .fillMaxWidth(0.9f)
                    .height(150.dp)
                    .clip(RoundedCornerShape(16.dp))
                    .background(shimmer)
            )
        }
    }
}

@Composable
fun rememberShimmerBrush(): androidx.compose.ui.graphics.Brush {
    val colors = listOf(
        MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f),
        MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.2f),
        MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f)
    )
    val transition = rememberInfiniteTransition(label = "shimmer")
    val translateAnim by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1000f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1200, easing = LinearEasing)
        ),
        label = "translate"
    )
    return androidx.compose.ui.graphics.Brush.linearGradient(
        colors = colors,
        start = androidx.compose.ui.geometry.Offset(translateAnim, 0f),
        end = androidx.compose.ui.geometry.Offset(translateAnim + 200f, 200f)
    )
}

@Composable
fun ErrorView(message: String, onRetry: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(stringResource(R.string.error_title), style = MaterialTheme.typography.titleLarge)
        Spacer(Modifier.height(8.dp))
        Text(message, style = MaterialTheme.typography.bodyMedium, textAlign = androidx.compose.ui.text.style.TextAlign.Center)
        Spacer(Modifier.height(12.dp))
        Button(onClick = onRetry) {
            Text(stringResource(R.string.button_retry))
        }
    }
}

@Composable
fun ContentDetailSheet(
    item: FeedItem,
    content: ContentDetail,
    progress: ContentProgress?,
    isDownloaded: Boolean,
    onDownload: () -> Unit,
    onRemoveDownload: () -> Unit,
    onSeekFinished: (Int) -> Unit,
    onComplete: () -> Unit,
    onClose: () -> Unit
) {
    var position by remember { mutableStateOf((progress?.position ?: 0).toFloat()) }
    var isPlaying by remember { mutableStateOf(false) }
    val duration = content.duration.toFloat().coerceAtLeast(1f)

    LaunchedEffect(progress?.position) {
        position = (progress?.position ?: 0).toFloat()
    }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(content.title, style = MaterialTheme.typography.titleLarge)
        Text(content.description, style = MaterialTheme.typography.bodyMedium)
        Text(stringResource(R.string.feed_instructor, content.instructor), style = MaterialTheme.typography.labelLarge)

        Slider(
            value = position,
            onValueChange = { position = it },
            valueRange = 0f..duration,
            onValueChangeFinished = { onSeekFinished(position.toInt()) },
            modifier = Modifier.semantics {
                contentDescription = stringResource(R.string.player_position_value, position.toInt(), content.duration)
                value = stringResource(R.string.player_position_value, position.toInt(), content.duration)
                progressBarRangeInfo = ProgressBarRangeInfo(position, 0f..duration)
            }
        )
        LinearProgressIndicator(progress = position / duration)

        Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
            Button(onClick = {
                val newPos = max(position - 15f, 0f)
                position = newPos
                onSeekFinished(newPos.toInt())
            }) { Text(stringResource(R.string.player_back_15)) }
            Button(onClick = { isPlaying = !isPlaying }) {
                Text(if (isPlaying) "Pause" else "Play")
            }
            Button(onClick = {
                val newPos = min(position + 15f, duration)
                position = newPos
                onSeekFinished(newPos.toInt())
            }) { Text(stringResource(R.string.player_forward_15)) }
        }

        Button(onClick = {
            position = duration
            onComplete()
        }, modifier = Modifier.fillMaxWidth()) {
            Text(stringResource(R.string.button_mark_complete))
        }

        Button(onClick = { if (isDownloaded) onRemoveDownload() else onDownload() }, modifier = Modifier.fillMaxWidth()) {
            Text(if (isDownloaded) stringResource(R.string.button_remove_download) else stringResource(R.string.button_download))
        }

        TextButton(onClick = onClose, modifier = Modifier.align(Alignment.End)) {
            Text(stringResource(R.string.button_close))
        }
    }
}
