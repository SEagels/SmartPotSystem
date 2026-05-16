from __future__ import annotations

import asyncio
import ipaddress
import secrets
import socket
import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device

DISCOVERY_TIMEOUT_S = 0.8
DISCOVERY_CONCURRENCY = 64


def _local_cidrs() -> list[ipaddress.IPv4Network]:
    cidrs: list[ipaddress.IPv4Network] = []
    try:
        _, _, addresses = socket.gethostbyname_ex(socket.gethostname())
    except OSError:
        addresses = []

    for address in addresses:
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            continue
        if isinstance(ip, ipaddress.IPv4Address) and ip.is_private and not ip.is_loopback:
            cidrs.append(ipaddress.ip_network(f"{ip}/24", strict=False))
    return cidrs


def _parse_scan_targets(cidr: str | None) -> list[str]:
    networks = [ipaddress.ip_network(cidr, strict=False)] if cidr else _local_cidrs()
    targets: list[str] = []
    for network in networks:
        if not isinstance(network, ipaddress.IPv4Network):
            continue
        if not network.is_private or network.is_loopback or network.is_link_local:
            raise ValueError("仅允许扫描私有局域网网段")
        if network.num_addresses > 512:
            raise ValueError("扫描网段过大，请使用 /24 或更小网段")
        targets.extend(str(ip) for ip in network.hosts())
    return sorted(set(targets))


async def _probe_status(client: httpx.AsyncClient, ip: str) -> dict | None:
    url = f"http://{ip}/api/status"
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return None

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict) or not data.get("device_id"):
        return None

    return {
        "device_id": str(data.get("device_id")),
        "ip": ip,
        "firmware_version": data.get("fw_version"),
        "wifi_rssi": data.get("wifi_rssi"),
        "uptime_s": data.get("uptime_s"),
        "mock_mode": data.get("mock_mode"),
        "pump_running": data.get("pump_running"),
    }


async def discover_lan_devices(cidr: str | None = None) -> list[dict]:
    targets = _parse_scan_targets(cidr)
    if not targets:
        return []

    semaphore = asyncio.Semaphore(DISCOVERY_CONCURRENCY)

    async with httpx.AsyncClient(timeout=DISCOVERY_TIMEOUT_S) as client:
        async def guarded_probe(ip: str) -> dict | None:
            async with semaphore:
                return await _probe_status(client, ip)

        results = await asyncio.gather(*(guarded_probe(ip) for ip in targets))
    return [item for item in results if item]


async def probe_lan_device(ip: str) -> dict | None:
    async with httpx.AsyncClient(timeout=DISCOVERY_TIMEOUT_S) as client:
        return await _probe_status(client, ip)


async def bind_lan_device(
    db: AsyncSession,
    user_id: uuid.UUID,
    device_id: str,
    ip: str,
    name: str | None = None,
) -> Device:
    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError as exc:
        raise ValueError("设备 IP 格式错误") from exc
    if not isinstance(ip_obj, ipaddress.IPv4Address) or not ip_obj.is_private:
        raise ValueError("仅允许绑定私有局域网内的设备")

    status = await probe_lan_device(ip)
    if not status:
        raise ValueError("无法访问该设备，请确认手机/电脑与 ESP32 在同一 WiFi")
    if status["device_id"] != device_id:
        raise ValueError("设备 ID 与局域网探测结果不一致")

    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()
    if device and device.user_id and device.user_id != user_id:
        raise ValueError("设备已被其他用户绑定")

    if not device:
        device = Device(
            device_id=device_id,
            bind_code=secrets.token_hex(4).upper(),
            firmware_version=status.get("firmware_version"),
            online=True,
        )
        db.add(device)

    device.user_id = user_id
    device.bound_at = device.bound_at or datetime.now(UTC)
    device.last_seen_at = datetime.now(UTC)
    device.name = name or device.name or f"新设备-{device_id}"
    device.online = True
    device.firmware_version = status.get("firmware_version") or device.firmware_version
    return device
