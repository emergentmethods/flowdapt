import platform
from datetime import datetime
from typing import Any

import psutil

from flowdapt.lib.config import get_configuration
from flowdapt.lib.context import get_context
from flowdapt.lib.utils.misc import get_full_path_type
from flowdapt.lib.utils.model import BaseModel


SYSTEM_STATUS_RESOURCE_KIND = "system"


class SystemStatusSystemInfo(BaseModel):
    time: str
    cpu_pct: float
    memory: int
    disk_pct: float
    network_io_sent: int
    network_io_recv: int
    threads: int
    fds: int
    pid: int


class SystemStatusOSInfo(BaseModel):
    name: str
    version: str
    release: str
    machine: str


class SystemStatus(BaseModel):
    version: str
    name: str
    system: SystemStatusSystemInfo
    os: SystemStatusOSInfo
    python: str
    hostname: str
    services: dict[str, Any]
    database: str

    @classmethod
    async def snapshot(cls):
        from flowdapt import __version__

        context = get_context()
        config = get_configuration()

        return cls(
            **{
                "version": __version__,
                "name": config.name,
                "system": {
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "cpu_pct": psutil.cpu_percent(interval=1),
                    "memory": psutil.Process().memory_info().rss,
                    "disk_pct": psutil.disk_usage("/").percent,
                    "network_io_sent": psutil.net_io_counters().bytes_sent,
                    "network_io_recv": psutil.net_io_counters().bytes_recv,
                    "threads": psutil.Process().num_threads(),
                    "fds": psutil.Process().num_fds(),
                    "pid": psutil.Process().pid,
                },
                "os": {
                    "name": platform.system(),
                    "version": platform.version(),
                    "release": platform.release(),
                    "machine": platform.machine(),
                },
                "python": platform.python_version(),
                "hostname": platform.node(),
                "services": await context.controller.get_service_status(),
                "database": get_full_path_type(context.database),
            }
        )
