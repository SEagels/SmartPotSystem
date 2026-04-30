/**
 * upload_service.cpp — MQTT + HTTPS 上传服务
 *
 * 负责:
 * 1. MQTT 遥测上报 (smartpot/{id}/telemetry, QoS 1)
 * 2. HTTP 图片上传 (POST /v1/devices/{id}/images, multipart)
 * 3. MQTT 指令接收 (command/water, command/photo, command/config)
 * 4. MQTT 事件发布 (event/watering)
 * 5. LWT 在线状态 (status, retain)
 */

#include "upload_service.h"
#include "config.h"
#include "board_pins.h"
#include "wifi_manager.h"
#include "sensor_service.h"
#include "pump_service.h"
#include "camera_service.h"
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <HTTPClient.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ----- MQTT 状态 -----------------------------------------------
static WiFiClient s_mqtt_wifi;
static PubSubClient      s_mqtt(s_mqtt_wifi);
static unsigned long     s_last_mqtt_retry = 0;
static bool              s_mqtt_ok = false;
static uint32_t          s_telemetry_seq = 0;

// ----- 指令处理回调 --------------------------------------------
static void mqtt_callback(char* topic, byte* payload, unsigned int length) {
    char buf[1024];
    unsigned int n = length < sizeof(buf)-1 ? length : sizeof(buf)-1;
    memcpy(buf, payload, n);
    buf[n] = '\0';

    Serial.printf("[MQTT] << %s: %s\n", topic, buf);

    JsonDocument doc;
    if (deserializeJson(doc, buf)) return;

    const char* cmd_id = doc["cmd_id"] | "";

    if (strstr(topic, "/command/water")) {
        uint32_t dur = doc["duration_ms"] | (uint32_t)AUTO_WATER_DURATION_MS;
        const char* src = doc["source"] | "manual";

        if (!pump_can_run()) {
            upload_cmd_response(cmd_id, "rejected", "{\"reason\":\"cooldown\"}");
            return;
        }
        float sb = soil_moisture_read();
        uint32_t actual = pump_run(dur);
        float sa = soil_moisture_read();
        float ml = pump_estimate_volume(actual);
        upload_watering_event(src, actual, ml, sb, sa);

        JsonDocument r;
        r["actual_duration_ms"] = actual;
        r["water_pumped_ml"] = ml;
        String d;
        serializeJson(r, d);
        upload_cmd_response(cmd_id, "executed", d.c_str());
    }
    else if (strstr(topic, "/command/photo")) {
        int burst = constrain((int)(doc["burst_count"] | 1), 1, 5);
        CameraFrame frame;
        if (!camera_capture_best(burst, frame)) {
            upload_cmd_response(cmd_id, "failed", "{\"error\":\"capture\"}");
            return;
        }
        bool ok = upload_image(frame, 1, burst);
        camera_frame_free(frame);

        JsonDocument r;
        r["image_count"] = burst;
        r["selected_index"] = 1;
        r["uploaded"] = ok;
        String d;
        serializeJson(r, d);
        upload_cmd_response(cmd_id, ok ? "executed" : "failed", d.c_str());
    }
    else if (strstr(topic, "/command/config")) {
        JsonDocument changes = doc["changes"];
        Serial.println("[Config] Updated:");
        serializeJsonPretty(changes, Serial);
        upload_cmd_response(cmd_id, "applied", "{}");
    }
    else if (strstr(topic, "/command/sync")) {
        Serial.println("[Sync] Immediate sensor read + telemetry upload");
        sensors_read();
        upload_telemetry(sensors_get_latest(), millis() / 1000);
        upload_cmd_response(cmd_id, "executed", "{\"synced\":true}");
    }
}

// ----- 初始化 --------------------------------------------------
void upload_init() {
#if MOCK_MODE
    Serial.println("[Upload] MOCK MODE: MQTT+HTTP simulated");
    s_mqtt_ok = true;
#else
    s_mqtt.setServer(MQTT_BROKER_HOST, MQTT_BROKER_PORT);
    s_mqtt.setCallback(mqtt_callback);
    s_mqtt.setKeepAlive(MQTT_KEEPALIVE_S);
    Serial.printf("[Upload] MQTT broker: %s:%d\n", MQTT_BROKER_HOST, MQTT_BROKER_PORT);
#endif
}

