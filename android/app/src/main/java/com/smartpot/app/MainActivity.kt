package com.smartpot.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.smartpot.app.data.AlertItem
import com.smartpot.app.data.CreatePlantRequest
import com.smartpot.app.data.DailyReport
import com.smartpot.app.data.DeviceDetail
import com.smartpot.app.data.DeviceListItem
import com.smartpot.app.data.ImageItem
import com.smartpot.app.data.LanDeviceCandidate
import com.smartpot.app.data.LatestTelemetry
import com.smartpot.app.data.PlantTypeItem
import com.smartpot.app.data.PlantThresholds
import com.smartpot.app.data.PlantWateringConfig
import com.smartpot.app.data.RangeValues
import com.smartpot.app.data.SmartPotApi
import com.smartpot.app.data.UpdatePlantRequest
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

private val Moss = Color(0xFF14532D)
private val Leaf = Color(0xFF15803D)
private val Mint = Color(0xFFEAF7EE)
private val Linen = Color(0xFFFFFBF2)
private val Amber = Color(0xFFD97706)
private val Ink = Color(0xFF102018)
private val Muted = Color(0xFF64746A)
private val Glass = Color.White.copy(alpha = 0.68f)

private enum class AppModule {
    Devices,
    Alerts,
    Plants,
}

private data class AlertWithDevice(
    val alert: AlertItem,
    val device: DeviceListItem,
)

private data class DetailBundle(
    val device: DeviceDetail,
    val telemetry: LatestTelemetry?,
    val report: DailyReport?,
    val images: List<ImageItem>,
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(
                colorScheme = lightColorScheme(
                    primary = Leaf,
                    secondary = Amber,
                    background = Mint,
                    surface = Color.White,
                    onPrimary = Color.White,
                    onSurface = Ink,
                ),
            ) {
                Surface(modifier = Modifier.fillMaxSize(), color = Mint) {
                    SmartPotApp()
                }
            }
        }
    }
}

