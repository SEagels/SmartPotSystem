/**
 * http_server.cpp — 本地 HTTP 控制接口 (端口 80)
 *
 * GET  /              HTML 状态页
 * GET  /api/status    设备状态 JSON
 * GET  /api/sensors   传感器数据 JSON
 * POST /api/pump      触发补水 { "duration_ms": 5000 }
 * POST /api/photo     触发拍照 { "burst_count": 1 }
 */

#include "http_server.h"
#include "config.h"
#include "board_pins.h"
#include "wifi_manager.h"
#include "sensor_service.h"
#include "pump_service.h"
#include "camera_service.h"
#include "upload_service.h"
#include <Arduino.h>
#include <WiFi.h>
#include <ArduinoJson.h>

static WiFiServer s_server(LOCAL_HTTP_PORT);
static bool s_initialized = false;

static void handle_request(WiFiClient& client);
static void send_json(WiFiClient& client, int code, const char* message,
                      const char* json_body);
static void handle_status(WiFiClient& client);
static void handle_sensors(WiFiClient& client);
static void handle_pump(WiFiClient& client, const String& body);
static void handle_photo(WiFiClient& client, const String& body);
static String read_body(WiFiClient& client, int len);

// ================================================================

void http_server_init() {
    s_server.begin();
    s_initialized = true;
    Serial.printf("[HTTP] Server on port %d\n", LOCAL_HTTP_PORT);
}

void http_server_loop() {
    if (!s_initialized) return;
    WiFiClient client = s_server.accept();
    if (!client) return;
    handle_request(client);
    client.stop();
}

// ================================================================

static void handle_request(WiFiClient& client) {
    String line = client.readStringUntil('\r');
    client.read(); // \n
    if (line.length() == 0) return;

    int sp1 = line.indexOf(' ');
    int sp2 = line.indexOf(' ', sp1 + 1);
    if (sp1 < 0 || sp2 < 0) return;

    String method = line.substring(0, sp1);
    String path   = line.substring(sp1 + 1, sp2);

    int content_length = 0;
    while (client.available()) {
        String h = client.readStringUntil('\r');
        client.read();
        if (h.length() <= 1) break;
        if (h.startsWith("Content-Length:"))
            content_length = h.substring(15).toInt();
    }

    String body;
    if (content_length > 0) body = read_body(client, content_length);

    Serial.printf("[HTTP] %s %s\n", method.c_str(), path.c_str());

    if (method == "GET" && path == "/") {
        String html = "<!DOCTYPE html><html><head><meta charset='utf-8'>"
          "<title>SmartPot - " DEVICE_ID "</title></head><body>"
          "<h1>SmartPot " DEVICE_ID "</h1>"
          "<p>WiFi: " + String(wifi_is_connected() ? "ON" : "OFF") +
          " | IP: " + String(wifi_get_ip()) + " | FW: " FIRMWARE_VERSION "</p>"
          "<p><a href='/api/status'>Status</a> | "
          "<a href='/api/sensors'>Sensors</a></p>"
          "</body></html>";
        client.println("HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\n");
        client.println(html);
    }
    else if (method == "GET" && path == "/api/status")  handle_status(client);
    else if (method == "GET" && path == "/api/sensors") handle_sensors(client);
    else if (method == "POST" && path == "/api/pump")   handle_pump(client, body);
    else if (method == "POST" && path == "/api/photo")  handle_photo(client, body);
    else send_json(client, 404, "not_found", "{}");
}

// ================================================================

static void handle_status(WiFiClient& client) {
    SensorData s = sensors_get_latest();
    JsonDocument doc;
    doc["device_id"]   = DEVICE_ID;
    doc["fw_version"]  = FIRMWARE_VERSION;
    doc["wifi_ok"]     = wifi_is_connected();
    doc["wifi_rssi"]   = wifi_get_rssi();
    doc["ip"]          = wifi_get_ip();
    doc["uptime_s"]    = millis() / 1000;
    doc["free_heap"]   = ESP.getFreeHeap();
    doc["pump_running"] = pump_is_running();
    doc["mock_mode"]   = (bool)MOCK_MODE;

    JsonObject sn = doc["sensors"].to<JsonObject>();
    sn["temperature"] = s.temperature;
    sn["humidity"]    = s.humidity;
    sn["soil_moisture"]   = s.soil_moisture;
    sn["light_intensity"] = s.light_intensity;

    String json;
    serializeJson(doc, json);
    send_json(client, 200, "success", json.c_str());
}

static void handle_sensors(WiFiClient& client) {
    SensorData s = sensors_read();
    JsonDocument doc;
    doc["device_id"]       = DEVICE_ID;
    doc["temperature"]     = s.temperature;
    doc["humidity"]        = s.humidity;
    doc["soil_moisture"]   = s.soil_moisture;
    doc["light_intensity"] = s.light_intensity;
    doc["valid"]           = s.valid;

    String json;
    serializeJson(doc, json);
    send_json(client, 200, "success", json.c_str());
}

static void handle_pump(WiFiClient& client, const String& body) {
    uint32_t duration_ms = AUTO_WATER_DURATION_MS;
    if (body.length() > 0) {
        JsonDocument doc;
        if (!deserializeJson(doc, body) && doc["duration_ms"].is<int>())
            duration_ms = doc["duration_ms"];
    }
    if (!pump_can_run()) {
        send_json(client, 200, "rejected", "{\"reason\":\"cooldown\"}");
        return;
    }

    float sb = soil_moisture_read();
    uint32_t actual = pump_run(duration_ms);
    float sa = soil_moisture_read();
    float ml = pump_estimate_volume(actual);
    upload_watering_event("manual", actual, ml, sb, sa);

    JsonDocument doc;
    doc["duration_ms"] = actual;
    doc["water_ml"]    = ml;
    doc["soil_before"] = sb;
    doc["soil_after"]  = sa;
    String json;
    serializeJson(doc, json);
    send_json(client, 200, "success", json.c_str());
}

static void handle_photo(WiFiClient& client, const String& body) {
    int burst = 1;
    if (body.length() > 0) {
        JsonDocument doc;
        if (!deserializeJson(doc, body) && doc["burst_count"].is<int>())
            burst = constrain((int)doc["burst_count"], 1, 5);
    }

    CameraFrame frame;
    if (!camera_capture_best(burst, frame)) {
        send_json(client, 500, "failed", "{\"error\":\"capture\"}");
        return;
    }

    bool ok = upload_image(frame, 1, burst);
    camera_frame_free(frame);

    JsonDocument doc;
    doc["burst_count"] = burst;
    doc["uploaded"]    = ok;
    String json;
    serializeJson(doc, json);
    send_json(client, 200, "success", json.c_str());
}

// ================================================================

static void send_json(WiFiClient& client, int http_code,
                      const char* message, const char* json_body) {
    client.printf("HTTP/1.1 %d OK\r\n", http_code);
    client.println("Content-Type: application/json; charset=utf-8");
    client.println("Connection: close");
    client.println();
    client.printf("{\"code\":%d,\"message\":\"%s\",\"data\":%s}",
                  http_code == 200 ? 0 : http_code, message, json_body);
}

static String read_body(WiFiClient& client, int len) {
    String body;
    body.reserve(len);
    while (body.length() < (unsigned)len && client.available())
        body += (char)client.read();
    return body;
}
