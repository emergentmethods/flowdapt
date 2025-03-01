from flowdapt.compute.domain.dto.v1.config import (
    V1Alpha1ConfigResourceCreateRequest,
    V1Alpha1ConfigResourceCreateResponse,
    V1Alpha1ConfigResourceReadResponse,
    V1Alpha1ConfigResourceUpdateRequest,
    V1Alpha1ConfigResourceUpdateResponse,
)
from flowdapt.compute.domain.dto.v1.workflow import (
    V1Alpha1WorkflowResourceCreateRequest,
    V1Alpha1WorkflowResourceCreateResponse,
    V1Alpha1WorkflowResourceReadResponse,
    V1Alpha1WorkflowResourceUpdateRequest,
    V1Alpha1WorkflowResourceUpdateResponse,
)
from flowdapt.compute.domain.dto.v1.workflowrun import (
    V1Alpha1WorkflowRunReadResponse,
)


WorkflowResourceCreateRequest = V1Alpha1WorkflowResourceCreateRequest
WorkflowResourceCreateResponse = V1Alpha1WorkflowResourceCreateResponse
WorkflowResourceUpdateRequest = V1Alpha1WorkflowResourceUpdateRequest
WorkflowResourceUpdateResponse = V1Alpha1WorkflowResourceUpdateResponse
WorkflowResourceReadResponse = V1Alpha1WorkflowResourceReadResponse
WorkflowRunReadResponse = V1Alpha1WorkflowRunReadResponse
ConfigResourceCreateRequest = V1Alpha1ConfigResourceCreateRequest
ConfigResourceCreateResponse = V1Alpha1ConfigResourceCreateResponse
ConfigResourceUpdateRequest = V1Alpha1ConfigResourceUpdateRequest
ConfigResourceUpdateResponse = V1Alpha1ConfigResourceUpdateResponse
ConfigResourceReadResponse = V1Alpha1ConfigResourceReadResponse

WorkflowResourceCreateDTOs = {
    "v1alpha1": (V1Alpha1WorkflowResourceCreateRequest, V1Alpha1WorkflowResourceCreateResponse),
}

WorkflowResourceReadDTOs = {
    "v1alpha1": (None, V1Alpha1WorkflowResourceReadResponse),
}

WorkflowResourceUpdateDTOs = {
    "v1alpha1": (V1Alpha1WorkflowResourceUpdateRequest, V1Alpha1WorkflowResourceUpdateResponse),
}

WorkflowRunReadDTOs = {
    "v1alpha1": (None, V1Alpha1WorkflowRunReadResponse),
}

ConfigResourceCreateDTOs = {
    "v1alpha1": (V1Alpha1ConfigResourceCreateRequest, V1Alpha1ConfigResourceCreateResponse),
}

ConfigResourceUpdateDTOs = {
    "v1alpha1": (V1Alpha1ConfigResourceUpdateRequest, V1Alpha1ConfigResourceUpdateResponse),
}

ConfigResourceReadDTOs = {
    "v1alpha1": (None, V1Alpha1ConfigResourceReadResponse),
}