@Composable
private fun SmartPotApp() {
    val api = remember { SmartPotApi("http://10.0.2.2:8000/v1") }
    val scope = rememberCoroutineScope()
    var username by remember { mutableStateOf("demo_user") }
    var password by remember { mutableStateOf("123456") }
    var loggedIn by remember { mutableStateOf(false) }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var devices by remember { mutableStateOf<List<DeviceListItem>>(emptyList()) }
    var candidates by remember { mutableStateOf<List<LanDeviceCandidate>>(emptyList()) }
    var selectedTelemetry by remember { mutableStateOf<LatestTelemetry?>(null) }
    var selectedDevice by remember { mutableStateOf<DeviceListItem?>(null) }
    var detailDevice by remember { mutableStateOf<DeviceDetail?>(null) }
    var detailReport by remember { mutableStateOf<DailyReport?>(null) }
    var detailImages by remember { mutableStateOf<List<ImageItem>>(emptyList()) }
    var currentModule by remember { mutableStateOf(AppModule.Devices) }
    var alerts by remember { mutableStateOf<List<AlertWithDevice>>(emptyList()) }
    var plants by remember { mutableStateOf<List<PlantTypeItem>>(emptyList()) }

    fun refreshDevices() {
        scope.launch {
            loading = true
            error = null
            runCatching { api.getDevices() }
                .onSuccess { devices = it }
                .onFailure { error = it.message ?: "设备列表加载失败" }
            loading = false
        }
    }

    fun loadAlerts(sourceDevices: List<DeviceListItem> = devices) {
        scope.launch {
            loading = true
            error = null
            runCatching {
                sourceDevices.flatMap { device ->
                    runCatching { api.getAlerts(device.deviceId) }
                        .getOrDefault(emptyList())
                        .map { AlertWithDevice(it, device) }
                }.sortedByDescending { it.alert.createdAt ?: "" }
            }.onSuccess {
                alerts = it
            }.onFailure {
                error = it.message ?: "告警加载失败"
            }
            loading = false
        }
    }

    fun loadPlants() {
        scope.launch {
            loading = true
            error = null
            runCatching { api.getPlants() }
                .onSuccess { plants = it }
                .onFailure { error = it.message ?: "植物品种加载失败" }
            loading = false
        }
    }

    fun createPlant(request: CreatePlantRequest) {
        scope.launch {
            loading = true
            error = null
            runCatching { api.createPlant(request) }
                .onSuccess { loadPlants() }
                .onFailure { error = it.message ?: "植物品种添加失败" }
            loading = false
        }
    }

    fun updatePlant(plantType: String, request: UpdatePlantRequest) {
        scope.launch {
            loading = true
            error = null
            runCatching { api.updatePlant(plantType, request) }
                .onSuccess { loadPlants() }
                .onFailure { error = it.message ?: "植物品种修改失败" }
            loading = false
        }
    }

    fun deletePlant(plantType: String) {
        scope.launch {
            loading = true
            error = null
            runCatching { api.deletePlant(plantType) }
                .onSuccess { loadPlants() }
                .onFailure { error = it.message ?: "植物品种删除失败" }
            loading = false
        }
    }

    fun openDevice(device: DeviceListItem) {
        selectedDevice = device
        scope.launch {
            loading = true
            error = null
            detailDevice = null
            detailReport = null
            detailImages = emptyList()
            selectedTelemetry = null
            runCatching {
                val today = SimpleDateFormat("yyyy-MM-dd", Locale.US).format(Date())
                DetailBundle(
                    device = api.getDevice(device.deviceId),
                    telemetry = api.getLatestTelemetry(device.deviceId),
                    report = runCatching { api.getDailyReport(device.deviceId, today) }.getOrNull(),
                    images = runCatching { api.getImages(device.deviceId) }.getOrDefault(emptyList()),
                )
            }.onSuccess {
                detailDevice = it.device
                selectedTelemetry = it.telemetry
                detailReport = it.report
                detailImages = it.images
            }.onFailure {
                error = it.message ?: "设备详情加载失败"
            }
            loading = false
        }
    }

    GlassScaffold {
        if (!loggedIn) {
            LoginScreen(
                username = username,
                password = password,
                loading = loading,
                error = error,
                onUsernameChange = { username = it },
                onPasswordChange = { password = it },
                onLogin = {
                    scope.launch {
                        loading = true
                        error = null
                        runCatching { api.login(username, password) }
                            .onSuccess {
                                api.setToken(it.token)
                                loggedIn = true
                                currentModule = AppModule.Devices
                                refreshDevices()
                            }
                            .onFailure { error = it.message ?: "登录失败" }
                        loading = false
                    }
                },
            )
        } else if (selectedDevice != null) {
            DeviceDetailScreen(
                device = selectedDevice!!,
                detail = detailDevice,
                telemetry = selectedTelemetry,
                report = detailReport,
                images = detailImages,
                loading = loading,
                error = error,
                onBack = {
                    selectedDevice = null
                    detailDevice = null
                    detailReport = null
                    detailImages = emptyList()
                    selectedTelemetry = null
                    error = null
                    refreshDevices()
                },
                onRefresh = { openDevice(selectedDevice!!) },
                onWater = {
                    scope.launch {
                        loading = true
                        error = null
                        runCatching { api.water(selectedDevice!!.deviceId, 5000) }
                            .onFailure { error = it.message ?: "补水指令发送失败" }
                        loading = false
                    }
                },
                onPhoto = {
                    scope.launch {
                        loading = true
                        error = null
                        runCatching { api.photo(selectedDevice!!.deviceId, 1) }
                            .onSuccess { openDevice(selectedDevice!!) }
                            .onFailure { error = it.message ?: "拍照指令发送失败" }
                        loading = false
                    }
                },
            )
        } else {
            Box(modifier = Modifier.fillMaxSize()) {
                when (currentModule) {
                    AppModule.Devices -> DashboardScreen(
                        loading = loading,
                        error = error,
                        devices = devices,
                        candidates = candidates,
                        selectedTelemetry = selectedTelemetry,
                        onRefresh = { refreshDevices() },
                        onLogout = {
                            api.setToken(null)
                            loggedIn = false
                            currentModule = AppModule.Devices
                            devices = emptyList()
                            candidates = emptyList()
                            alerts = emptyList()
                            plants = emptyList()
                            selectedTelemetry = null
                            error = null
                        },
                        onOpenAlerts = {
                            currentModule = AppModule.Alerts
                            loadAlerts()
                        },
                        onDiscover = {
                            scope.launch {
                                loading = true
                                error = null
                                runCatching { api.discoverLanDevices(null) }
                                    .onSuccess { candidates = it }
                                    .onFailure { error = it.message ?: "局域网扫描失败" }
                                loading = false
                            }
                        },
                        onBindCandidate = { candidate ->
                            scope.launch {
                                loading = true
                                error = null
                                runCatching { api.bindLanDevice(candidate) }
                                    .onSuccess {
                                        candidates = candidates.filterNot { it.deviceId == candidate.deviceId }
                                        refreshDevices()
                                    }
                                    .onFailure { error = it.message ?: "设备绑定失败" }
                                loading = false
                            }
                        },
                        onLoadTelemetry = { openDevice(it) },
                        onOpenDevice = { openDevice(it) },
                        onWater = { device ->
                            scope.launch {
                                loading = true
                                error = null
                                runCatching { api.water(device.deviceId, 5000) }
                                    .onFailure { error = it.message ?: "补水指令发送失败" }
                                loading = false
                            }
                        },
                    )
                    AppModule.Alerts -> AlertsScreen(
                        loading = loading,
                        error = error,
                        alerts = alerts,
                        unreadCount = alerts.count { !it.alert.read },
                        onRefresh = { loadAlerts() },
                        onMarkRead = { item ->
                            scope.launch {
                                loading = true
                                error = null
                                runCatching { api.markAlertRead(item.alert.alertId) }
                                    .onSuccess {
                                        alerts = alerts.map {
                                            if (it.alert.alertId == item.alert.alertId) it.copy(alert = it.alert.copy(read = true)) else it
                                        }
                                    }
                                    .onFailure { error = it.message ?: "标记已读失败" }
                                loading = false
                            }
                        },
                        onMarkDeviceRead = { device ->
                            scope.launch {
                                loading = true
                                error = null
                                runCatching { api.markAllAlertsRead(device.deviceId) }
                                    .onSuccess {
                                        alerts = alerts.map {
                                            if (it.device.deviceId == device.deviceId) it.copy(alert = it.alert.copy(read = true)) else it
                                        }
                                    }
                                    .onFailure { error = it.message ?: "批量标记失败" }
                                loading = false
                            }
                        },
                        onOpenDevice = { openDevice(it) },
                    )
                    AppModule.Plants -> PlantTypesScreen(
                        loading = loading,
                        error = error,
                        plants = plants,
                        onRefresh = { loadPlants() },
                        onCreatePlant = { createPlant(it) },
                        onUpdatePlant = { plantType, request -> updatePlant(plantType, request) },
                        onDeletePlant = { deletePlant(it) },
                    )
                }
                BottomModuleBar(
                    current = currentModule,
                    alertCount = devices.count { it.hasActiveAlert },
                    modifier = Modifier.align(Alignment.BottomCenter),
                    onSelect = {
                        currentModule = it
                        error = null
                        when (it) {
                            AppModule.Devices -> refreshDevices()
                            AppModule.Alerts -> loadAlerts()
                            AppModule.Plants -> loadPlants()
                        }
                    },
                )
            }
        }
    }
}

@Composable
private fun GlassScaffold(content: @Composable () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    listOf(Color(0xFFE7F6EC), Linen, Color(0xFFDFF1E5)),
                ),
            ),
    ) {
        BotanicalBackground()
        Box(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .padding(horizontal = 18.dp),
        ) {
            content()
        }
    }
}

@Composable
private fun BotanicalBackground() {
    Canvas(modifier = Modifier.fillMaxSize()) {
        val leafPath = Path().apply {
            moveTo(size.width * 0.74f, size.height * 0.06f)
            cubicTo(size.width * 0.98f, size.height * 0.12f, size.width * 0.92f, size.height * 0.34f, size.width * 0.68f, size.height * 0.31f)
            cubicTo(size.width * 0.56f, size.height * 0.17f, size.width * 0.62f, size.height * 0.08f, size.width * 0.74f, size.height * 0.06f)
        }
        drawPath(leafPath, color = Color(0xFFBFE8C9).copy(alpha = 0.38f))
        drawLine(
            color = Leaf.copy(alpha = 0.18f),
            start = Offset(size.width * 0.64f, size.height * 0.30f),
            end = Offset(size.width * 0.88f, size.height * 0.11f),
            strokeWidth = 3.dp.toPx(),
        )
        drawRoundRect(
            color = Color.White.copy(alpha = 0.36f),
            topLeft = Offset(-size.width * 0.10f, size.height * 0.72f),
            size = androidx.compose.ui.geometry.Size(size.width * 1.2f, size.height * 0.22f),
            cornerRadius = androidx.compose.ui.geometry.CornerRadius(36.dp.toPx(), 36.dp.toPx()),
            style = Stroke(width = 1.dp.toPx()),
        )
    }
}

