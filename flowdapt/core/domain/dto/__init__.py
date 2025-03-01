from flowdapt.core.domain.dto.v1.metrics import V1Alpha1Metrics
from flowdapt.core.domain.dto.v1.plugin import V1Alpha1Plugin, V1Alpha1PluginFiles
from flowdapt.core.domain.dto.v1.status import V1Alpha1SystemStatus


SystemStatusResponse = V1Alpha1SystemStatus
MetricsResponse = V1Alpha1Metrics
PluginResponse = V1Alpha1Plugin
PluginFilesResponse = V1Alpha1PluginFiles

SystemStatusReadDTOs = {
    "v1alpha1": (None, V1Alpha1SystemStatus),
}

PluginReadDTOs = {
    "v1alpha1": (None, V1Alpha1Plugin),
}

PluginFilesReadDTOs = {
    "v1alpha1": (None, V1Alpha1PluginFiles),
}

MetricsReadDTOs = {
    "v1alpha1": (None, V1Alpha1Metrics),
}
