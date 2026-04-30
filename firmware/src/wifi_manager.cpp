/**
 * wifi_manager.cpp — WiFi 连接管理实现
 */

#include "wifi_manager.h"
#include "config.h"

static bool s_connected = false;
static unsigned long s_last_retry_ms = 0;

void wifi_init() {
    Serial.println("[WiFi] Initializing...");
    WiFi.mode(WIFI_STA);

#if MOCK_MODE
    Serial.println("[WiFi] MOCK MODE: faking connection");
    s_connected = true;
#else
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.printf("[WiFi] Connecting to %s ...\n", WIFI_SSID);

    unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED &&
           millis() - start < WIFI_CONNECT_TIMEOUT_MS) {
        delay(500);
        Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED) {
        s_connected = true;
        Serial.printf("\n[WiFi] Connected! IP: %s, RSSI: %d\n",
                      WiFi.localIP().toString().c_str(), WiFi.RSSI());
    } else {
        s_connected = false;
        Serial.printf("\n[WiFi] Failed (timeout %dms)\n", WIFI_CONNECT_TIMEOUT_MS);
    }
#endif
}

void wifi_loop() {
#if MOCK_MODE
    s_connected = true;
#else
    if (s_connected && WiFi.status() == WL_CONNECTED)
        return;

    s_connected = false;

    if (millis() - s_last_retry_ms >= WIFI_RETRY_INTERVAL_MS) {
        s_last_retry_ms = millis();
        Serial.println("[WiFi] Reconnecting...");
        WiFi.disconnect();
        delay(100);
        WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

        unsigned long start = millis();
        while (WiFi.status() != WL_CONNECTED &&
               millis() - start < WIFI_CONNECT_TIMEOUT_MS) {
            delay(500);
        }

        if (WiFi.status() == WL_CONNECTED) {
            s_connected = true;
            Serial.printf("[WiFi] Reconnected! IP: %s\n",
                          WiFi.localIP().toString().c_str());
        }
    }
#endif
}

bool wifi_is_connected() {
    return s_connected;
}

int wifi_get_rssi() {
#if MOCK_MODE
    return -45;
#else
    return WiFi.RSSI();
#endif
}

const char* wifi_get_ip() {
    static char ip[16];
#if MOCK_MODE
    snprintf(ip, sizeof(ip), "192.168.1.100");
#else
    snprintf(ip, sizeof(ip), "%s", WiFi.localIP().toString().c_str());
#endif
    return ip;
}
