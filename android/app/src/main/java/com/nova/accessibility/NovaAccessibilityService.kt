package com.nova.accessibility

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.view.accessibility.AccessibilityEvent
import com.nova.transport.NovaWebSocketClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject

/**
 * Streams on-screen context to the Nova brain over the existing WebSocket.
 *
 * Registered with isAccessibilityTool="true" in the Play Console policy
 * declaration.  The disclosure dialog (POLICY_DISCLOSURE_TEXT from the
 * Python protocol layer) must be shown before the user enables this
 * service — see SettingsActivity.showAccessibilityDisclosure().
 */
class NovaAccessibilityService : AccessibilityService() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onServiceConnected() {
        serviceInfo = serviceInfo.apply {
            eventTypes = AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED or
                    AccessibilityEvent.TYPE_VIEW_FOCUSED or
                    AccessibilityEvent.TYPE_ANNOUNCEMENT
            feedbackType = AccessibilityServiceInfo.FEEDBACK_SPOKEN
            flags = AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS or
                    AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS
            notificationTimeout = 100L
        }
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent) {
        val texts = JSONArray()
        event.text.forEach { texts.put(it.toString()) }

        val frame = JSONObject().apply {
            put("type", "accessibility_event")
            put("event_type", AccessibilityEvent.eventTypeToString(event.eventType))
            put("package_name", event.packageName?.toString() ?: "")
            put("class_name", event.className?.toString() ?: "")
            put("text", texts)
            put("content_description", event.contentDescription?.toString() ?: "")
            put("window_title", rootInActiveWindow?.findAccessibilityNodeInfosByText("")
                ?.firstOrNull()?.window?.title?.toString() ?: "")
        }

        scope.launch {
            NovaWebSocketClient.instance?.sendText(frame.toString())
        }
    }

    override fun onInterrupt() = Unit
}