@Composable
private fun LoginScreen(
    username: String,
    password: String,
    loading: Boolean,
    error: String?,
    onUsernameChange: (String) -> Unit,
    onPasswordChange: (String) -> Unit,
    onLogin: () -> Unit,
) {
    LazyColumn(verticalArrangement = Arrangement.spacedBy(18.dp)) {
        item {
            Spacer(Modifier.height(18.dp))
            Text("SmartPot Home", color = Moss, fontSize = 34.sp, fontWeight = FontWeight.Bold)
            Text("智能盆栽 · 家居绿意养护", color = Muted, fontSize = 14.sp)
        }
        item {
            GlassCard {
                Text("欢迎回来", color = Ink, fontSize = 22.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(18.dp))
                AppTextField(username, onUsernameChange, "用户名")
                Spacer(Modifier.height(10.dp))
                AppTextField(password, onPasswordChange, "密码", isPassword = true)
                error?.let {
                    Spacer(Modifier.height(12.dp))
                    ErrorBanner(it)
                }
                Spacer(Modifier.height(18.dp))
                PrimaryAction("登录", loading, onLogin)
            }
        }
    }
}

@Composable
private fun DashboardScreen(
    loading: Boolean,
    error: String?,
    devices: List<DeviceListItem>,
    candidates: List<LanDeviceCandidate>,
    selectedTelemetry: LatestTelemetry?,
    onRefresh: () -> Unit,
    onLogout: () -> Unit,
    onOpenAlerts: () -> Unit,
    onDiscover: () -> Unit,
    onBindCandidate: (LanDeviceCandidate) -> Unit,
    onLoadTelemetry: (DeviceListItem) -> Unit,
    onOpenDevice: (DeviceListItem) -> Unit,
    onWater: (DeviceListItem) -> Unit,
) {
    LazyColumn(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        item { Header(devices = devices, loading = loading, onRefresh = onRefresh, onLogout = onLogout, onOpenAlerts = onOpenAlerts) }
        item { QuickActions(loading = loading, onDiscover = onDiscover, onRefresh = onRefresh) }
        error?.let { item { ErrorBanner(it) } }
        if (candidates.isNotEmpty()) {
            item { SectionTitle("发现的设备", "绑定同一 WiFi 下的 ESP32") }
            items(candidates) { candidate ->
                CandidateCard(candidate, onBind = { onBindCandidate(candidate) })
            }
        }
        item { SectionTitle("我的盆栽", "环境状态、在线情况与快捷控制") }
        if (devices.isEmpty() && !loading) {
            item { EmptyState() }
        }
        items(devices) { device ->
            DeviceCard(
                device = device,
                telemetry = selectedTelemetry?.takeIf { it.deviceId == device.deviceId },
                onLoadTelemetry = { onLoadTelemetry(device) },
                onOpen = { onOpenDevice(device) },
                onWater = { onWater(device) },
            )
        }
        item { Spacer(Modifier.height(98.dp)) }
    }
}

@Composable
private fun AlertsScreen(
    loading: Boolean,
    error: String?,
    alerts: List<AlertWithDevice>,
    unreadCount: Int,
    onRefresh: () -> Unit,
    onMarkRead: (AlertWithDevice) -> Unit,
    onMarkDeviceRead: (DeviceListItem) -> Unit,
    onOpenDevice: (DeviceListItem) -> Unit,
) {
    LazyColumn(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        item {
            Spacer(Modifier.height(10.dp))
            GlassCard {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text("告警中心", color = Moss, fontSize = 28.sp, fontWeight = FontWeight.Bold)
                        Text("聚合所有盆栽的未读告警与历史记录", color = Muted, fontSize = 13.sp)
                    }
                    StatusBadge(if (loading) "同步中" else "$unreadCount 未读", unreadCount > 0 || loading)
                }
                Spacer(Modifier.height(14.dp))
                SecondaryAction("刷新告警", enabled = !loading, onClick = onRefresh)
            }
        }
        error?.let { item { ErrorBanner(it) } }
        if (alerts.isEmpty() && !loading) {
            item {
                GlassCard {
                    Text("暂无告警", color = Ink, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                    Text("设备离线、传感器异常、补水失败或病害识别风险会出现在这里。", color = Muted, fontSize = 13.sp)
                }
            }
        }
        items(alerts) { item ->
            AlertCard(
                item = item,
                onMarkRead = { onMarkRead(item) },
                onMarkDeviceRead = { onMarkDeviceRead(item.device) },
                onOpenDevice = { onOpenDevice(item.device) },
            )
        }
        item { Spacer(Modifier.height(98.dp)) }
    }
}

