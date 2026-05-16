package com.smartpot.app.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ApiEnvelope<T>(
    val code: Int,
    val message: String,
    val data: T? = null,
)

@Serializable
data class LoginRequest(
    val username: String,
    val password: String,
)

@Serializable
data class LoginData(
    @SerialName("user_id") val userId: String,
    val username: String,
    val token: String,
    @SerialName("expires_at") val expiresAt: String? = null,
)

@Serializable
data class DeviceListItem(
    @SerialName("device_id") val deviceId: String,
    val name: String,
    @SerialName("plant_type") val plantType: String? = null,
    @SerialName("plant_type_name") val plantTypeName: String? = null,
    val online: Boolean = false,
    @SerialName("latest_telemetry") val latestTelemetry: TelemetrySnippet? = null,
    @SerialName("has_active_alert") val hasActiveAlert: Boolean = false,
    @SerialName("bound_at") val boundAt: String? = null,
)

@Serializable
data class DeviceDetail(
    @SerialName("device_id") val deviceId: String,
    val name: String,
    @SerialName("plant_type") val plantType: String? = null,
    @SerialName("plant_type_name") val plantTypeName: String? = null,
    val online: Boolean = false,
    @SerialName("firmware_version") val firmwareVersion: String? = null,
    @SerialName("latest_telemetry") val latestTelemetry: TelemetrySnippet? = null,
)

@Serializable
data class TelemetrySnippet(
    val temperature: Double? = null,
    val humidity: Double? = null,
    @SerialName("soil_moisture") val soilMoisture: Double? = null,
    val timestamp: String? = null,
)

@Serializable
data class LatestTelemetry(
    @SerialName("device_id") val deviceId: String,
    val timestamp: String,
    val sensors: SensorValues,
    val actuators: ActuatorValues,
    val system: SystemValues,
)

@Serializable
data class SensorValues(
    val temperature: Double? = null,
    val humidity: Double? = null,
    @SerialName("soil_moisture") val soilMoisture: Double? = null,
    @SerialName("light_intensity") val lightIntensity: Double? = null,
)

@Serializable
data class ActuatorValues(
    @SerialName("pump_running") val pumpRunning: Boolean = false,
    @SerialName("led_on") val ledOn: Boolean = false,
)

@Serializable
data class SystemValues(
    @SerialName("wifi_rssi") val wifiRssi: Int? = null,
    @SerialName("uptime_s") val uptimeSeconds: Int? = null,
)

@Serializable
data class LanDeviceCandidate(
    @SerialName("device_id") val deviceId: String,
    val ip: String,
    @SerialName("firmware_version") val firmwareVersion: String? = null,
    @SerialName("wifi_rssi") val wifiRssi: Int? = null,
    @SerialName("uptime_s") val uptimeSeconds: Int? = null,
    @SerialName("mock_mode") val mockMode: Boolean? = null,
)

@Serializable
data class LanBindRequest(
    @SerialName("device_id") val deviceId: String,
    val ip: String,
    val name: String? = null,
)

@Serializable
data class WaterRequest(
    @SerialName("duration_ms") val durationMs: Int,
)

@Serializable
data class PhotoRequest(
    @SerialName("burst_count") val burstCount: Int,
)

@Serializable
data class CommandResult(
    @SerialName("cmd_id") val commandId: String? = null,
    val status: String? = null,
    val timestamp: String? = null,
)

@Serializable
data class ImageItem(
    @SerialName("image_id") val imageId: String,
    val url: String? = null,
    @SerialName("annotated_url") val annotatedUrl: String? = null,
    val timestamp: String? = null,
    @SerialName("photo_index") val photoIndex: Int? = null,
    @SerialName("detection_status") val detectionStatus: String? = null,
    @SerialName("disease_count") val diseaseCount: Int = 0,
    @SerialName("health_score") val healthScore: Int? = null,
)

@Serializable
data class DailyReport(
    val date: String,
    @SerialName("environment_summary") val environmentSummary: EnvironmentSummary? = null,
    val watering: WateringSummary? = null,
    @SerialName("photos_taken") val photosTaken: Int = 0,
    @SerialName("disease_alert") val diseaseAlert: Boolean = false,
    @SerialName("health_score") val healthScore: Int? = null,
    val suggestion: String = "",
    @SerialName("suggestion_detail") val suggestionDetail: SuggestionDetail? = null,
)

@Serializable
data class EnvironmentSummary(
    val temperature: StatValues? = null,
    val humidity: StatValues? = null,
    @SerialName("soil_moisture") val soilMoisture: StatValues? = null,
)

@Serializable
data class StatValues(
    val avg: Double? = null,
    val min: Double? = null,
    val max: Double? = null,
)

@Serializable
data class WateringSummary(
    val count: Int = 0,
    @SerialName("total_ml") val totalMl: Double = 0.0,
    @SerialName("trigger_reasons") val triggerReasons: List<String> = emptyList(),
)

@Serializable
data class SuggestionDetail(
    @SerialName("watering_recommendation") val wateringRecommendation: String? = null,
    @SerialName("next_watering_time") val nextWateringTime: String? = null,
    @SerialName("attention_items") val attentionItems: List<String> = emptyList(),
)

@Serializable
data class AlertItem(
    @SerialName("alert_id") val alertId: String,
    val type: String,
    val severity: String,
    val title: String,
    val message: String,
    @SerialName("image_id") val imageId: String? = null,
    val read: Boolean = false,
    @SerialName("created_at") val createdAt: String? = null,
)

@Serializable
data class PlantTypeItem(
    @SerialName("plant_type") val plantType: String,
    val name: String,
    val category: String,
    @SerialName("icon_url") val iconUrl: String? = null,
    @SerialName("default_thresholds") val defaultThresholds: PlantThresholds,
    @SerialName("watering_cfg") val wateringConfig: PlantWateringConfig,
)

@Serializable
data class CreatePlantRequest(
    @SerialName("plant_type") val plantType: String,
    val name: String,
    val category: String,
    @SerialName("default_thresholds") val defaultThresholds: PlantThresholds,
    @SerialName("watering_cfg") val wateringConfig: PlantWateringConfig,
)

@Serializable
data class UpdatePlantRequest(
    val name: String,
    val category: String,
    @SerialName("default_thresholds") val defaultThresholds: PlantThresholds,
    @SerialName("watering_cfg") val wateringConfig: PlantWateringConfig,
)

@Serializable
data class PlantThresholds(
    val temperature: RangeValues,
    val humidity: RangeValues,
    @SerialName("soil_moisture") val soilMoisture: RangeValues,
)

@Serializable
data class RangeValues(
    val min: Double,
    val max: Double,
)

@Serializable
data class PlantWateringConfig(
    @SerialName("trigger_soil_moisture") val triggerSoilMoisture: Double,
    @SerialName("default_duration_ms") val defaultDurationMs: Int,
)
