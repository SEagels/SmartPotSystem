package com.smartpot.app.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.builtins.nullable
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.net.URLEncoder
import java.nio.charset.StandardCharsets
import java.util.concurrent.TimeUnit

class SmartPotApi(
    private var baseUrl: String,
) {
    private val json = Json { ignoreUnknownKeys = true }
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .build()
    private val mediaType = "application/json; charset=utf-8".toMediaType()
    private var token: String? = null

    fun setBaseUrl(value: String) {
        baseUrl = value.trimEnd('/')
    }

    fun setToken(value: String?) {
        token = value
    }

    suspend fun login(username: String, password: String): LoginData {
        val body = json.encodeToString(LoginRequest.serializer(), LoginRequest(username, password))
        val text = execute(
            Request.Builder()
                .url("$baseUrl/auth/login")
                .post(body.toRequestBody(mediaType))
                .build()
        )
        val envelope = json.decodeFromString(
            ApiEnvelope.serializer(LoginData.serializer()),
            text,
        )
        return envelope.unwrap()
    }

    suspend fun getDevices(): List<DeviceListItem> {
        val text = execute(authorizedBuilder("$baseUrl/devices").get().build())
        val envelope = json.decodeFromString(
            ApiEnvelope.serializer(ListSerializer(DeviceListItem.serializer())),
            text,
        )
        return envelope.unwrap()
    }

    suspend fun getDevice(deviceId: String): DeviceDetail {
        val text = execute(authorizedBuilder("$baseUrl/devices/$deviceId").get().build())
        val envelope = json.decodeFromString(
            ApiEnvelope.serializer(DeviceDetail.serializer()),
            text,
        )
        return envelope.unwrap()
    }

    suspend fun getLatestTelemetry(deviceId: String): LatestTelemetry? {
        val text = execute(authorizedBuilder("$baseUrl/devices/$deviceId/telemetry/latest").get().build())
        val envelope = json.decodeFromString(
            ApiEnvelope.serializer(LatestTelemetry.serializer().nullable),
            text,
        )
        return envelope.data
    }

    suspend fun discoverLanDevices(cidr: String?): List<LanDeviceCandidate> {
        val suffix = if (cidr.isNullOrBlank()) {
            ""
        } else {
            "?cidr=${URLEncoder.encode(cidr, StandardCharsets.UTF_8.name())}"
        }
        val text = execute(authorizedBuilder("$baseUrl/devices/lan-discover$suffix").get().build())
        val envelope = json.decodeFromString(
            ApiEnvelope.serializer(ListSerializer(LanDeviceCandidate.serializer())),
            text,
        )
        return envelope.unwrap()
    }

    suspend fun bindLanDevice(candidate: LanDeviceCandidate): DeviceListItem? {
        val body = json.encodeToString(
            LanBindRequest.serializer(),
            LanBindRequest(candidate.deviceId, candidate.ip),
        )
        val text = execute(
            authorizedBuilder("$baseUrl/devices/lan-bind")
                .post(body.toRequestBody(mediaType))
                .build()
        )
        val envelope = json.decodeFromString(
            ApiEnvelope.serializer(DeviceListItem.serializer().nullable),
            text,
        )
        return envelope.data
    }

    suspend fun water(deviceId: String, durationMs: Int) {
        val body = json.encodeToString(WaterRequest.serializer(), WaterRequest(durationMs))
        val text = execute(
            authorizedBuilder("$baseUrl/devices/$deviceId/water")
                .post(body.toRequestBody(mediaType))
                .build()
        )
        val envelope = json.decodeFromString(ApiEnvelope.serializer(kotlinx.serialization.json.JsonObject.serializer()), text)
        envelope.unwrap()
    }

    suspend fun photo(deviceId: String, burstCount: Int = 1): CommandResult? {
        val body = json.encodeToString(PhotoRequest.serializer(), PhotoRequest(burstCount))
        val text = execute(
            authorizedBuilder("$baseUrl/devices/$deviceId/photo")
                .post(body.toRequestBody(mediaType))
                .build()
        )
        val envelope = json.decodeFromString(
            ApiEnvelope.serializer(CommandResult.serializer().nullable),
            text,
        )
        return envelope.data
    }

    suspend fun getDailyReport(deviceId: String, date: String): DailyReport {
        val encodedDate = URLEncoder.encode(date, StandardCharsets.UTF_8.name())
        val text = execute(authorizedBuilder("$baseUrl/devices/$deviceId/reports/daily?date=$encodedDate").get().build())
        val envelope = json.decodeFromString(
            ApiEnvelope.serializer(DailyReport.serializer()),
            text,
        )
        return envelope.unwrap()
    }

    suspend fun getImages(deviceId: String): List<ImageItem> {
        val text = execute(authorizedBuilder("$baseUrl/devices/$deviceId/images").get().build())
        val envelope = json.decodeFromString(
            ApiEnvelope.serializer(ListSerializer(ImageItem.serializer())),
            text,
        )
        return envelope.unwrap().map { item ->
            item.copy(
                url = item.url?.let(::absoluteUrl),
                annotatedUrl = item.annotatedUrl?.let(::absoluteUrl),
            )
        }
    }

    suspend fun getAlerts(deviceId: String, status: String? = null): List<AlertItem> {
        val suffix = status?.takeIf { it.isNotBlank() }?.let {
            "?status=${URLEncoder.encode(it, StandardCharsets.UTF_8.name())}&page_size=50"
        } ?: "?page_size=50"
        val text = execute(authorizedBuilder("$baseUrl/devices/$deviceId/alerts$suffix").get().build())
        val envelope = json.decodeFromString(
            ApiEnvelope.serializer(ListSerializer(AlertItem.serializer())),
            text,
        )
        return envelope.unwrap()
    }

    suspend fun markAlertRead(alertId: String) {
        val text = execute(authorizedBuilder("$baseUrl/alerts/$alertId/read").put("{}".toRequestBody(mediaType)).build())
        val envelope = json.decodeFromString(ApiEnvelope.serializer(kotlinx.serialization.json.JsonObject.serializer().nullable), text)
        if (envelope.code != 0) throw IllegalStateException(envelope.message)
    }

    suspend fun markAllAlertsRead(deviceId: String) {
        val text = execute(authorizedBuilder("$baseUrl/devices/$deviceId/alerts/read-all").put("{}".toRequestBody(mediaType)).build())
        val envelope = json.decodeFromString(ApiEnvelope.serializer(kotlinx.serialization.json.JsonObject.serializer().nullable), text)
        if (envelope.code != 0) throw IllegalStateException(envelope.message)
    }

    suspend fun getPlants(): List<PlantTypeItem> {
        val text = execute(authorizedBuilder("$baseUrl/plants").get().build())
        val envelope = json.decodeFromString(
            ApiEnvelope.serializer(ListSerializer(PlantTypeItem.serializer())),
            text,
        )
        return envelope.unwrap()
    }

    suspend fun createPlant(request: CreatePlantRequest): PlantTypeItem {
        val body = json.encodeToString(CreatePlantRequest.serializer(), request)
        val text = execute(
            authorizedBuilder("$baseUrl/plants")
                .post(body.toRequestBody(mediaType))
                .build()
        )
        val envelope = json.decodeFromString(
            ApiEnvelope.serializer(PlantTypeItem.serializer()),
            text,
        )
        return envelope.unwrap()
    }

    suspend fun updatePlant(plantType: String, request: UpdatePlantRequest): PlantTypeItem {
        val encodedType = URLEncoder.encode(plantType, StandardCharsets.UTF_8.name())
        val body = json.encodeToString(UpdatePlantRequest.serializer(), request)
        val text = execute(
            authorizedBuilder("$baseUrl/plants/$encodedType")
                .put(body.toRequestBody(mediaType))
                .build()
        )
        val envelope = json.decodeFromString(
            ApiEnvelope.serializer(PlantTypeItem.serializer()),
            text,
        )
        return envelope.unwrap()
    }

    suspend fun deletePlant(plantType: String) {
        val encodedType = URLEncoder.encode(plantType, StandardCharsets.UTF_8.name())
        val text = execute(authorizedBuilder("$baseUrl/plants/$encodedType").delete().build())
        val envelope = json.decodeFromString(ApiEnvelope.serializer(kotlinx.serialization.json.JsonObject.serializer().nullable), text)
        if (envelope.code != 0) throw IllegalStateException(envelope.message)
    }

    private fun absoluteUrl(value: String): String {
        if (value.startsWith("http://") || value.startsWith("https://")) return value
        val origin = baseUrl.removeSuffix("/v1")
        return if (value.startsWith("/")) "$origin$value" else "$origin/$value"
    }

    private fun authorizedBuilder(url: String): Request.Builder {
        val builder = Request.Builder().url(url)
        token?.let { builder.header("Authorization", "Bearer $it") }
        return builder
    }

    private suspend fun execute(request: Request): String = withContext(Dispatchers.IO) {
        client.newCall(request).execute().use { response ->
            val body = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                throw IllegalStateException("HTTP ${response.code}: $body")
            }
            body
        }
    }
}

private fun <T> ApiEnvelope<T>.unwrap(): T {
    if (code != 0) throw IllegalStateException(message)
    return data ?: throw IllegalStateException("响应数据为空")
}