@Composable
private fun PlantTypesScreen(
    loading: Boolean,
    error: String?,
    plants: List<PlantTypeItem>,
    onRefresh: () -> Unit,
    onCreatePlant: (CreatePlantRequest) -> Unit,
    onUpdatePlant: (String, UpdatePlantRequest) -> Unit,
    onDeletePlant: (String) -> Unit,
) {
    var showAddForm by remember { mutableStateOf(false) }
    var editingPlant by remember { mutableStateOf<PlantTypeItem?>(null) }
    var formError by remember { mutableStateOf<String?>(null) }
    var plantType by remember { mutableStateOf("") }
    var plantName by remember { mutableStateOf("") }
    var category by remember { mutableStateOf("foliage") }
    var tempMin by remember { mutableStateOf("15") }
    var tempMax by remember { mutableStateOf("30") }
    var humidityMin by remember { mutableStateOf("30") }
    var humidityMax by remember { mutableStateOf("80") }
    var soilMin by remember { mutableStateOf("20") }
    var soilMax by remember { mutableStateOf("70") }
    var triggerSoil by remember { mutableStateOf("25") }
    var durationMs by remember { mutableStateOf("5000") }

    fun resetForm() {
        plantType = ""
        plantName = ""
        category = "foliage"
        tempMin = "15"
        tempMax = "30"
        humidityMin = "30"
        humidityMax = "80"
        soilMin = "20"
        soilMax = "70"
        triggerSoil = "25"
        durationMs = "5000"
        formError = null
    }

    fun fillForm(plant: PlantTypeItem) {
        plantType = plant.plantType
        plantName = plant.name
        category = plant.category
        tempMin = plant.defaultThresholds.temperature.min.toString()
        tempMax = plant.defaultThresholds.temperature.max.toString()
        humidityMin = plant.defaultThresholds.humidity.min.toString()
        humidityMax = plant.defaultThresholds.humidity.max.toString()
        soilMin = plant.defaultThresholds.soilMoisture.min.toString()
        soilMax = plant.defaultThresholds.soilMoisture.max.toString()
        triggerSoil = plant.wateringConfig.triggerSoilMoisture.toString()
        durationMs = plant.wateringConfig.defaultDurationMs.toString()
        formError = null
    }

    fun startEdit(plant: PlantTypeItem) {
        editingPlant = plant
        showAddForm = true
        fillForm(plant)
    }

    fun submit() {
        val code = plantType.trim()
        val name = plantName.trim()
        val categoryValue = category.trim().ifBlank { "foliage" }
        val tMin = tempMin.toDoubleOrNull()
        val tMax = tempMax.toDoubleOrNull()
        val hMin = humidityMin.toDoubleOrNull()
        val hMax = humidityMax.toDoubleOrNull()
        val sMin = soilMin.toDoubleOrNull()
        val sMax = soilMax.toDoubleOrNull()
        val trigger = triggerSoil.toDoubleOrNull()
        val duration = durationMs.toIntOrNull()
        if (code.isBlank() || name.isBlank()) {
            formError = "请填写品种代码和品种名称"
            return
        }
        if (listOf(tMin, tMax, hMin, hMax, sMin, sMax, trigger).any { it == null } || duration == null) {
            formError = "阈值和补水参数必须是数字"
            return
        }
        val thresholds = PlantThresholds(
            temperature = RangeValues(tMin!!, tMax!!),
            humidity = RangeValues(hMin!!, hMax!!),
            soilMoisture = RangeValues(sMin!!, sMax!!),
        )
        val watering = PlantWateringConfig(
            triggerSoilMoisture = trigger!!,
            defaultDurationMs = duration,
        )
        val editing = editingPlant
        if (editing == null) {
            onCreatePlant(
                CreatePlantRequest(
                    plantType = code,
                    name = name,
                    category = categoryValue,
                    defaultThresholds = thresholds,
                    wateringConfig = watering,
                ),
            )
        } else {
            onUpdatePlant(
                editing.plantType,
                UpdatePlantRequest(
                    name = name,
                    category = categoryValue,
                    defaultThresholds = thresholds,
                    wateringConfig = watering,
                ),
            )
        }
        showAddForm = false
        editingPlant = null
        resetForm()
    }

    LazyColumn(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        item {
            Spacer(Modifier.height(10.dp))
            GlassCard {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text("植物品种", color = Moss, fontSize = 28.sp, fontWeight = FontWeight.Bold)
                        Text("查看不同植物的推荐环境阈值与默认补水参数", color = Muted, fontSize = 13.sp)
                    }
                    StatusBadge(if (loading) "同步中" else "${plants.size} 种", plants.isNotEmpty() || loading)
                }
                Spacer(Modifier.height(14.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                    SecondaryAction("刷新品种", enabled = !loading, modifier = Modifier.weight(1f), onClick = onRefresh)
                    SecondaryAction(
                        if (showAddForm) "收起表单" else "添加品种",
                        enabled = !loading,
                        modifier = Modifier.weight(1f),
                        onClick = {
                            if (showAddForm) {
                                showAddForm = false
                                editingPlant = null
                                resetForm()
                            } else {
                                resetForm()
                                showAddForm = true
                            }
                        },
                    )
                }
            }
        }
        error?.let { item { ErrorBanner(it) } }
        if (showAddForm) {
            item {
                PlantCreateForm(
                    loading = loading,
                    formError = formError,
                    plantType = plantType,
                    plantName = plantName,
                    category = category,
                    tempMin = tempMin,
                    tempMax = tempMax,
                    humidityMin = humidityMin,
                    humidityMax = humidityMax,
                    soilMin = soilMin,
                    soilMax = soilMax,
                    triggerSoil = triggerSoil,
                    durationMs = durationMs,
                    onPlantTypeChange = { plantType = it },
                    onPlantNameChange = { plantName = it },
                    onCategoryChange = { category = it },
                    onTempMinChange = { tempMin = it },
                    onTempMaxChange = { tempMax = it },
                    onHumidityMinChange = { humidityMin = it },
                    onHumidityMaxChange = { humidityMax = it },
                    onSoilMinChange = { soilMin = it },
                    onSoilMaxChange = { soilMax = it },
                    onTriggerSoilChange = { triggerSoil = it },
                    onDurationMsChange = { durationMs = it },
                    onSubmit = { submit() },
                    editing = editingPlant != null,
                )
            }
        }
        if (plants.isEmpty() && !loading) {
            item {
                GlassCard {
                    Text("暂无植物品种", color = Ink, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                    Text("后端 /plants 接口返回品种后，会在这里显示适宜温湿度、土壤湿度和补水规则。", color = Muted, fontSize = 13.sp)
                }
            }
        }
        items(plants) { plant ->
            PlantTypeCard(
                plant = plant,
                loading = loading,
                onEdit = { startEdit(plant) },
                onDelete = { onDeletePlant(plant.plantType) },
            )
        }
        item { Spacer(Modifier.height(98.dp)) }
    }
}

