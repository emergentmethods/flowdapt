from typing import Any

from flowdapt.core.domain.models.status import SystemStatus
from flowdapt.lib.utils.model import BaseModel, model_dump


class V1Alpha1SystemStatusSystemInfo(BaseModel):
    time: str
    cpu_pct: float
    memory: int
    disk_pct: float
    network_io_sent: int
    network_io_recv: int
    threads: int
    fds: int
    pid: int


class V1Alpha1SystemStatusOSInfo(BaseModel):
    name: str
    version: str
    release: str
    machine: str


class V1Alpha1SystemStatus(BaseModel):
    version: str
    name: str
    system: V1Alpha1SystemStatusSystemInfo
    os: V1Alpha1SystemStatusOSInfo
    python: str
    hostname: str
    services: dict[str, Any]
    database: str

    @classmethod
    def from_model(cls, model: SystemStatus):
        return cls(**model_dump(model))