void upload_loop() {
#if MOCK_MODE
    s_mqtt_ok = true;
#else
    if (!wifi_is_connected()) { s_mqtt_ok = false; return; }

    if (!s_mqtt.connected()) {
        s_mqtt_ok = false;
        if (millis() - s_last_mqtt_retry >= MQTT_RECONNECT_INTERVAL_MS) {
            s_last_mqtt_retry = millis();
            Serial.print("[MQTT] Connecting...");

            String lwt_topic = MQTT_TOPIC_STATUS;
            String lwt_payload = "{\"online\":false}";

            if (s_mqtt.connect(MQTT_CLIENT_ID, MQTT_USERNAME, MQTT_PASSWORD,
                               lwt_topic.c_str(), 0, true, lwt_payload.c_str())) {
                s_mqtt_ok = true;
                Serial.println(" OK");
                s_mqtt.subscribe(MQTT_TOPIC_COMMAND_WATER, 0);
                s_mqtt.subscribe(MQTT_TOPIC_COMMAND_PHOTO, 0);
                s_mqtt.subscribe(MQTT_TOPIC_COMMAND_CONFIG, 0);
                s_mqtt.subscribe(MQTT_TOPIC_COMMAND_SYNC, 0);
                upload_device_online();
            } else {
                Serial.printf(" FAIL (rc=%d)\n", s_mqtt.state());
            }
        }
    } else {
        s_mqtt.loop();
    }
#endif
}

// ----- 遥测上报 -------------------------------------------------
void upload_telemetry(const SensorData& data, uint32_t uptime_s) {
    s_telemetry_seq++;

    JsonDocument doc;
    doc["device_id"] = DEVICE_ID;

    char ts[32];
    time_t now = time(nullptr);
    struct tm* t = gmtime(&now);
    snprintf(ts, sizeof(ts), "%04d-%02d-%02dT%02d:%02d:%02dZ",
             t->tm_year+1900, t->tm_mon+1, t->tm_mday,
             t->tm_hour, t->tm_min, t->tm_sec);
    doc["timestamp"] = ts;
    doc["sequence"]  = s_telemetry_seq;

    JsonObject s = doc["sensors"].to<JsonObject>();
    s["temperature"] = data.temperature;
    s["humidity"] = data.humidity;
    s["soil_moisture"] = data.soil_moisture;
    s["light_intensity"] = data.light_intensity;

    JsonObject a = doc["actuators"].to<JsonObject>();
    a["pump_running"] = pump_is_running();
    a["led_on"] = false;

    JsonObject y = doc["system"].to<JsonObject>();
    y["wifi_rssi"] = wifi_get_rssi();
    y["free_heap_kb"] = ESP.getFreeHeap() / 1024;
    y["uptime_s"] = uptime_s;
    y["firmware_version"] = FIRMWARE_VERSION;

    String payload;
    serializeJson(doc, payload);

#if MOCK_MODE
    Serial.printf("[Upload] MOCK telemetry seq=%d\n", s_telemetry_seq);
#else
    if (s_mqtt_ok) {
        bool ok = s_mqtt.publish(MQTT_TOPIC_TELEMETRY, payload.c_str());
        Serial.printf("[MQTT] >> telemetry seq=%d %s\n", s_telemetry_seq, ok ? "OK" : "FAIL");
    }
#endif
}

// ----- 图片上传 -------------------------------------------------
bool upload_image(const CameraFrame& frame, int photo_index, int burst_total) {
#if MOCK_MODE
    Serial.printf("[Upload] MOCK image %d bytes (idx=%d/%d)\n",
                  frame.len, photo_index, burst_total);
    return true;
#else
    if (!wifi_is_connected()) return false;

    char image_id[64];
    time_t now = time(nullptr);
    struct tm* t = gmtime(&now);
    snprintf(image_id, sizeof(image_id), "IMG-%04d%02d%02d-%02d%02d%02d-" DEVICE_ID,
             t->tm_year+1900, t->tm_mon+1, t->tm_mday, t->tm_hour, t->tm_min, t->tm_sec);

    JsonDocument meta;
    meta["image_id"] = image_id;
    meta["device_id"] = DEVICE_ID;
    meta["photo_index"] = photo_index;
    meta["burst_total"] = burst_total;
    meta["quality_score"] = frame.quality;
    meta["light_condition"] = "natural";
    meta["resolution"] = String(frame.width) + "x" + String(frame.height);
    meta["file_size_bytes"] = frame.len;
    meta["format"] = "jpg";
    String meta_str;
    serializeJson(meta, meta_str);

    WiFiClient client;
    client.setTimeout(15);

    String boundary = "----SmartPot" + String(random(100000, 999999));
    String ct = "multipart/form-data; boundary=" + boundary;

    String body1 = "--" + boundary + "\r\n"
      "Content-Disposition: form-data; name=\"image\"; filename=\"photo.jpg\"\r\n"
      "Content-Type: image/jpeg\r\n\r\n";

    String body2 = "\r\n--" + boundary + "\r\n"
      "Content-Disposition: form-data; name=\"metadata\"\r\n\r\n"
      + meta_str + "\r\n";

    String body3 = "--" + boundary + "--\r\n";

    size_t total = body1.length() + frame.len + body2.length() + body3.length();

    if (!client.connect(CLOUD_API_HOST, CLOUD_API_PORT)) {
        Serial.println("[Upload] TCP connect failed");
        return false;
    }

    client.printf("POST /v1/devices/" DEVICE_ID "/images HTTP/1.1\r\n");
    client.printf("Host: %s\r\n", CLOUD_API_HOST);
    client.printf("Authorization: Bearer %s\r\n", CLOUD_API_TOKEN);
    client.printf("Content-Type: %s\r\n", ct.c_str());
    client.printf("Content-Length: %d\r\n", total);
    client.println("Connection: close\r\n");

    client.print(body1);
    client.write(frame.buf, frame.len);
    client.print(body2);
    client.print(body3);

    unsigned long to = millis() + 15000;
    while (client.connected() && millis() < to) {
        if (client.available()) {
            String line = client.readStringUntil('\n');
            Serial.printf("[Upload] %s", line.c_str());
        }
    }
    client.stop();
    Serial.printf("[Upload] %s sent (%d bytes)\n", image_id, frame.len);

    if (s_mqtt_ok) {
        JsonDocument ntf;
        ntf["image_id"] = image_id;
        ntf["photo_index"] = photo_index;
        String p;
        serializeJson(ntf, p);
        s_mqtt.publish(MQTT_TOPIC_IMAGE_UPLOADED, p.c_str());
    }
    return true;
#endif
}

