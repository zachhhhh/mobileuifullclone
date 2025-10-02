package com.example.cloneapp

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    TokenScreen(
                        loadTokens = { TokenStore.load(applicationContext) },
                        loadBackendStatus = { BackendClient.default(applicationContext).health() }
                    )
                }
            }
        }
    }
}

@Composable
fun TokenScreen(
    loadTokens: suspend () -> DesignTokens,
    loadBackendStatus: suspend () -> String
) {
    var tokens by remember { mutableStateOf(DesignTokens()) }
    var error by remember { mutableStateOf<String?>(null) }
    var backendStatus by remember { mutableStateOf("loading") }

    LaunchedEffect(Unit) {
        try {
            tokens = loadTokens()
            backendStatus = loadBackendStatus()
        } catch (t: Throwable) {
            error = t.message
        }
    }

    if (error != null) {
        Column(
            Modifier.fillMaxSize(),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Text("Error: $error")
        }
    } else {
        LazyColumn {
            item {
                Text("Backend", style = MaterialTheme.typography.titleMedium)
                Text("Status: $backendStatus", style = MaterialTheme.typography.bodySmall)
                Spacer(modifier = Modifier.height(16.dp))
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
                        Text("Status: $it", style = MaterialTheme.typography.labelSmall)
                    }
                }
            }
        }
    }
}