@Composable
private fun PlantCreateForm(
    loading: Boolean,
    formError: String?,
    plantType: String,
    plantName: String,
    category: String,
    tempMin: String,
    tempMax: String,
    humidityMin: String,
    humidityMax: String,
    soilMin: String,
    soilMax: String,
    triggerSoil: String,
    durationMs: String,
    onPlantTypeChange: (String) -> Unit,
    onPlantNameChange: (String) -> Unit,
    onCategoryChange: (String) -> Unit,
    onTempMinChange: (String) -> Unit,
    onTempMaxChange: (String) -> Unit,
    onHumidityMinChange: (String) -> Unit,
    onHumidityMaxChange: (String) -> Unit,
    onSoilMinChange: (String) -> Unit,
    onSoilMaxChange: (String) -> Unit,
    onTriggerSoilChange: (String) -> Unit,
    onDurationMsChange: (String) -> Unit,
    onSubmit: () -> Unit,
    editing: Boolean,
) {
    GlassCard {
        Text(if (editing) "修改植物品种" else "添加植物品种", color = Ink, fontSize = 20.sp, fontWeight = FontWeight.Bold)
        Text(if (editing) "品种代码不可修改，可调整名称、分类和养护参数。" else "与 Web 端一致，可配置默认环境阈值和补水规则。", color = Muted, fontSize = 12.sp)
        Spacer(Modifier.height(14.dp))
        AppTextField(plantType, onPlantTypeChange, "品种代码，例如 rose")
        Spacer(Modifier.height(10.dp))
        AppTextField(plantName, onPlantNameChange, "品种名称，例如 玫瑰")
        Spacer(Modifier.height(10.dp))
        AppTextField(category, onCategoryChange, "分类：foliage / succulent / flowering / herb")
        Spacer(Modifier.height(14.dp))
        SectionTitle("环境阈值", "填写数字即可")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            AppTextField(tempMin, onTempMinChange, "最低温度", modifier = Modifier.weight(1f))
            AppTextField(tempMax, onTempMaxChange, "最高温度", modifier = Modifier.weight(1f))
        }
        Spacer(Modifier.height(8.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            AppTextField(humidityMin, onHumidityMinChange, "最低湿度", modifier = Modifier.weight(1f))
            AppTextField(humidityMax, onHumidityMaxChange, "最高湿度", modifier = Modifier.weight(1f))
        }
        Spacer(Modifier.height(8.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            AppTextField(soilMin, onSoilMinChange, "土壤湿度下限", modifier = Modifier.weight(1f))
            AppTextField(soilMax, onSoilMaxChange, "土壤湿度上限", modifier = Modifier.weight(1f))
        }
        Spacer(Modifier.height(14.dp))
        SectionTitle("补水配置", "低于触发值时提示或执行补水")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            AppTextField(triggerSoil, onTriggerSoilChange, "触发土壤湿度", modifier = Modifier.weight(1f))
            AppTextField(durationMs, onDurationMsChange, "默认时长(ms)", modifier = Modifier.weight(1f))
        }
        formError?.let {
            Spacer(Modifier.height(12.dp))
            ErrorBanner(it)
        }
        Spacer(Modifier.height(14.dp))
        PrimaryAction(if (editing) "保存修改" else "保存品种", loading, onSubmit)
    }
}

@Composable
private fun DeviceDetailScreen(
    device: DeviceListItem,
    detail: DeviceDetail?,
    telemetry: LatestTelemetry?,
    report: DailyReport?,
    images: List<ImageItem>,
    loading: Boolean,
    error: String?,
    onBack: () -> Unit,
    onRefresh: () -> Unit,
    onWater: () -> Unit,
    onPhoto: () -> Unit,
) {
    val displayName = detail?.name?.ifBlank { device.name } ?: device.name.ifBlank { device.deviceId }
    LazyColumn(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        item {
            Spacer(Modifier.height(10.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Button(
                    onClick = onBack,
                    modifier = Modifier.height(42.dp),
                    shape = RoundedCornerShape(14.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color.White.copy(alpha = 0.66f), contentColor = Moss),
                    border = BorderStroke(1.dp, Color.White.copy(alpha = 0.84f)),
                ) {
                    Text("返回", fontWeight = FontWeight.SemiBold)
                }
                Column(modifier = Modifier.weight(1f).padding(start = 12.dp)) {
                    Text(displayName, color = Moss, fontSize = 26.sp, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(device.deviceId, color = Muted, fontSize = 12.sp)
                }
                StatusBadge(if (detail?.online ?: device.online) "在线" else "离线", detail?.online ?: device.online)
            }
        }
        error?.let { item { ErrorBanner(it) } }
        item {
            GlassCard {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    DeviceGlyph(active = detail?.online ?: device.online)
                    Column(modifier = Modifier.weight(1f).padding(start = 12.dp)) {
                        Text(detail?.plantTypeName ?: device.plantTypeName ?: "未设置植物品种", color = Ink, fontSize = 19.sp, fontWeight = FontWeight.Bold)
                        Text("固件 ${detail?.firmwareVersion ?: "--"}", color = Muted, fontSize = 12.sp)
                    }
                    StatusBadge(if (loading) "同步中" else "实时", loading || (detail?.online ?: device.online))
                }
                Spacer(Modifier.height(16.dp))
                ActionRow(loading = loading, online = detail?.online ?: device.online, onRefresh = onRefresh, onWater = onWater, onPhoto = onPhoto)
            }
        }
        item { SectionTitle("传感器数据", "设备最新上报的环境读数") }
        item {
            GlassCard {
                telemetry?.let {
                    MetricGrid(it)
                    Spacer(Modifier.height(12.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                        MiniMetric("WiFi", "${it.system.wifiRssi ?: "--"} dBm", Modifier.weight(1f))
                        MiniMetric("运行", "${it.system.uptimeSeconds ?: "--"} 秒", Modifier.weight(1f))
                    }
                    Text("更新时间 ${it.timestamp}", color = Muted, fontSize = 12.sp, modifier = Modifier.padding(top = 10.dp))
                } ?: EmptyInline("暂无遥测数据，设备上报后点击刷新即可查看。")
            }
        }
        item { SectionTitle("大模型养护建议", "根据当天环境与病害状态生成") }
        item { CareAdviceCard(report = report, loading = loading) }
        item { SectionTitle("病害照片", "摄像头采集与识别结果") }
        if (images.isEmpty()) {
            item {
                GlassCard {
                    EmptyInline("暂无病害照片，点击拍照可让 ESP32 摄像头采集新图片。")
                }
            }
        } else {
            items(images.take(8)) { image -> ImageCard(image) }
        }
        item { Spacer(Modifier.height(28.dp)) }
    }
}

@Composable
private fun Header(
    devices: List<DeviceListItem>,
    loading: Boolean,
    onRefresh: () -> Unit,
    onLogout: () -> Unit,
    onOpenAlerts: () -> Unit,
) {
    val onlineCount = devices.count { it.online }
    val alertCount = devices.count { it.hasActiveAlert }
    GlassCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(modifier = Modifier.weight(1f)) {
                Text("智能盆栽", color = Moss, fontSize = 30.sp, fontWeight = FontWeight.Bold)
                Text("家中绿意、环境数据与远程控制", color = Muted, fontSize = 13.sp)
            }
            StatusBadge(if (loading) "同步中" else "$onlineCount/${devices.size} 在线", loading || onlineCount > 0)
        }
        Spacer(Modifier.height(18.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            SummaryTile("设备", devices.size.toString(), Modifier.weight(1f))
            SummaryTile("在线", onlineCount.toString(), Modifier.weight(1f))
            SummaryTile("告警", alertCount.toString(), Modifier.weight(1f).clickable(onClick = onOpenAlerts), Amber)
        }
        Spacer(Modifier.height(14.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
            SecondaryAction("刷新状态", enabled = !loading, modifier = Modifier.weight(1f), onClick = onRefresh)
            SecondaryAction("退出登录", enabled = true, modifier = Modifier.weight(1f), onClick = onLogout)
        }
    }
}

@Composable
private fun BottomModuleBar(
    current: AppModule,
    alertCount: Int,
    modifier: Modifier = Modifier,
    onSelect: (AppModule) -> Unit,
) {
    GlassCard(modifier = modifier.padding(bottom = 12.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            NavButton("概览", current == AppModule.Devices, Modifier.weight(1f)) { onSelect(AppModule.Devices) }
            NavButton(if (alertCount > 0) "告警 $alertCount" else "告警", current == AppModule.Alerts, Modifier.weight(1f)) { onSelect(AppModule.Alerts) }
            NavButton("品种", current == AppModule.Plants, Modifier.weight(1f)) { onSelect(AppModule.Plants) }
        }
    }
}

@Composable
private fun NavButton(label: String, selected: Boolean, modifier: Modifier, onClick: () -> Unit) {
    Button(
        onClick = onClick,
        modifier = modifier.height(42.dp),
        shape = RoundedCornerShape(14.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = if (selected) Moss else Color.White.copy(alpha = 0.56f),
            contentColor = if (selected) Color.White else Moss,
        ),
        border = if (selected) null else BorderStroke(1.dp, Color.White.copy(alpha = 0.82f)),
    ) {
        Text(label, fontWeight = FontWeight.SemiBold, fontSize = 12.sp)
    }
}

@Composable
private fun QuickActions(loading: Boolean, onDiscover: () -> Unit, onRefresh: () -> Unit) {
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
        Button(
            onClick = onDiscover,
            enabled = !loading,
            modifier = Modifier.weight(1f).height(48.dp),
            shape = RoundedCornerShape(16.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Moss, contentColor = Color.White),
        ) {
            Text("扫描设备", fontWeight = FontWeight.SemiBold)
        }
        Button(
            onClick = onRefresh,
            enabled = !loading,
            modifier = Modifier.weight(1f).height(48.dp),
            shape = RoundedCornerShape(16.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Color.White.copy(alpha = 0.66f), contentColor = Moss),
            border = BorderStroke(1.dp, Color.White.copy(alpha = 0.82f)),
        ) {
            Text("刷新数据", fontWeight = FontWeight.SemiBold)
        }
    }
}

@Composable
private fun CandidateCard(candidate: LanDeviceCandidate, onBind: () -> Unit) {
    GlassCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            DeviceGlyph(active = true)
            Column(modifier = Modifier.weight(1f).padding(start = 12.dp)) {
                Text(candidate.deviceId, color = Ink, fontWeight = FontWeight.Bold, fontSize = 17.sp)
                Text("IP ${candidate.ip}", color = Muted, fontSize = 12.sp)
                Text("固件 ${candidate.firmwareVersion ?: "--"}  RSSI ${candidate.wifiRssi ?: "--"} dBm", color = Muted, fontSize = 12.sp)
            }
            Button(
                onClick = onBind,
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Leaf, contentColor = Color.White),
            ) {
                Text("绑定")
            }
        }
    }
}

