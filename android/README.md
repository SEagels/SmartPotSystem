# SmartPot Android App

原生 Android 客户端骨架，使用 Kotlin + Jetpack Compose，对接 `docs/04-API接口设计.md` 中的 `/v1` 接口。

## 已包含功能

- 登录并保存本次会话 token
- 获取设备列表
- 查看设备最新传感器数据
- 手动补水
- 局域网发现 ESP32：调用后端 `GET /v1/devices/lan-discover`
- 无设备码绑定：调用后端 `POST /v1/devices/lan-bind`

## 后端地址

默认地址在登录页可改：

- Android 模拟器访问本机后端：`http://10.0.2.2:8000/v1`
- 真机和电脑同 WiFi：改为电脑局域网 IP，例如 `http://192.168.1.100:8000/v1`

后端启动：

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 构建方式

用 Android Studio 打开 `android/` 目录后，同步 Gradle，然后运行 `app`。

如果本机已安装 Gradle 和 Android SDK，也可以在 `android/` 目录执行：

```bash
gradle :app:assembleDebug
```

## Android Studio 同步报错处理

如果看到类似：

```text
prepareKotlinBuildScriptModel
Could not get resource 'https://services.gradle.org/distributions/gradle-9.0.0-src.zip'
PKIX path building failed
```

这是 Android Studio/Gradle 在解析 Kotlin DSL 构建脚本时下载 Gradle 源码失败，常见于网络代理或 JDK 证书链问题。当前工程已改为 Groovy Gradle 脚本：

- `settings.gradle`
- `build.gradle`
- `app/build.gradle`

处理步骤：

1. 关闭 Android Studio。
2. 删除 `android/.gradle` 和 `android/.idea` 后重新打开 `android/` 目录。
3. 在 Android Studio 的 Gradle 设置里选择 Gradle JDK 为内置 JBR 或 JDK 17。
4. 如果仍使用本机 Gradle 9，可以在 Gradle 设置中改用 Gradle `8.10.2`，本工程的 `gradle/wrapper/gradle-wrapper.properties` 已锁定该版本。

## 局域网新增设备流程

1. ESP32 与电脑/后端在同一 WiFi。
2. 固件本地 HTTP 服务可访问：`http://<esp32-ip>/api/status`。
3. App 登录后点击“扫描局域网设备”。
4. 后端扫描 LAN 并返回候选设备。
5. App 点击候选设备的“绑定”，后端再次探测该 IP，确认 `device_id` 后绑定到当前用户。
