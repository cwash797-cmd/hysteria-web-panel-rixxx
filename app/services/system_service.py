import platform
import psutil
import shutil
import time

_last_net_sample = {
    "ts": None,
    "bytes_sent": None,
    "bytes_recv": None,
}


def _network_rate_mbps() -> dict:
    counters = psutil.net_io_counters()
    now = time.time()

    ts = _last_net_sample["ts"]
    sent = _last_net_sample["bytes_sent"]
    recv = _last_net_sample["bytes_recv"]

    tx_mbps = 0.0
    rx_mbps = 0.0
    if ts is not None and sent is not None and recv is not None:
        dt = max(now - ts, 0.0001)
        tx_mbps = max(((counters.bytes_sent - sent) * 8 / dt) / 1_000_000, 0.0)
        rx_mbps = max(((counters.bytes_recv - recv) * 8 / dt) / 1_000_000, 0.0)

    _last_net_sample["ts"] = now
    _last_net_sample["bytes_sent"] = counters.bytes_sent
    _last_net_sample["bytes_recv"] = counters.bytes_recv

    return {
        "tx_mbps": round(tx_mbps, 2),
        "rx_mbps": round(rx_mbps, 2),
        "total_sent_mb": round(counters.bytes_sent / 1024 / 1024, 2),
        "total_recv_mb": round(counters.bytes_recv / 1024 / 1024, 2),
    }


def get_system_status() -> dict:
    vm = psutil.virtual_memory()
    disk = shutil.disk_usage("/")
    return {
        "os": platform.platform(),
        "uptime_seconds": int(time.time() - psutil.boot_time()),
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "memory": {
            "total_mb": round(vm.total / 1024 / 1024, 2),
            "used_mb": round(vm.used / 1024 / 1024, 2),
            "percent": vm.percent,
        },
        "disk_root": {
            "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
            "used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
            "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
        },
        "network": _network_rate_mbps(),
    }