@Composable
private fun DeviceCard(
    device: DeviceListItem,
    telemetry: LatestTelemetry?,
    onLoadTelemetry: () -> Unit,
    onOpen: () -> Unit,
    onWater: () -> Unit,
) {
    GlassCard(modifier = Modifier.clickable(onClick = onOpen)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            DeviceGlyph(active = device.online)
            Column(modifier = Modifier.weight(1f).padding(start = 12.dp)) {
                Text(device.name.ifBlank { device.deviceId }, color = Ink, fontSize = 18.sp, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text("${device.deviceId}  ${device.plantTypeName ?: "未设置植物"}", color = Muted, fontSize = 12.sp)
            }
            StatusBadge(if (device.online) "在线" else "离线", device.online)
        }
        Spacer(Modifier.height(16.dp))
        telemetry?.let {
            MetricGrid(it)
            Spacer(Modifier.height(12.dp))
        } ?: device.latestTelemetry?.let {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                MiniMetric("温度", formatValue(it.temperature, " ℃"), Modifier.weight(1f))
                MiniMetric("湿度", formatValue(it.humidity, "%"), Modifier.weight(1f))
                MiniMetric("土壤", formatValue(it.soilMoisture, "%"), Modifier.weight(1f))
            }
            Spacer(Modifier.height(12.dp))
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            SecondaryAction("进入详情", enabled = true, modifier = Modifier.weight(1f), onClick = onLoadTelemetry)
            Button(
                onClick = onWater,
                enabled = device.online,
                modifier = Modifier.weight(1f).height(46.dp),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Amber, contentColor = Color.White, disabledContainerColor = Color(0xFFD7DED8)),
            ) {
                Text("补水 5 秒", fontWeight = FontWeight.SemiBold)
            }
        }
    }
}

@Composable
private fun AlertCard(
    item: AlertWithDevice,
    onMarkRead: () -> Unit,
    onMarkDeviceRead: () -> Unit,
    onOpenDevice: () -> Unit,
) {
    val severityColor = when (item.alert.severity) {
        "critical" -> Color(0xFFB91C1C)
        "warning" -> Amber
        else -> Leaf
    }
    GlassCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(42.dp)
                    .clip(CircleShape)
                    .background(severityColor.copy(alpha = if (item.alert.read) 0.18f else 0.28f)),
                contentAlignment = Alignment.Center,
            ) {
                Text(if (item.alert.read) "✓" else "!", color = severityColor, fontWeight = FontWeight.Bold, fontSize = 18.sp)
            }
            Column(modifier = Modifier.weight(1f).padding(start = 12.dp)) {
                Text(item.alert.title, color = Ink, fontSize = 17.sp, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(item.alert.message, color = Muted, fontSize = 13.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
                Text("${item.device.name} · ${item.alert.createdAt ?: "--"}", color = Muted, fontSize = 11.sp)
            }
            StatusBadge(if (item.alert.read) "已读" else "未读", !item.alert.read)
        }
        Spacer(Modifier.height(12.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            SecondaryAction("查看设备", enabled = true, modifier = Modifier.weight(1f), onClick = onOpenDevice)
            SecondaryAction("设为已读", enabled = !item.alert.read, modifier = Modifier.weight(1f), onClick = onMarkRead)
        }
        Spacer(Modifier.height(8.dp))
        SecondaryAction("该设备全部已读", enabled = true, onClick = onMarkDeviceRead)
    }
}

