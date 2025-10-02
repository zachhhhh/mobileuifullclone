package com.example.cloneapp

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.BufferedReader
import java.io.InputStreamReader
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

    companion object {
        fun default(context: Context): BackendClient {
            val url = context.getString(R.string.backend_url)
            return BackendClient(url)
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
