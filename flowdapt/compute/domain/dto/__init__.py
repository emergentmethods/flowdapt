from typing import Union

from flowdapt.compute.domain.dto.v1.workflow import (
    V1Alpha1WorkflowResourceCreateRequest,
    V1Alpha1WorkflowResourceCreateResponse,
    V1Alpha1WorkflowResourceUpdateRequest,
    V1Alpha1WorkflowResourceUpdateResponse,
    V1Alpha1WorkflowResourceReadResponse,
)
from flowdapt.compute.domain.dto.v1.workflowrun import (
    V1Alpha1WorkflowRunReadResponse,
)
from flowdapt.compute.domain.dto.v1.config import (
    V1Alpha1ConfigResourceCreateRequest,
    V1Alpha2ConfigResourceCreateRequest,
    V1Alpha1ConfigResourceCreateResponse,
    V1Alpha2ConfigResourceCreateResponse,
    V1Alpha1ConfigResourceUpdateRequest,
    V1Alpha1ConfigResourceUpdateResponse,
    V1Alpha1ConfigResourceReadResponse,
)

WorkflowResourceCreateRequest = V1Alpha1WorkflowResourceCreateRequest
WorkflowResourceCreateResponse = V1Alpha1WorkflowResourceCreateResponse
WorkflowResourceUpdateRequest = V1Alpha1WorkflowResourceUpdateRequest
WorkflowResourceUpdateResponse = V1Alpha1WorkflowResourceUpdateResponse
WorkflowResourceReadResponse = V1Alpha1WorkflowResourceReadResponse
WorkflowRunReadResponse = V1Alpha1WorkflowRunReadResponse
ConfigResourceCreateRequest = Union[
    V1Alpha1ConfigResourceCreateRequest,
    V1Alpha2ConfigResourceCreateRequest,
]
ConfigResourceCreateResponse = Union[
    V1Alpha1ConfigResourceCreateResponse,
    V1Alpha2ConfigResourceCreateResponse,
]
ConfigResourceUpdateRequest = V1Alpha1ConfigResourceUpdateRequest
ConfigResourceUpdateResponse = V1Alpha1ConfigResourceUpdateResponse
ConfigResourceReadResponse = V1Alpha1ConfigResourceReadResponse

WorkflowResourceCreateDTOs = {
    "v1alpha1": (
        V1Alpha1WorkflowResourceCreateRequest,
        V1Alpha1WorkflowResourceCreateResponse
    ),
}

WorkflowResourceReadDTOs = {
    "v1alpha1": (
        None,
        V1Alpha1WorkflowResourceReadResponse
    ),
}

WorkflowResourceUpdateDTOs = {
    "v1alpha1": (
        V1Alpha1WorkflowResourceUpdateRequest,
        V1Alpha1WorkflowResourceUpdateResponse
    ),
}

WorkflowRunReadDTOs = {
    "v1alpha1": (
        None,
        V1Alpha1WorkflowRunReadResponse
    ),
}

ConfigResourceCreateDTOs = {
    "v1alpha1": (
        V1Alpha1ConfigResourceCreateRequest,
        V1Alpha1ConfigResourceCreateResponse
    ),
    "v1alpha2": (
        V1Alpha2ConfigResourceCreateRequest,
        V1Alpha2ConfigResourceCreateResponse
    ),
}

ConfigResourceUpdateDTOs = {
    "v1alpha1": (
        V1Alpha1ConfigResourceUpdateRequest,
        V1Alpha1ConfigResourceUpdateResponse
    ),
}

ConfigResourceReadDTOs = {
    "v1alpha1": (
        None,
        V1Alpha1ConfigResourceReadResponse
    ),
}