@Composable
private fun PlantTypeCard(
    plant: PlantTypeItem,
    loading: Boolean,
    onEdit: () -> Unit,
    onDelete: () -> Unit,
) {
    GlassCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            DeviceGlyph(active = true)
            Column(modifier = Modifier.weight(1f).padding(start = 12.dp)) {
                Text(plant.name, color = Ink, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                Text("${categoryLabel(plant.category)} · ${plant.plantType}", color = Muted, fontSize = 12.sp)
            }
            StatusBadge("${plant.wateringConfig.defaultDurationMs / 1000} 秒", true)
        }
        Spacer(Modifier.height(14.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            MiniMetric("温度", rangeText(plant.defaultThresholds.temperature.min, plant.defaultThresholds.temperature.max, " ℃"), Modifier.weight(1f))
            MiniMetric("湿度", rangeText(plant.defaultThresholds.humidity.min, plant.defaultThresholds.humidity.max, "%"), Modifier.weight(1f))
        }
        Spacer(Modifier.height(8.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            MiniMetric("土壤", rangeText(plant.defaultThresholds.soilMoisture.min, plant.defaultThresholds.soilMoisture.max, "%"), Modifier.weight(1f))
            MiniMetric("触发补水", formatValue(plant.wateringConfig.triggerSoilMoisture, "%"), Modifier.weight(1f))
        }
        Spacer(Modifier.height(12.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
            SecondaryAction("修改", enabled = !loading, modifier = Modifier.weight(1f), onClick = onEdit)
            Button(
                onClick = onDelete,
                enabled = !loading,
                modifier = Modifier.weight(1f).height(46.dp),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFB91C1C), contentColor = Color.White, disabledContainerColor = Color(0xFFD7DED8)),
            ) {
                Text("删除", fontWeight = FontWeight.SemiBold)
            }
        }
    }
}

@Composable
private fun ActionRow(
    loading: Boolean,
    online: Boolean,
    onRefresh: () -> Unit,
    onWater: () -> Unit,
    onPhoto: () -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
            SecondaryAction("刷新", enabled = !loading, modifier = Modifier.weight(1f), onClick = onRefresh)
            SecondaryAction("拍照", enabled = !loading && online, modifier = Modifier.weight(1f), onClick = onPhoto)
        }
        Button(
            onClick = onWater,
            enabled = !loading && online,
            modifier = Modifier.fillMaxWidth().height(48.dp),
            shape = RoundedCornerShape(16.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Amber, contentColor = Color.White, disabledContainerColor = Color(0xFFD7DED8)),
        ) {
            Text("补水 5 秒", fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun MetricGrid(telemetry: LatestTelemetry) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            MiniMetric("温度", formatValue(telemetry.sensors.temperature, " ℃"), Modifier.weight(1f))
            MiniMetric("湿度", formatValue(telemetry.sensors.humidity, "%"), Modifier.weight(1f))
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            MiniMetric("土壤", formatValue(telemetry.sensors.soilMoisture, "%"), Modifier.weight(1f))
            MiniMetric("光照", formatValue(telemetry.sensors.lightIntensity, " lux"), Modifier.weight(1f))
        }
    }
}

@Composable
private fun CareAdviceCard(report: DailyReport?, loading: Boolean) {
    GlassCard {
        if (report == null) {
            EmptyInline(if (loading) "正在生成今日养护视图..." else "暂无今日养护报告。")
            return@GlassCard
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
            SummaryTile("健康", report.healthScore?.toString() ?: "--", Modifier.weight(1f), Leaf)
            SummaryTile("照片", report.photosTaken.toString(), Modifier.weight(1f), Amber)
            SummaryTile("补水", report.watering?.count?.toString() ?: "0", Modifier.weight(1f), Moss)
        }
        Spacer(Modifier.height(14.dp))
        Text(report.suggestion.ifBlank { "今日暂无特殊养护建议。" }, color = Ink, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
        report.suggestionDetail?.wateringRecommendation?.let {
            Spacer(Modifier.height(10.dp))
            Text("补水建议：$it", color = Muted, fontSize = 13.sp)
        }
        report.suggestionDetail?.nextWateringTime?.let {
            Text("下次补水：$it", color = Muted, fontSize = 13.sp)
        }
        val items = report.suggestionDetail?.attentionItems.orEmpty()
        if (items.isNotEmpty()) {
            Spacer(Modifier.height(10.dp))
            items.take(3).forEach { item ->
                Text("- $item", color = Muted, fontSize = 13.sp)
            }
        }
        Spacer(Modifier.height(14.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            MiniMetric("均温", formatValue(report.environmentSummary?.temperature?.avg, " ℃"), Modifier.weight(1f))
            MiniMetric("均湿", formatValue(report.environmentSummary?.humidity?.avg, "%"), Modifier.weight(1f))
            MiniMetric("土壤均值", formatValue(report.environmentSummary?.soilMoisture?.avg, "%"), Modifier.weight(1f))
        }
        if (report.diseaseAlert) {
            Spacer(Modifier.height(10.dp))
            ErrorBanner("今日照片中发现病害风险。")
        }
    }
}

@Composable
private fun ImageCard(image: ImageItem) {
    GlassCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            AsyncImage(
                model = image.annotatedUrl ?: image.url,
                contentDescription = "植物照片",
                contentScale = ContentScale.Crop,
                modifier = Modifier
                    .size(92.dp)
                    .clip(RoundedCornerShape(20.dp))
                    .background(Color.White.copy(alpha = 0.46f)),
            )
            Column(modifier = Modifier.weight(1f).padding(start = 12.dp)) {
                Text("照片 ${image.photoIndex ?: ""}".trim(), color = Ink, fontSize = 17.sp, fontWeight = FontWeight.Bold)
                Text(image.timestamp ?: "暂无时间", color = Muted, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text("识别状态 ${image.detectionStatus ?: "--"}", color = Muted, fontSize = 12.sp)
            }
            Column(horizontalAlignment = Alignment.End) {
                Text("${image.diseaseCount}", color = if (image.diseaseCount > 0) Amber else Leaf, fontSize = 22.sp, fontWeight = FontWeight.Bold)
                Text("问题", color = Muted, fontSize = 11.sp)
                Text("${image.healthScore ?: "--"}", color = Moss, fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
            }
        }
    }
}

@Composable
private fun GlassCard(
    modifier: Modifier = Modifier,
    content: @Composable ColumnScope.() -> Unit,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(26.dp),
        colors = CardDefaults.cardColors(containerColor = Glass),
        border = BorderStroke(1.dp, Color.White.copy(alpha = 0.72f)),
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp),
    ) {
        Column(modifier = Modifier.padding(18.dp), content = content)
    }
}

