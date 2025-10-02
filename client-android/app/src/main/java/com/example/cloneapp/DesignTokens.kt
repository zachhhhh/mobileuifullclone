package com.example.cloneapp

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

@Serializable
data class DesignTokens(
    @SerialName("run_id") val runId: String? = null,
    val screens: Map<String, ScreenToken> = emptyMap()
)

@Serializable
data class ScreenToken(
    val name: String? = null,
    val description: String? = null,
    val status: String? = null,
    val screenshot: String? = null,
    val hierarchy: String? = null,
    val directory: String? = null,
    val metrics: ScreenMetrics? = null,
    val steps: List<Step>? = null
)

@Serializable
data class ScreenMetrics(
    @SerialName("element_count") val elementCount: Int? = null,
    @SerialName("class_frequency") val classFrequency: Map<String, Int>? = null,
    val accessibility: List<AccessibilityEntry>? = null
)

@Serializable
data class AccessibilityEntry(
    val label: String? = null,
    val identifier: String? = null,
    val value: String? = null
)

@Serializable
data class Step(
    val index: Int? = null,
    val action: String? = null,
    val description: String? = null,
    val status: String? = null
)

object TokenStore {
    private val json = Json { ignoreUnknownKeys = true }

    suspend fun load(context: Context): DesignTokens = withContext(Dispatchers.IO) {
        val input = context.assets.open("tokens.json")
        val bytes = input.use { it.readBytes() }
        json.decodeFromString(DesignTokens.serializer(), bytes.decodeToString())
    }
}