// ----- 事件发布 -------------------------------------------------
void upload_watering_event(const char* trigger, uint32_t duration_ms,
                           float water_ml, float soil_before, float soil_after) {
    JsonDocument doc;
    char eid[64];
    time_t now = time(nullptr);
    struct tm* t = gmtime(&now);
    snprintf(eid, sizeof(eid), "EVT-WATER-%04d%02d%02d-%02d%02d%02d-" DEVICE_ID,
             t->tm_year+1900, t->tm_mon+1, t->tm_mday, t->tm_hour, t->tm_min, t->tm_sec);
    doc["event_id"] = eid;
    doc["trigger"] = trigger;
    doc["duration_ms"] = duration_ms;
    doc["water_pumped_ml"] = water_ml;
    doc["reason"] = "soil_moisture_below_threshold";
    doc["soil_moisture_before"] = soil_before;
    doc["soil_moisture_after"] = soil_after;

    String payload;
    serializeJson(doc, payload);

#if MOCK_MODE
    Serial.printf("[Upload] MOCK watering: %s\n", payload.c_str());
#else
    if (s_mqtt_ok) {
        s_mqtt.publish(MQTT_TOPIC_EVENT_WATERING, payload.c_str());
        Serial.println("[MQTT] >> watering event");
    }
#endif
}

void upload_cmd_response(const char* cmd_id, const char* status, const char* detail) {
    JsonDocument doc;
    doc["cmd_id"] = cmd_id;
    doc["status"] = status;
    String payload;
    serializeJson(doc, payload);

    if (detail && strlen(detail) > 2) {
        payload.remove(payload.length() - 1);
        payload += ",\"response\":" + String(detail) + "}";
    }

#if MOCK_MODE
    Serial.printf("[Upload] MOCK cmd resp: %s\n", payload.c_str());
#else
    if (s_mqtt_ok) {
        String topic = MQTT_TOPIC_RESPONSE_WATER;
        if (strstr(cmd_id, "PHOTO"))  topic = MQTT_TOPIC_RESPONSE_PHOTO;
        if (strstr(cmd_id, "CONFIG")) topic = MQTT_TOPIC_RESPONSE_CONFIG;
        if (strstr(cmd_id, "SYNC"))   topic = MQTT_TOPIC_RESPONSE_SYNC;
        s_mqtt.publish(topic.c_str(), payload.c_str());
    }
#endif
}

void upload_device_online() {
    JsonDocument doc;
    doc["online"] = true;
    char ts[32];
    time_t now = time(nullptr);
    struct tm* t = gmtime(&now);
    snprintf(ts, sizeof(ts), "%04d-%02d-%02dT%02d:%02d:%02dZ",
             t->tm_year+1900, t->tm_mon+1, t->tm_mday, t->tm_hour, t->tm_min, t->tm_sec);
    doc["timestamp"] = ts;
    doc["firmware_version"] = FIRMWARE_VERSION;
    doc["wifi_rssi"] = wifi_get_rssi();
    doc["free_heap"] = ESP.getFreeHeap();

    String payload;
    serializeJson(doc, payload);

#if MOCK_MODE
    Serial.printf("[Upload] MOCK online: %s\n", payload.c_str());
#else
    if (s_mqtt_ok) {
        s_mqtt.publish(MQTT_TOPIC_STATUS, payload.c_str(), true);
        Serial.println("[MQTT] >> device online (retain)");
    }
#endif
}

bool upload_mqtt_connected() {
    return s_mqtt_ok;
}