@Composable
private fun AppTextField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier.fillMaxWidth(),
    isPassword: Boolean = false,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(label) },
        visualTransformation = if (isPassword) PasswordVisualTransformation() else VisualTransformation.None,
        modifier = modifier,
        shape = RoundedCornerShape(16.dp),
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = Leaf,
            unfocusedBorderColor = Color.White.copy(alpha = 0.85f),
            focusedContainerColor = Color.White.copy(alpha = 0.48f),
            unfocusedContainerColor = Color.White.copy(alpha = 0.42f),
        ),
    )
}

@Composable
private fun PrimaryAction(label: String, loading: Boolean, onClick: () -> Unit) {
    Button(
        onClick = onClick,
        enabled = !loading,
        modifier = Modifier.fillMaxWidth().height(52.dp),
        shape = RoundedCornerShape(18.dp),
        colors = ButtonDefaults.buttonColors(containerColor = Moss, contentColor = Color.White),
    ) {
        if (loading) {
            CircularProgressIndicator(modifier = Modifier.size(20.dp), color = Color.White, strokeWidth = 2.dp)
        } else {
            Text(label, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun SecondaryAction(
    label: String,
    enabled: Boolean,
    modifier: Modifier = Modifier.fillMaxWidth(),
    onClick: () -> Unit,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier.height(46.dp),
        shape = RoundedCornerShape(14.dp),
        colors = ButtonDefaults.buttonColors(containerColor = Color.White.copy(alpha = 0.64f), contentColor = Moss),
        border = BorderStroke(1.dp, Color.White.copy(alpha = 0.84f)),
    ) {
        Text(label, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun SectionTitle(title: String, subtitle: String) {
    Column(modifier = Modifier.padding(top = 8.dp, bottom = 2.dp)) {
        Text(title, color = Moss, fontSize = 19.sp, fontWeight = FontWeight.Bold)
        Text(subtitle, color = Muted, fontSize = 12.sp)
    }
}

@Composable
private fun SummaryTile(label: String, value: String, modifier: Modifier, color: Color = Leaf) {
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(18.dp))
            .background(Color.White.copy(alpha = 0.46f))
            .padding(12.dp),
    ) {
        Text(label, color = Muted, fontSize = 11.sp)
        Text(value, color = color, fontSize = 22.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun MiniMetric(label: String, value: String, modifier: Modifier) {
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(16.dp))
            .background(Color.White.copy(alpha = 0.48f))
            .padding(12.dp),
    ) {
        Text(label, color = Muted, fontSize = 11.sp)
        Text(value, color = Ink, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
    }
}

@Composable
private fun StatusBadge(text: String, active: Boolean) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .clip(RoundedCornerShape(999.dp))
            .background(if (active) Color(0xFFE3F7E8) else Color(0xFFF1F1EE))
            .padding(horizontal = 10.dp, vertical = 7.dp),
    ) {
        Box(
            modifier = Modifier
                .size(8.dp)
                .clip(CircleShape)
                .background(if (active) Leaf else Color(0xFF9AA59E)),
        )
        Text(text, color = if (active) Moss else Muted, fontSize = 12.sp, modifier = Modifier.padding(start = 6.dp), fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun DeviceGlyph(active: Boolean) {
    Box(
        modifier = Modifier
            .size(54.dp)
            .clip(RoundedCornerShape(18.dp))
            .background(
                Brush.verticalGradient(
                    listOf(
                        if (active) Color(0xFFDDF6E4) else Color(0xFFE9ECE9),
                        if (active) Color(0xFFBDE8C9) else Color(0xFFD5DAD6),
                    ),
                ),
            ),
        contentAlignment = Alignment.Center,
    ) {
        Canvas(modifier = Modifier.size(34.dp)) {
            val stem = Leaf.copy(alpha = if (active) 0.95f else 0.42f)
            drawLine(stem, Offset(size.width * 0.50f, size.height * 0.82f), Offset(size.width * 0.50f, size.height * 0.32f), strokeWidth = 3.dp.toPx())
            drawOval(stem.copy(alpha = 0.78f), topLeft = Offset(size.width * 0.16f, size.height * 0.18f), size = androidx.compose.ui.geometry.Size(size.width * 0.38f, size.height * 0.28f))
            drawOval(stem.copy(alpha = 0.66f), topLeft = Offset(size.width * 0.48f, size.height * 0.08f), size = androidx.compose.ui.geometry.Size(size.width * 0.38f, size.height * 0.30f))
            drawRoundRect(Amber.copy(alpha = if (active) 0.84f else 0.40f), topLeft = Offset(size.width * 0.23f, size.height * 0.72f), size = androidx.compose.ui.geometry.Size(size.width * 0.54f, size.height * 0.18f), cornerRadius = androidx.compose.ui.geometry.CornerRadius(6.dp.toPx(), 6.dp.toPx()))
        }
    }
}

@Composable
private fun ErrorBanner(message: String) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(Color(0xFFFFEFE9).copy(alpha = 0.92f))
            .padding(12.dp),
    ) {
        Text(message, color = Color(0xFF9A3412), fontSize = 13.sp)
    }
}

@Composable
private fun EmptyState() {
    GlassCard {
        Text("还没有绑定设备", color = Ink, fontWeight = FontWeight.Bold, fontSize = 18.sp)
        Text("让 ESP32 与后端处在同一 WiFi 下，点击扫描即可发现并绑定。", color = Muted, fontSize = 13.sp)
    }
}

@Composable
private fun EmptyInline(text: String) {
    Text(text, color = Muted, fontSize = 13.sp)
}

private fun categoryLabel(value: String): String {
    return when (value) {
        "foliage" -> "观叶植物"
        "succulent" -> "多肉植物"
        "flowering" -> "观花植物"
        "herb" -> "草本植物"
        else -> value
    }
}

private fun rangeText(min: Double, max: Double, suffix: String): String {
    return "%.0f~%.0f%s".format(Locale.US, min, max, suffix)
}

private fun formatValue(value: Double?, suffix: String): String {
    return value?.let { "%.1f%s".format(Locale.US, it, suffix) } ?: "--"
}
