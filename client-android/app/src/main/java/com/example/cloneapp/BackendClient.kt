package com.example.cloneapp

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.io.BufferedReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

class BackendClient(private val baseUrl: String = BuildConfig.BACKEND_URL) {
    suspend fun health(): String = withContext(Dispatchers.IO) {
        val url = URL("$baseUrl/health")
        val connection = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 5000
            readTimeout = 5000
        }
        return@withContext connection.use { conn ->
            val status = conn.responseCode
            val stream = if (status in 200..299) conn.inputStream else conn.errorStream
            val body = stream?.bufferedReader()?.use(BufferedReader::readText) ?: ""
            if (status == HttpURLConnection.HTTP_OK) {
                Regex("\"status\"\s*:\s*\"(.*?)\"").find(body)?.groupValues?.getOrNull(1) ?: "unknown"
            } else {
                "error"
            }
        }
    }

    suspend fun session(): SessionResponse = withContext(Dispatchers.IO) {
        val url = URL("$baseUrl/session")
        val connection = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 5000
            readTimeout = 5000
        }
        connection.use { conn ->
            val status = conn.responseCode
            val body = if (status in 200..299) {
                conn.inputStream.bufferedReader().use(BufferedReader::readText)
            } else {
                throw IllegalStateException("Session request failed with $status")
            }
            Json { ignoreUnknownKeys = true }.decodeFromString(SessionResponse.serializer(), body)
        }
    }

    companion object {
        fun default(context: Context): BackendClient {
            val url = context.getString(R.string.backend_url)
            return BackendClient(url)
        }
    }

    suspend fun login(email: String, password: String) = withContext(Dispatchers.IO) {
        val url = URL("$baseUrl/auth/login")
        val connection = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 5000
            readTimeout = 5000
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
        }
        connection.use { conn ->
            OutputStreamWriter(conn.outputStream).use { writer ->
                writer.write(Json.encodeToString(mapOf("email" to email, "password" to password)))
            }
            val status = conn.responseCode
            if (status !in 200..299) throw IllegalStateException("Login failed with $status")
        }
    }

    suspend fun logout() = withContext(Dispatchers.IO) {
        val url = URL("$baseUrl/auth/logout")
        val conn = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 5000
            readTimeout = 5000
        }
        conn.use { connection ->
            val status = connection.responseCode
            if (status !in 200..299) throw IllegalStateException("Logout failed with $status")
        }
    }

    suspend fun advanceOnboarding(completed: Boolean, step: String? = null) = withContext(Dispatchers.IO) {
        val url = URL("$baseUrl/onboarding/advance")
        val conn = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 5000
            readTimeout = 5000
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
        }
        conn.use { connection ->
            val payload = mutableMapOf("completed" to completed)
            if (step != null) payload["step"] = step
            OutputStreamWriter(connection.outputStream).use { writer ->
                writer.write(Json.encodeToString(payload))
            }
            val status = connection.responseCode
            if (status !in 200..299) throw IllegalStateException("Advance onboarding failed with $status")
            val body = connection.inputStream.bufferedReader().use(BufferedReader::readText)
            Json.decodeFromString(OnboardingResponse.serializer(), body)
        }
    }

    suspend fun fetchFeed(): List<FeedItem> = withContext(Dispatchers.IO) {
        val url = URL("$baseUrl/feed")
        val conn = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 5000
            readTimeout = 5000
        }
        conn.use { connection ->
            val status = connection.responseCode
            if (status !in 200..299) throw IllegalStateException("Feed fetch failed with $status")
            val body = connection.inputStream.bufferedReader().use(BufferedReader::readText)
            Json.decodeFromString(FeedResponse.serializer(), body).items
        }
    }

    suspend fun contentDetail(contentId: String): ContentResponse = withContext(Dispatchers.IO) {
        val url = URL("$baseUrl/content/$contentId")
        val conn = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 5000
            readTimeout = 5000
        }
        conn.use { connection ->
            val status = connection.responseCode
            if (status !in 200..299) throw IllegalStateException("Content fetch failed with $status")
            val body = connection.inputStream.bufferedReader().use(BufferedReader::readText)
            Json.decodeFromString(ContentResponse.serializer(), body)
        }
    }

    suspend fun fetchPaywall(): PaywallResponse = withContext(Dispatchers.IO) {
        val url = URL("$baseUrl/paywall")
        val conn = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 5000
            readTimeout = 5000
        }
        conn.use { connection ->
            val status = connection.responseCode
            if (status !in 200..299) throw IllegalStateException("Paywall fetch failed with $status")
            val body = connection.inputStream.bufferedReader().use(BufferedReader::readText)
            Json.decodeFromString(PaywallResponse.serializer(), body)
        }
    }

    suspend fun purchase(planId: String) = withContext(Dispatchers.IO) {
        val url = URL("$baseUrl/paywall/purchase")
        val conn = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 5000
            readTimeout = 5000
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
        }
        conn.use { connection ->
            OutputStreamWriter(connection.outputStream).use { writer ->
                writer.write(Json.encodeToString(mapOf("planId" to planId)))
            }
            val status = connection.responseCode
            if (status !in 200..299) throw IllegalStateException("Purchase failed with $status")
        }
    }

    suspend fun notificationPreview(): NotificationPreview = withContext(Dispatchers.IO) {
        val url = URL("$baseUrl/notifications/preview")
        val conn = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 5000
            readTimeout = 5000
        }
        conn.use { connection ->
            val status = connection.responseCode
            if (status !in 200..299) throw IllegalStateException("Notification preview failed with $status")
            val body = connection.inputStream.bufferedReader().use(BufferedReader::readText)
            Json.decodeFromString(NotificationPreviewResponse.serializer(), body).notification
        }
    }

    suspend fun fetchProfile(): ProfileResponse = withContext(Dispatchers.IO) {
        val url = URL("$baseUrl/profile")
        val conn = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 5000
            readTimeout = 5000
        }
        conn.use { connection ->
            val status = connection.responseCode
            if (status !in 200..299) throw IllegalStateException("Profile fetch failed with $status")
            val body = connection.inputStream.bufferedReader().use(BufferedReader::readText)
            Json.decodeFromString(ProfileResponse.serializer(), body)
        }
    }

    suspend fun updateProfileName(name: String): ProfileResponse = withContext(Dispatchers.IO) {
        val url = URL("$baseUrl/profile")
        val conn = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 5000
            readTimeout = 5000
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
        }
        conn.use { connection ->
            OutputStreamWriter(connection.outputStream).use { writer ->
                writer.write(Json.encodeToString(mapOf("name" to name)))
            }
            val status = connection.responseCode
            if (status !in 200..299) throw IllegalStateException("Profile update failed with $status")
            val body = connection.inputStream.bufferedReader().use(BufferedReader::readText)
            Json.decodeFromString(ProfileResponse.serializer(), body)
        }
    }

    suspend fun updateFeatureFlags(paywallEnabled: Boolean? = null, notificationsEnabled: Boolean? = null): FeatureFlags = withContext(Dispatchers.IO) {
        val url = URL("$baseUrl/feature-flags")
        val conn = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 5000
            readTimeout = 5000
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
        }
        conn.use { connection ->
            val payload = buildMap {
                paywallEnabled?.let { put("paywallEnabled", it) }
                notificationsEnabled?.let { put("notificationsEnabled", it) }
            }
            OutputStreamWriter(connection.outputStream).use { writer ->
                writer.write(Json.encodeToString(payload))
            }
            val status = connection.responseCode
            if (status !in 200..299) throw IllegalStateException("Feature flag update failed with $status")
            val body = connection.inputStream.bufferedReader().use(BufferedReader::readText)
            Json.decodeFromString(FeatureFlagResponse.serializer(), body).featureFlags
        }
    }

    suspend fun updateProgress(contentId: String, position: Int, completed: Boolean): ContentProgress = withContext(Dispatchers.IO) {
        val url = URL("$baseUrl/content/$contentId/progress")
        val conn = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 5000
            readTimeout = 5000
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
        }
        conn.use { connection ->
            OutputStreamWriter(connection.outputStream).use { writer ->
                writer.write(Json.encodeToString(mapOf("position" to position, "completed" to completed)))
            }
            val status = connection.responseCode
            if (status !in 200..299) throw IllegalStateException("Progress update failed with $status")
            val body = connection.inputStream.bufferedReader().use(BufferedReader::readText)
            Json.decodeFromString(ProgressResponse.serializer(), body).progress
        }
    }

    suspend fun logEvent(name: String, properties: Map<String, String> = emptyMap()) = withContext(Dispatchers.IO) {
        val url = URL("$baseUrl/analytics/events")
        val conn = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 5000
            readTimeout = 5000
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
        }
        conn.use { connection ->
            OutputStreamWriter(connection.outputStream).use { writer ->
                writer.write(Json.encodeToString(mapOf("name" to name, "properties" to properties)))
            }
            connection.responseCode // ignore response
        }
    }
}

private inline fun <T> HttpURLConnection.use(block: (HttpURLConnection) -> T): T {
    return try {
        block(this)
    } finally {
        disconnect()
    }
}


    suspend fun requestDownload(contentId: String): DownloadResponse = withContext(Dispatchers.IO) {
        val url = URL("$baseUrl/content/$contentId/download")
        val conn = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 5000
            readTimeout = 5000
        }
        conn.use { connection ->
            val status = connection.responseCode
            if (status !in 200..299) throw IllegalStateException("Download request failed with $status")
            val body = connection.inputStream.bufferedReader().use(BufferedReader::readText)
            Json.decodeFromString(DownloadResponse.serializer(), body)
        }
    }

    suspend fun deleteDownload(contentId: String) = withContext(Dispatchers.IO) {
        val url = URL("$baseUrl/content/$contentId/download")
        val conn = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "DELETE"
            connectTimeout = 5000
            readTimeout = 5000
        }
        conn.use { connection ->
            connection.responseCode
        }
    }
